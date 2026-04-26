# PDF 解析工具
import fitz  # PyMuPDF
import pdfplumber
import concurrent.futures
from pathlib import Path
from config.config import DATA_DIR, IMAGE_PROCESSING_ENABLED, MIN_IMAGE_SIZE
from src.utils.cache_manager import CacheManager
from src.utils.logger import logger

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

            # 按文件名排序
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
        """从 PDF 文件中提取图片（带过滤）"""
        images = []
        try:
            doc = fitz.open(pdf_path)
            
            # 定义每页提取图片的函数
            def extract_page_images(page_num):
                page_images = []
                page = doc[page_num]
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # 过滤太小的图片（可能是图标、装饰等）
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
            
            # 并行处理每页
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # 提交所有页面的处理任务
                future_to_page = {executor.submit(extract_page_images, page_num): page_num 
                                 for page_num in range(len(doc))}
                
                # 收集处理结果
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
    
    def save_image_to_temp(self, img_data):
        """保存图片到临时文件"""
        try:
            temp_dir = Path.cwd() / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # 生成唯一的临时文件名
            temp_filename = f"temp_image_{img_data['page']}_{img_data['index']}.{img_data['ext']}"
            temp_path = temp_dir / temp_filename

            with open(temp_path, "wb") as f:
                f.write(img_data["bytes"])

            return str(temp_path)
        except Exception as e:
            logger.error(f"保存临时图片错误: {e}")
            return None

    def get_image_description(self, img_data, ai_service, prompt):
        """获取图片描述，使用缓存（单张处理）"""
        # 保存图片到临时文件
        temp_path = self.save_image_to_temp(img_data)
        if not temp_path:
            return None

        try:
            # 检查缓存
            cached_description = self.cache_manager.get_image_cache(temp_path)
            if cached_description:
                logger.info(f"使用缓存的图片描述 (第{img_data['page']}页)")
                return cached_description

            # 调用 AI 服务获取描述
            description = ai_service.understand_image(
                image_path=temp_path,
                prompt=prompt
            )

            # 缓存结果
            if description:
                self.cache_manager.set_image_cache(temp_path, description)

            return description
        except Exception as e:
            logger.error(f"获取图片描述错误：{e}")
            return None
        finally:
            # 清理临时文件
            temp_path_obj = Path(temp_path)
            if temp_path_obj.exists():
                try:
                    temp_path_obj.unlink()
                except:
                    pass
    
    def get_images_descriptions_batch(self, images_data, ai_service, prompt, progress_callback=None):
        """批量获取多张图片描述，使用缓存
        
        Args:
            images_data: 图片数据列表
            ai_service: AI 服务实例
            prompt: 描述提示
            progress_callback: 进度回调函数，签名为 (current, total, message) -> None
            
        Returns:
            列表：[{page, description}]
        """
        if not IMAGE_PROCESSING_ENABLED:
            print("图片理解功能已禁用")
            return []
        
        total_images = len(images_data)
        
        # 保存所有图片到临时文件（并行）
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
            # 检查缓存（并行）
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
            
            # 批量处理未缓存的图片
            if uncached_paths:
                print(f"需要处理 {len(uncached_paths)} 张未缓存的图片...")
                
                # 使用批量处理
                uncached_path_list = [path for _, path in uncached_paths]
                batch_results = ai_service.understand_images_batch(
                    image_paths=uncached_path_list,
                    prompt=prompt,
                    progress_callback=progress_callback
                )
                
                # 缓存结果（并行）
                def cache_result(img_data_temp_path_description):
                    (img_data, temp_path), description = img_data_temp_path_description
                    if description:
                        self.cache_manager.set_image_cache(temp_path, description)
                        return {
                            "page": img_data["page"],
                            "description": description
                        }
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
            # 清理临时文件（并行）
            def cleanup_temp(temp_path):
                temp_path_obj = Path(temp_path)
                if temp_path_obj.exists():
                    try:
                        temp_path_obj.unlink()
                    except:
                        pass

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                executor.map(cleanup_temp, [temp_path for _, temp_path in temp_paths])