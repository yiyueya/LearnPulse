# 内容提取 Agent
from src.utils.pdf_parser import PDFParser
from src.utils.file_status_manager import FileStatusManager
from src.services.ai_service import AIService
from src.utils.text_splitter import TextSplitter
from src.utils.cache_manager import CacheManager
from src.utils.logger import logger
from src.utils.quota_tracker import MiniMaxVLMError
import json
from pathlib import Path
from config.config import JSON_DIR, IMAGE_PROCESSING_ENABLED, IMAGE_SMART_FILTER

class ContentExtractorAgent:
    """内容提取Agent，负责从PDF文档中提取知识点"""

    def __init__(self):
        self.pdf_parser = PDFParser()
        self.file_status_manager = FileStatusManager()
        self.ai_service = AIService()
        self.text_splitter = TextSplitter()
        self.cache_manager = CacheManager()
        self.json_dir = JSON_DIR
        self.json_dir.mkdir(parents=True, exist_ok=True)
        self.progress_callback = None
        self._cancel_check = None
        self._cancelled = False

    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback

    def set_cancel_check(self, check_fn):
        """设置取消检查函数"""
        self._cancel_check = check_fn

    def cancel(self):
        """标记为取消"""
        self._cancelled = True

    def _check_cancel(self):
        """检查是否请求了取消"""
        if self._cancelled:
            from src.agents.agent_coordinator import CancellationRequested
            raise CancellationRequested("用户取消了处理")
        if self._cancel_check:
            self._cancel_check()

    def _update_progress(self, message, progress=None):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback({"message": message, "progress": progress})

    def _calculate_step_progress(self, current_step, total_steps, sub_progress=0):
        """计算步骤进度百分比"""
        step_weight = 100 / total_steps
        base_progress = (current_step - 1) * step_weight
        step_progress = step_weight * sub_progress / 100
        return min(int(base_progress + step_progress), 99)
    
    def process_pdf(self, pdf_path, subject):
        """处理PDF文档，提取知识点（包括图片内容）"""
        filename = Path(pdf_path).name
        logger.debug(f"[ContentExtractor] Starting PDF processing: {filename}")

        self._check_cancel()

        if self.cache_manager.is_file_completed(pdf_path):
            result = self.cache_manager.get_process_result(pdf_path)
            if result:
                self._update_progress(f"文件已处理完成，使用缓存结果: {filename}", 100)
                return result

        self._check_cancel()
        self.cache_manager.set_process_status(pdf_path, 'processing', current_step=1, total_steps=4)
        self._update_progress(f"开始处理 {subject}: {filename}", self._calculate_step_progress(1, 4, 0))

        process_cache = self.cache_manager.get_process_cache(pdf_path)
        extracted_data = process_cache.get("extracted_data", {
            "text": "",
            "images_description": [],
            "combined_content": ""
        })

        if not extracted_data.get("text"):
            self._update_progress(f"提取PDF文本: {filename}", self._calculate_step_progress(1, 4, 30))
            logger.debug(f"[ContentExtractor] Extracting text from PDF: {filename}")
            text = self.pdf_parser.extract_text(pdf_path)
            if not text:
                logger.error(f"[ContentExtractor] Text extraction failed: {filename}")
                self._update_progress(f"PDF文本提取失败: {filename}", 0)
                self.cache_manager.set_process_status(pdf_path, 'failed', error_message="PDF文本提取失败")
                return {"status": "error", "message": "PDF文本提取失败"}

            extracted_data["text"] = text
            logger.info(f"[ContentExtractor] Text extracted: {len(text)} chars from {filename}")
            self._update_progress(f"提取到 {len(text)} 字符的文本", self._calculate_step_progress(1, 4, 60))
            self.cache_manager.set_process_cache_and_flush(pdf_path, {"extracted_data": extracted_data})
        
        self.cache_manager.set_process_status(pdf_path, 'processing', current_step=2, total_steps=4)

        if not extracted_data.get("images_description"):
            self._check_cancel()
            self._update_progress(f"提取 PDF 图片：{filename}", self._calculate_step_progress(2, 4, 0))
            logger.debug(f"[ContentExtractor] Starting image extraction from {filename}")

            # Smart streaming: use IMAGE_SMART_FILTER to skip B-class (decorative) images
            # and process only A-class (knowledge diagrams) through AI
            # C-class (text/formulas) are handled via OCR callback internally
            images_description = []
            image_count = 0
            ai_processed_count = 0

            def ocr_result_callback(ocr_text, page_num):
                """C类图片OCR结果回调，附加到图片描述中"""
                if ocr_text:
                    images_description.append({
                        "page": page_num,
                        "description": f"[OCR文字] {ocr_text}",
                        "is_ocr": True
                    })

            try:
                # Use smart generator: skips B-class, yields only A-class for AI processing
                for img_data in self.pdf_parser.extract_images_smart_generator(pdf_path, ocr_callback=ocr_result_callback):
                    self._check_cancel()
                    image_count += 1

                    # img_data already has temp_path if it's A-class (from smart generator)
                    temp_path = img_data.get("temp_path")
                    if not temp_path:
                        continue

                    # Progress update for each image processed
                    self._update_progress(
                        f"理解图片 {ai_processed_count}/{image_count} (共提取{len(images_description)}张)",
                        self._calculate_step_progress(2, 4, 10 + min((image_count % 50) * 0.5, 30))
                    )

                    try:
                        # Check cache first
                        cached = self.cache_manager.get_image_cache(temp_path)
                        if cached:
                            description = cached
                        else:
                            # Process single image (5MB limit is checked inside understand_image)
                            description = self.ai_service.understand_image(
                                image_path=temp_path,
                                prompt="这是一张小学教材的图片。请描述图片中的内容，包括其中的文字、公式、图表等信息。如果是数学题目或知识点，请详细说明。如果是图表或插图，请描述其含义。"
                            )
                            if description:
                                self.cache_manager.set_image_cache(temp_path, description)

                        if description:
                            ai_processed_count += 1
                            images_description.append({
                                "page": img_data["page"],
                                "description": description,
                                "value_class": img_data.get("value_class", "A")
                            })

                            # Save progress immediately to disk (support resumable processing)
                            extracted_data["images_description"] = images_description
                            self.cache_manager.set_process_cache_and_flush(pdf_path, {"extracted_data": extracted_data})

                    finally:
                        # Release temp file memory immediately
                        Path(temp_path).unlink(missing_ok=True)

                self._update_progress(
                    f"已理解 {ai_processed_count} 张A类图片 (共跳过 B/C 类 {image_count - ai_processed_count} 张)",
                    self._calculate_step_progress(2, 4, 40)
                )

            except MiniMaxVLMError as e:
                logger.warning(f"[ContentExtractor] Image quota exhausted, skipping image understanding: {e}")
                self._update_progress(f"图片额度耗尽，跳过图片理解: {e}", self._calculate_step_progress(2, 4, 40))
                # Keep whatever images were processed so far

            extracted_data["images_description"] = images_description
            self.cache_manager.set_process_cache_and_flush(pdf_path, {"extracted_data": extracted_data})

        # 更新处理状态
        self.cache_manager.set_process_status(pdf_path, 'processing', current_step=3, total_steps=4)

        # 合并内容
        combined_content = extracted_data["text"]
        if extracted_data["images_description"]:
            combined_content += "\n\n=== 图片内容 ===\n"
            for img_desc in extracted_data["images_description"]:
                combined_content += f"\n[第{img_desc['page']}页图片]: {img_desc['description']}\n"

        extracted_data["combined_content"] = combined_content

        self._check_cancel()
        self._update_progress(f"使用AI提取知识点: {filename}")
        logger.debug(f"[ContentExtractor] Starting AI knowledge extraction for {filename}")

        # 检查内容长度，需要分片处理
        if len(combined_content) > 100000:  # 超过10万字符就分片
            self._update_progress(f"内容过长，需要分片处理...")
            chunks = self.text_splitter.split_text(combined_content)
            self._update_progress(f"已分割为 {len(chunks)} 个分片")
            
            results = []
            for i, chunk in enumerate(chunks):
                self._check_cancel()
                self._update_progress(f"处理第 {i + 1}/{len(chunks)} 个分片")
                knowledge_json = self.ai_service.extract_knowledge(chunk)
                self._check_cancel()
                if knowledge_json:
                    results.append(knowledge_json)
                else:
                    self._update_progress(f"第 {i + 1} 个分片提取失败")
            
            if not results:
                logger.error(f"[ContentExtractor] All chunks failed for {filename}")
                self._update_progress(f"所有分片提取失败: {filename}")
                self.cache_manager.set_process_status(pdf_path, 'failed', error_message="所有分片提取失败")
                return {"status": "error", "message": "知识点提取失败", "extracted_data": extracted_data}
            
            # 合并结果
            self._update_progress("合并分片结果...")
            merged_result = self.text_splitter.merge_results(results)
            knowledge_data = merged_result
        else:
            # 直接处理
            knowledge_json = self.ai_service.extract_knowledge(combined_content)
            if not knowledge_json:
                logger.error(f"[ContentExtractor] Knowledge extraction failed for {filename}")
                self._update_progress(f"知识点提取失败: {filename}")
                self.cache_manager.set_process_status(pdf_path, 'failed', error_message="知识点提取失败")
                return {"status": "error", "message": "知识点提取失败", "extracted_data": extracted_data}
            
            try:
                knowledge_data = json.loads(knowledge_json)
            except json.JSONDecodeError:
                self._update_progress(f"处理完成 (非JSON): {filename}")
                json_filename = Path(pdf_path).name.replace(".pdf", ".json")
                filepath = self.json_dir / f"{subject}_{json_filename}"
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(knowledge_json)
                self.file_status_manager.update_file_status(pdf_path)
                
                # 保存处理结果和状态
                result_data = {
                    "status": "warning",
                    "message": "AI返回的不是有效JSON，已保存原始文本",
                    "file": str(filepath),
                    "extracted_data": {
                        "text_length": len(extracted_data["text"]),
                        "image_count": len(extracted_data["images_description"]),
                        "images_understood": len(extracted_data["images_description"])
                    }
                }
                
                # 保存处理结果到缓存
                self.cache_manager.set_process_result(pdf_path, result_data)
                # 设置处理状态为已完成
                self.cache_manager.set_process_status(pdf_path, 'completed', current_step=4, total_steps=4)
                self.cache_manager.flush()

                return result_data

        self._update_progress(f"保存知识点: {filename}")
        json_filename = Path(pdf_path).name.replace(".pdf", ".json")
        filepath = self.json_dir / f"{subject}_{json_filename}"

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(knowledge_data, f, ensure_ascii=False, indent=2)
            self.file_status_manager.update_file_status(pdf_path)
            
            # 保存处理结果和状态
            result_data = {
                "status": "success",
                "data": knowledge_data,
                "file": str(filepath),
                "extracted_data": {
                    "text_length": len(extracted_data["text"]),
                    "image_count": len(extracted_data["images_description"]),
                    "images_understood": len(extracted_data["images_description"])
                }
            }
            
            # 保存处理结果到缓存
            self.cache_manager.set_process_result(pdf_path, result_data)
            # 设置处理状态为已完成
            self.cache_manager.set_process_status(pdf_path, 'completed', current_step=4, total_steps=4)
            self.cache_manager.flush()

            self._update_progress(f"处理完成: {filename}")
            logger.info(f"[ContentExtractor] PDF processed successfully: {filename} | text={len(extracted_data['text'])} chars, images={len(extracted_data['images_description'])}")
            return result_data
        except Exception as e:
            logger.error(f"[ContentExtractor] Failed to save results for {filename}: {e}")
            self._update_progress(f"保存失败: {e}")
            self.cache_manager.set_process_status(pdf_path, 'failed', error_message=f"保存失败: {e}")
            self.cache_manager.flush()
            return {"status": "error", "message": f"保存失败: {e}", "extracted_data": extracted_data}

    def process_all_pdfs(self):
        """处理所有PDF文档"""
        subjects = ["数学", "语文"]

        results = {}
        total_files = 0
        processed_files = 0
        skipped_files = 0
        modified_files = []

        for subject in subjects:
            files = self.file_status_manager.get_modified_files(subject)
            modified_files.extend(files)

        total_files = len(modified_files)

        if total_files == 0:
            self._update_progress("没有需要处理的文件", 100)
            return {"message": "没有需要处理的文件"}

        self._update_progress(f"开始处理所有PDF文档，共 {total_files} 个文件")

        for pdf_file in modified_files:
            self._check_cancel()
            filename = Path(pdf_file).name
            subject = "数学" if "数学" in pdf_file else "语文"

            # 检查文件是否已完成处理
            if self.cache_manager.is_file_completed(pdf_file):
                result = self.cache_manager.get_process_result(pdf_file)
                if result:
                    self._update_progress(f"文件已处理完成，使用缓存结果: {filename}")
                    if subject not in results:
                        results[subject] = {}
                    results[subject][filename] = result
                    skipped_files += 1
                    processed_files += 1
                    progress = (processed_files / total_files) * 100 if total_files > 0 else 100
                    self._update_progress(f"已处理 {processed_files}/{total_files} 个文件 (跳过 {skipped_files} 个已完成文件)", progress)
                    continue

            result = self.process_pdf(pdf_file, subject)
            self._check_cancel()
            if subject not in results:
                results[subject] = {}
            results[subject][filename] = result

            processed_files += 1
            progress = (processed_files / total_files) * 100 if total_files > 0 else 100
            self._update_progress(f"已处理 {processed_files}/{total_files} 个文件 (跳过 {skipped_files} 个已完成文件)", progress)

        self._update_progress("所有PDF文档处理完成", 100)
        return {
            "extraction_results": results,
            "message": f"共处理 {processed_files} 个文件，跳过 {skipped_files} 个已完成文件"
        }

    def process_selected_files(self, selected_files):
        """处理选定的PDF文档"""
        results = {}
        total_files = len(selected_files)
        processed_files = 0
        success_files = 0
        failed_files = 0
        skipped_files = 0

        if total_files == 0:
            self._update_progress("没有选择文件", 100)
            return {"message": "没有选择文件"}

        self._update_progress(f"开始处理选定的 {total_files} 个文件")

        for file_info in selected_files:
            self._check_cancel()
            pdf_path = file_info.get("path")
            subject = file_info.get("subject")
            filename = Path(pdf_path).name if pdf_path else "未知"

            if not pdf_path or not subject:
                self._update_progress(f"文件信息不完整，跳过")
                continue

            # 检查文件是否已完成处理
            if self.cache_manager.is_file_completed(pdf_path):
                result = self.cache_manager.get_process_result(pdf_path)
                if result:
                    filename = Path(pdf_path).name
                    self._update_progress(f"文件已处理完成，使用缓存结果: {filename}")
                    if subject not in results:
                        results[subject] = {}
                    results[subject][Path(pdf_path).name] = result
                    skipped_files += 1
                    processed_files += 1
                    progress = (processed_files / total_files) * 100 if total_files > 0 else 100
                    self._update_progress(f"已处理 {processed_files}/{total_files} 个文件 (跳过 {skipped_files} 个已完成文件)", progress)
                    continue

            result = self.process_pdf(pdf_path, subject)
            self._check_cancel()
            if subject not in results:
                results[subject] = {}
            results[subject][Path(pdf_path).name] = result

            # Track success/failure based on result status
            if result.get("status") == "success" or result.get("status") == "warning":
                success_files += 1
            else:
                failed_files += 1

            processed_files += 1
            progress = (processed_files / total_files) * 100 if total_files > 0 else 100
            self._update_progress(f"已处理 {processed_files}/{total_files} 个文件 (成功 {success_files} 个，失败 {failed_files} 个)", progress)

        self._update_progress("选定文件处理完成", 100)
        status = "success" if failed_files == 0 else "partial"
        return {
            "status": status,
            "extraction_results": results,
            "message": f"共处理 {processed_files} 个文件，成功 {success_files} 个，失败 {failed_files} 个"
        }

    def get_pending_files(self):
        """获取待处理的文件列表"""
        return self.file_status_manager.get_all_modified_files()