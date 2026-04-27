# PDF 解析工具
import fitz  # PyMuPDF
import pdfplumber
import concurrent.futures
from pathlib import Path
from config.config import (
    DATA_DIR, IMAGE_PROCESSING_ENABLED, MIN_IMAGE_SIZE,
    IMAGE_SMART_FILTER, IMAGE_OCR_THRESHOLD, IMAGE_AI_MIN_SIZE
)
from src.utils.cache_manager import CacheManager
from src.utils.logger import logger
from src.utils.image_value_analyzer import ImageValueAnalyzer

class PDFParser:
    """PDF解析工具，用于提取文本和图片"""

    def __init__(self):
        self.data_dir = DATA_DIR
        self.cache_manager = CacheManager()

    def get_pdf_files(self, subject):
        """获取指定学科的PDF文件列表"""
        try:
            subject_dir = self.data_dir / subject
            if not subject_dir.exists():
                return []

            pdf_files = []
            for file in subject_dir.iterdir():
                if file.suffix == ".pdf":
                    pdf_files.append(str(file))

            pdf_files.sort()
            return pdf_files
        except Exception as e:
            logger.error(f"获取PDF文件列表错误: {e}")
            return []
    
    def extract_text(self, pdf_path):
        """从PDF文件中提取文本"""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"PDF解析错误: {e}")
            return ""
    
    def extract_images(self, pdf_path):
        """从 PDF 文件中提取图片（返回列表，保持向后兼容）"""
        images = []
        try:
            doc = fitz.open(pdf_path)

            def extract_page_images(page_num):
                page_images = []
                page = doc[page_num]
                image_list = page.get_images(full=True)

                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    if MIN_IMAGE_SIZE > 0 and len(image_bytes) < MIN_IMAGE_SIZE:
                        continue

                    page_images.append({
                        "page": page_num + 1,
                        "bytes": image_bytes,
                        "ext": image_ext,
                        "index": img_index,
                        "size": len(image_bytes)
                    })
                return page_images

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_to_page = {executor.submit(extract_page_images, page_num): page_num
                                 for page_num in range(len(doc))}

                for future in concurrent.futures.as_completed(future_to_page):
                    try:
                        page_images = future.result()
                        images.extend(page_images)
                    except Exception as e:
                        print(f"处理页面图片失败: {e}")

            doc.close()
            return images
        except Exception as e:
            logger.error(f"提取图片错误：{e}")
            return []

    def extract_images_smart_generator(self, pdf_path, ocr_callback=None):
        """智能提取并分类图片（生成器版本，避免内存堆积）
        
        仅返回 A 类（知识图示）和 C 类（文字/公式，需OCR）图片。
        B 类（装饰插画）直接跳过，不占用内存。
        
        Yields img_data dicts with added fields: value_class, reason, width, height, file_size
        """
        if not IMAGE_SMART_FILTER:
            # 智能过滤关闭时，返回所有图片（按原流程处理）
            for img_data in self.extract_images_generator(pdf_path):
                img_data["value_class"] = "A"
                img_data["reason"] = "smart_filter disabled"
                yield img_data
            return
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            analyzer = ImageValueAnalyzer(
                min_file_size_kb=15,
                min_dimension=IMAGE_AI_MIN_SIZE
            )
            
            for page_num in range(total_pages):
                page = doc[page_num]
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    if MIN_IMAGE_SIZE > 0 and len(image_bytes) < MIN_IMAGE_SIZE:
                        continue
                    
                    img_data = {
                        "page": page_num + 1,
                        "bytes": image_bytes,
                        "ext": image_ext,
                        "index": img_index,
                        "size": len(image_bytes)
                    }
                    
                    # 保存临时文件用于分析
                    temp_path = self.save_image_to_temp(img_data)
                    if not temp_path:
                        continue
                    
                    try:
                        analysis = analyzer.analyze(temp_path)
                        value_class = analysis["value_class"]
                        
                        # B类装饰插画：跳过，不占用AI额度
                        if value_class == "B":
                            logger.debug(f"[SmartFilter] Page {page_num+1} img {img_index}: B类装饰，跳过")
                            Path(temp_path).unlink(missing_ok=True)
                            continue
                        
                        # C类文字/公式：做OCR
                        if value_class == "C":
                            logger.debug(f"[SmartFilter] Page {page_num+1} img {img_index}: C类，执行OCR")
                            if ocr_callback:
                                try:
                                    from PIL import Image
                                    import pytesseract
                                    pil_img = Image.open(temp_path)
                                    ocr_text = pytesseract.image_to_string(pil_img, lang="chi_sim+eng")
                                    if ocr_text.strip():
                                        ocr_callback(ocr_text.strip(), page_num + 1)
                                    pil_img.close()
                                except Exception as e:
                                    logger.debug(f"OCR failed for page {page_num+1}: {e}")
                            Path(temp_path).unlink(missing_ok=True)
                            continue
                        
                        # A类知识图示：带分析结果yield
                        img_data["value_class"] = value_class
                        img_data["reason"] = analysis.get("reason", "")
                        img_data["width"] = analysis.get("width", 0)
                        img_data["height"] = analysis.get("height", 0)
                        img_data["file_size"] = analysis.get("file_size", 0)
                        img_data["aspect_ratio"] = analysis.get("aspect_ratio", 0)
                        img_data["temp_path"] = temp_path  # 保留temp_path让caller清理
                        
                        yield img_data
                        
                    except Exception as e:
                        logger.warning(f"Image analysis failed: {e}")
                        Path(temp_path).unlink(missing_ok=True)
            
            doc.close()
        except Exception as e:
            logger.error(f"提取图片错误（智能生成器）：{e}")
            return

    def extract_images_generator(self, pdf_path):
        """从 PDF 文件中提取图片（生成器版本，避免内存堆积）

        Yields images one at a time instead of loading all into memory.
        Each yielded image has its bytes cleared after processing to release memory.
        """
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            for page_num in range(total_pages):
                page = doc[page_num]
                image_list = page.get_images(full=True)

                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    if MIN_IMAGE_SIZE > 0 and len(image_bytes) < MIN_IMAGE_SIZE:
                        continue

                    img_data = {
                        "page": page_num + 1,
                        "bytes": image_bytes,
                        "ext": image_ext,
                        "index": img_index,
                        "size": len(image_bytes)
                    }
                    yield img_data

            doc.close()
        except Exception as e:
            logger.error(f"提取图片错误（生成器）：{e}")
            return

    def save_image_to_temp(self, img_data):
        """保存图片到临时文件"""
        try:
            temp_dir = Path.cwd() / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            temp_filename = f"temp_image_{img_data['page']}_{img_data['index']}.{img_data['ext']}"
            temp_path = temp_dir / temp_filename

            with open(temp_path, "wb") as f:
                f.write(img_data["bytes"])

            return str(temp_path)
        except Exception as e:
            logger.error(f"保存临时图片错误: {e}")
            return None

    def extract_images_smart(self, pdf_path, ocr_callback=None):
        """智能提取并分类图片
        
        Args:
            pdf_path: PDF 文件路径
            ocr_callback: 可选回调，用于C类图片的OCR结果 (ocr_text, page_num)
            
        Returns:
            dict: {
                "a_images": [...],  # 知识图示，需AI分析
                "b_images": [...],  # 装饰插画，跳过
                "c_images": [...],  # 文字/公式，OCR处理
                "a_count": int,
                "b_count": int, 
                "c_count": int,
                "total": int
            }
        """
        if not IMAGE_SMART_FILTER:
            # 智能过滤关闭时，返回所有图片为 A 类
            images = self.extract_images(pdf_path)
            return {
                "a_images": [{"page": img["page"], "bytes": img["bytes"], 
                              "ext": img["ext"], "index": img["index"], 
                              "size": img["size"]} for img in images],
                "b_images": [],
                "c_images": [],
                "a_count": len(images),
                "b_count": 0,
                "c_count": 0,
                "total": len(images)
            }
        
        images = self.extract_images(pdf_path)
        if not images:
            return {"a_images": [], "b_images": [], "c_images": [],
                    "a_count": 0, "b_count": 0, "c_count": 0, "total": 0}

        result = {"a_images": [], "b_images": [], "c_images": [],
                  "a_count": 0, "b_count": 0, "c_count": 0, "total": len(images)}

        # 保存图片到临时文件
        temp_data = []
        for img_data in images:
            temp_path = self.save_image_to_temp(img_data)
            if temp_path:
                temp_data.append({**img_data, "temp_path": temp_path})

        if not temp_data:
            return result

        analyzer = ImageValueAnalyzer(
            min_file_size_kb=15,
            min_dimension=IMAGE_AI_MIN_SIZE
        )

        for img in temp_data:
            try:
                analysis = analyzer.analyze(img["temp_path"])
                value_class = analysis["value_class"]
                
                categorized = {
                    "page": img["page"],
                    "bytes": img["bytes"],
                    "ext": img["ext"],
                    "index": img["index"],
                    "size": img["size"],
                    "temp_path": img["temp_path"],
                    "value_class": value_class,
                    "reason": analysis.get("reason", ""),
                    "width": analysis.get("width", 0),
                    "height": analysis.get("height", 0),
                    "file_size": analysis.get("file_size", 0),
                    "aspect_ratio": analysis.get("aspect_ratio", 0)
                }
                
                if value_class == "A":
                    result["a_images"].append(categorized)
                    result["a_count"] += 1
                elif value_class == "B":
                    result["b_images"].append(categorized)
                    result["b_count"] += 1
                    # B类直接清理临时文件
                    Path(img["temp_path"]).unlink(missing_ok=True)
                else:  # C 或 needs_ai_check
                    result["c_images"].append(categorized)
                    result["c_count"] += 1
                    # C类做OCR
                    if ocr_callback:
                        try:
                            from PIL import Image
                            import pytesseract
                            pil_img = Image.open(img["temp_path"])
                            ocr_text = pytesseract.image_to_string(pil_img, lang="chi_sim+eng")
                            if ocr_text.strip():
                                ocr_callback(ocr_text.strip(), img["page"])
                            pil_img.close()
                        except Exception as e:
                            logger.debug(f"OCR failed for page {img['page']}: {e}")
                        finally:
                            Path(img["temp_path"]).unlink(missing_ok=True)
                    else:
                        # 无callback也清理
                        Path(img["temp_path"]).unlink(missing_ok=True)
                        
            except Exception as e:
                logger.warning(f"Image analysis failed: {e}")

        logger.info(f"图片分类结果: A类={result['a_count']}, B类={result['b_count']}, C类={result['c_count']}")
        return result
    
    def get_image_description(self, img_data, ai_service, prompt):
        """获取图片描述，使用缓存"""
        temp_path = self.save_image_to_temp(img_data)
        if not temp_path:
            return None

        try:
            cached_description = self.cache_manager.get_image_cache(temp_path)
            if cached_description:
                logger.info(f"使用缓存的图片描述 (第{img_data['page']}页)")
                return cached_description

            description = ai_service.understand_image(
                image_path=temp_path,
                prompt=prompt
            )

            if description:
                self.cache_manager.set_image_cache(temp_path, description)

            return description
        except Exception as e:
            logger.error(f"获取图片描述错误：{e}")
            return None
        finally:
            temp_path_obj = Path(temp_path)
            if temp_path_obj.exists():
                try:
                    temp_path_obj.unlink()
                except:
                    pass
    
    def get_images_descriptions_batch(self, images_data, ai_service, prompt, progress_callback=None):
        """批量获取多张图片描述"""
        if not IMAGE_PROCESSING_ENABLED:
            print("图片理解功能已禁用")
            return []
        
        total_images = len(images_data)
        
        temp_paths = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_to_img = {executor.submit(self.save_image_to_temp, img_data): img_data 
                           for img_data in images_data}
            
            for future in concurrent.futures.as_completed(future_to_img):
                img_data = future_to_img[future]
                try:
                    temp_path = future.result()
                    if temp_path:
                        temp_paths.append((img_data, temp_path))
                except Exception as e:
                    print(f"保存临时图片失败: {e}")
        
        if not temp_paths:
            return []
        
        try:
            results = []
            uncached_paths = []
            
            def check_cache(img_data_temp_path):
                img_data, temp_path = img_data_temp_path
                cached = self.cache_manager.get_image_cache(temp_path)
                if cached:
                    print(f"使用缓存：第{img_data['page']}页图片")
                    return {
                        "page": img_data["page"],
                        "description": cached,
                        "is_cached": True
                    }
                else:
                    return {
                        "img_data": img_data,
                        "temp_path": temp_path,
                        "is_cached": False
                    }
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_to_result = {executor.submit(check_cache, (img_data, temp_path)): (img_data, temp_path) 
                                   for img_data, temp_path in temp_paths}
                
                for future in concurrent.futures.as_completed(future_to_result):
                    result = future.result()
                    if result["is_cached"]:
                        results.append(result)
                        if progress_callback:
                            progress_callback(len(results), total_images, f"从缓存加载第 {len(results)}/{total_images} 张图片...")
                    else:
                        uncached_paths.append((result["img_data"], result["temp_path"]))
            
            if uncached_paths:
                print(f"需要处理 {len(uncached_paths)} 张未缓存的图片...")
                
                uncached_path_list = [path for _, path in uncached_paths]
                batch_results = ai_service.understand_images_batch(
                    image_paths=uncached_path_list,
                    prompt=prompt,
                    progress_callback=progress_callback
                )
                
                def cache_result(img_data_temp_path_description):
                    (img_data, temp_path), description = img_data_temp_path_description
                    if description:
                        self.cache_manager.set_image_cache(temp_path, description)
                        return {"page": img_data["page"], "description": description}
                    return None
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    future_to_result = {executor.submit(cache_result, ((img_data, temp_path), batch_results.get(temp_path, ""))): 
                                       (img_data, temp_path) for img_data, temp_path in uncached_paths}
                    
                    for future in concurrent.futures.as_completed(future_to_result):
                        result = future.result()
                        if result:
                            results.append(result)
            
            return results
        except Exception as e:
            print(f"批量获取图片描述错误：{e}")
            return []
        finally:
            def cleanup_temp(temp_path):
                temp_path_obj = Path(temp_path)
                if temp_path_obj.exists():
                    try:
                        temp_path_obj.unlink()
                    except:
                        pass

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                executor.map(cleanup_temp, [temp_path for _, temp_path in temp_paths])