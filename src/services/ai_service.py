# AI服务模块
import requests
import base64
import hashlib
import json
import concurrent.futures
from pathlib import Path
from functools import lru_cache
from config.config import MINIMAX_API_KEY, MINIMAX_API_URL, MAX_MERGED_SIZE_MB, CACHE_DIR, MAX_IMAGE_BATCH_WORKERS
from src.utils.logger import logger

class AIService:
    """AI服务，用于与MiniMax API交互"""

    def __init__(self):
        self.api_key = MINIMAX_API_KEY
        self.api_url = MINIMAX_API_URL
        # 初始化缓存目录
        self.cache_dir = CACHE_DIR or Path(__file__).parent.parent.parent / 'temp' / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # 内存缓存
        self.image_cache = {}
        self.batch_cache = {}

    def _get_cache_key(self, image_path, prompt):
        """生成缓存键"""
        with open(image_path, 'rb') as f:
            img_hash = hashlib.md5(f.read()).hexdigest()
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        return f"{img_hash}_{prompt_hash}"

    def _get_batch_cache_key(self, image_paths, prompt):
        """生成批量处理的缓存键"""
        # 对图片路径排序，确保顺序不影响缓存键
        sorted_paths = sorted(image_paths)
        paths_str = '_'.join([Path(p).name for p in sorted_paths])
        paths_hash = hashlib.md5(paths_str.encode()).hexdigest()
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        return f"batch_{paths_hash}_{prompt_hash}"

    def _load_from_cache(self, cache_key):
        """从缓存加载数据"""
        # 先检查内存缓存
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        # 再检查文件缓存
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 存入内存缓存
                    self.image_cache[cache_key] = data
                    return data
            except Exception as e:
                print(f"加载缓存失败: {e}")
        
        return None

    def _save_to_cache(self, cache_key, data):
        """保存数据到缓存"""
        # 存入内存缓存
        self.image_cache[cache_key] = data

        # 存入文件缓存
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存缓存失败: {e}")

    def extract_knowledge(self, text, max_retries=3):
        """从文本中提取知识点

        Args:
            text: 输入文本
            max_retries: 最大重试次数

        Returns:
            str: JSON格式的知识点字符串，失败返回空字符串
        """
        # JSON schema示例
        json_schema_example = """{
    "knowledge_points": [
        {
            "name": "知识点名称",
            "subject": "数学或语文",
            "grade": "年级",
            "content": "知识点详细描述"
        }
    ]
}"""

        system_prompt = f"""你是一个教育专家，擅长从教材中提取知识点。

【关键要求】你必须且只能返回JSON格式的数据，不要包含任何其他文字、解释或 markdown 代码块标记。

返回格式必须符合以下JSON Schema：
{json_schema_example}

如果返回的内容不是纯JSON格式，将被视为失败。"""

        user_prompt = f"从以下文本中提取小学数学/语文的知识点:\n{text}"

        for attempt in range(max_retries):
            try:
                url = f"{self.api_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                # 根据重试次数调整提示词严格程度
                if attempt > 0:
                    strict_prompt = system_prompt + "\n\n【警告】上次返回的不是有效JSON，请务必只返回纯JSON数据，不要添加任何其他内容。"
                else:
                    strict_prompt = system_prompt

                payload = {
                    "model": "MiniMax-M2.7",
                    "messages": [
                        {"role": "system", "content": strict_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                }

                response = requests.post(url, headers=headers, json=payload, timeout=120)

                if response.status_code == 200:
                    result = response.json()
                    raw_content = result["choices"][0]["message"]["content"]

                    # 验证是否为有效JSON
                    try:
                        # 尝试解析JSON
                        json.loads(raw_content)
                        # 如果解析成功，直接返回
                        return raw_content
                    except json.JSONDecodeError:
                        logger.warning(f"第 {attempt + 1} 次尝试：AI返回的不是有效JSON")
                        if attempt < max_retries - 1:
                            logger.info(f"重试中... ({attempt + 1}/{max_retries})")
                        else:
                            logger.error(f"提取知识点失败，已尝试 {max_retries} 次，所有尝试均未返回有效JSON")
                            return ""
                else:
                    logger.error(f"AI API调用失败: {response.status_code}, {response.text}")
                    if response.status_code == 529:
                        wait_time = (2 ** (attempt + 1)) * 2
                    else:
                        wait_time = 2 ** (attempt + 1)
                    if attempt < max_retries - 1:
                        logger.info(f"等待 {wait_time} 秒后重试...")
                        import time
                        time.sleep(wait_time)
            except Exception as e:
                logger.error(f"AI提取知识点错误: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    import time
                    time.sleep(wait_time)

        logger.error(f"提取知识点失败，已尝试 {max_retries} 次")
        return ""

    def understand_image(self, image_path=None, image_url=None, prompt="描述这张图片的内容", max_retries=3):
        """使用MiniMax API理解图片内容

        Args:
            image_path: 本地图片路径
            image_url: 网络图片URL
            prompt: 对图片的提问
            max_retries: 最大重试次数

        Returns:
            图片理解结果文本
        """
        # 开始计时
        if image_path:
            timer_key = f"understand_image_{Path(image_path).name}"
        else:
            timer_key = "understand_image_url"
        logger.start_timer(timer_key)

        # 检查缓存（仅支持本地图片路径）
        if image_path:
            cache_key = self._get_cache_key(image_path, prompt)
            cached_result = self._load_from_cache(cache_key)
            if cached_result:
                logger.info(f"从缓存加载结果: {Path(image_path).name}")
                logger.stop_timer(timer_key)
                logger.log_performance(timer_key, "图片理解（缓存）")
                return cached_result

        retries = 0
        while retries < max_retries:
            try:
                url = "https://api.minimaxi.com/v1/coding_plan/vlm"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                if image_path:
                    with open(image_path, "rb") as img_file:
                        img_base64 = base64.b64encode(img_file.read()).decode("utf-8")
                        if image_path.lower().endswith(".png"):
                            mime_type = "image/png"
                        elif image_path.lower().endswith((".jpg", ".jpeg")):
                            mime_type = "image/jpeg"
                        elif image_path.lower().endswith(".gif"):
                            mime_type = "image/gif"
                        elif image_path.lower().endswith(".webp"):
                            mime_type = "image/webp"
                        else:
                            mime_type = "image/jpeg"
                        image_data = f"data:{mime_type};base64,{img_base64}"
                elif image_url:
                    image_data = image_url
                else:
                    logger.error("必须提供image_path或image_url")
                    return ""

                payload = {
                    "prompt": prompt,
                    "image_url": image_data
                }

                response = requests.post(url, headers=headers, json=payload, timeout=120)

                if response.status_code == 200:
                    result = response.json()
                    content = result.get("content", "")
                    # 保存到缓存（仅支持本地图片路径）
                    if image_path:
                        self._save_to_cache(cache_key, content)
                    logger.stop_timer(timer_key)
                    logger.log_performance(timer_key, "图片理解（API）")
                    return content
                else:
                    logger.error(f"图片理解API调用失败: {response.status_code}, {response.text}")
                    retries += 1
                    if retries < max_retries:
                        # 对于 529 错误（服务器拥挤）使用指数退避
                        wait_time = 2 ** retries  # 指数退避：2, 4, 8 秒
                        if response.status_code == 529:
                            wait_time = wait_time * 2  # 服务器拥挤时等待时间翻倍
                        logger.info(f"重试中... ({retries}/{max_retries})，等待 {wait_time} 秒")
                        import time
                        time.sleep(wait_time)
            except Exception as e:
                logger.error(f"图片理解错误：{e}")
                retries += 1
                if retries < max_retries:
                    # 对于异常也使用指数退避
                    wait_time = 2 ** retries
                    logger.info(f"重试中... ({retries}/{max_retries})，等待 {wait_time} 秒")
                    import time
                    time.sleep(wait_time)

        # 重试失败
        logger.error(f"图片理解失败，已尝试 {max_retries} 次")
        logger.stop_timer(timer_key)
        logger.log_performance(timer_key, "图片理解（失败）")
        return ""

    def understand_images_batch(self, image_paths, prompt="描述这些图片的内容", progress_callback=None):
        """批量处理多张图片（基于文件大小的动态分组）
        
        基于文件大小的智能分组策略：
        - 按页面分组
        - 动态计算合并后文件大小
        - 确保每组不超过 MAX_MERGED_SIZE_MB (5MB)
        - 自动分割过大的组
        
        Args:
            image_paths: 图片路径列表
            prompt: 对图片的提问
            
        Returns:
            字典：{图片路径：描述}
        """
        # 开始计时
        timer_key = f"understand_images_batch_{len(image_paths)}_images"
        logger.start_timer(timer_key)
        
        results = {}
        total_images = len(image_paths)
        
        # 直接按文件大小分批（移除按页面分组，以便更好地合并图片）
        all_batches = self._create_size_based_batches(image_paths)
        
        logger.info(f"批量处理 {total_images} 张图片，分为 {len(all_batches)} 个批次")
        
        if progress_callback:
            progress_callback(0, total_images, f"准备处理 {total_images} 张图片...")
        
        # 并行处理批次
        if all_batches:
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_IMAGE_BATCH_WORKERS) as executor:
                # 提交所有批次的处理任务
                future_to_batch = {}
                for batch in all_batches:
                    # 检查批次缓存
                    batch_cache_key = self._get_batch_cache_key(batch, prompt)
                    cached_batch_results = self._load_from_cache(batch_cache_key)

                    if cached_batch_results:
                        # 从缓存加载，直接处理
                        logger.info(f"从缓存加载批次结果: {len(batch)} 张图片")
                        for i, img_path in enumerate(batch):
                            if i < len(cached_batch_results):
                                results[img_path] = cached_batch_results[i]
                                if progress_callback:
                                    progress_callback(len(results), total_images, f"从缓存加载第 {len(results)}/{total_images} 张图片...")
                    else:
                        # 构造批次内回调（用于报告批次内部进度）
                        def make_batch_callback(base_count):
                            def batch_cb(sub_msg):
                                if progress_callback:
                                    progress_callback(base_count, total_images, sub_msg)
                            return batch_cb
                        base_count = len(results)
                        batch_cb = make_batch_callback(base_count)
                        # 提交到线程池处理
                        future = executor.submit(self._process_image_batch, batch, prompt, batch_cb)
                        future_to_batch[future] = (batch, batch_cache_key)

                # 收集处理结果
                processed_count = len(results)
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch, batch_cache_key = future_to_batch[future]
                    try:
                        batch_results = future.result()
                        results.update(batch_results)
                        processed_count += len(batch_results)

                        # 保存到缓存
                        if batch_results:
                            batch_result_list = list(batch_results.values())
                            self._save_to_cache(batch_cache_key, batch_result_list)

                        if progress_callback:
                            progress_callback(processed_count, total_images, f"处理第 {processed_count}/{total_images} 张图片...")
                    except Exception as e:
                        logger.error(f"处理批次失败: {e}")

        if progress_callback:
            progress_callback(total_images, total_images, f"图片理解完成，已处理 {total_images} 张")
        
        logger.stop_timer(timer_key)
        logger.log_performance(timer_key, f"批量处理 {len(image_paths)} 张图片")
        return results
    
    def _create_size_based_batches(self, image_paths):
        """基于文件大小创建批次
        
        Args:
            image_paths: 图片路径列表
            
        Returns:
            批次列表，每个批次不超过 MAX_MERGED_SIZE_MB
        """
        if not image_paths:
            return []
        
        batches = []
        current_batch = []
        current_size = 0
        max_size_bytes = MAX_MERGED_SIZE_MB * 1024 * 1024  # 转换为字节
        
        for img_path in image_paths:
            try:
                # 估算合并后的大小（实际合并后会更小，这里用原始大小估算）
                img_size = Path(img_path).stat().st_size
                
                # 预留 30% 空间用于压缩
                estimated_size = img_size * 0.7
                
                # 检查是否超过限制
                if current_size + estimated_size > max_size_bytes:
                    # 保存当前批次
                    if current_batch:
                        batches.append(current_batch)
                    # 开始新批次
                    current_batch = [img_path]
                    current_size = estimated_size
                else:
                    # 添加到当前批次
                    current_batch.append(img_path)
                    current_size += estimated_size
            except Exception as e:
                print(f"获取文件大小失败：{e}")
                # 无法获取大小，单独处理
                batches.append([img_path])
        
        # 添加最后一个批次
        if current_batch:
            batches.append(current_batch)
        
        print(f"\n基于大小分组：{len(image_paths)} 张图片 → {len(batches)} 个批次")
        for i, batch in enumerate(batches):
            try:
                batch_size = sum(Path(p).stat().st_size for p in batch) / 1024 / 1024
                print(f"  批次 {i+1}: {len(batch)} 张图片, 估算大小: {batch_size:.2f}MB")
            except:
                pass
        
        return batches
    
    def _process_image_batch(self, group_images, prompt, progress_callback=None):
        """处理一组图片（合并或单张）

        Args:
            group_images: 图片路径列表
            prompt: 提示词
            progress_callback: 进度回调，签名为 (msg: str) -> None

        Returns:
            字典：{图片路径：描述}
        """
        def cb(msg):
            if progress_callback:
                progress_callback(msg)

        results = {}

        if len(group_images) == 1:
            cb("单张图片直接识别...")
            img_path = group_images[0]
            description = self.understand_image(image_path=img_path, prompt=prompt)
            if description:
                results[img_path] = description
            cb("单张图片识别完成")
            return results

        cb(f"开始处理 {len(group_images)} 张图片，准备合并...")

        # 多张图片尝试合并处理
        try:
            from PIL import Image, ImageDraw

            # 打开所有图片，统一转换为 RGB
            imgs = []
            img_info = []  # 保存原始路径和页码信息
            for i, img_path in enumerate(group_images):
                try:
                    img = Image.open(img_path)
                    if img.mode == 'RGBA':
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    imgs.append(img)
                    import re
                    match = re.search(r'temp_image_(\d+)_(\d+)', img_path)
                    page_num = match.group(1) if match else str(i + 1)
                    img_info.append((img_path, page_num))
                    cb(f"加载图片 {i+1}/{len(group_images)}")
                except Exception as e:
                    print(f"警告：无法打开图片 {img_path}，跳过: {e}")
                    continue

            if not imgs:
                print("警告：没有可用的图片")
                return results

            # 计算合并后的尺寸
            max_width = max(img.width for img in imgs)
            total_height = sum(img.height for img in imgs)
            sep_height = 40
            num_seps = len(imgs) - 1
            combined_height = total_height + num_seps * sep_height

            cb(f"合并尺寸: {len(imgs)} 张, 最大宽度 {max_width}px, 总高度 {total_height}px")

            # 检查是否会超过 PIL 的限制
            if total_height > 100000 or max_width > 50000:
                cb(f"尺寸过大({max_width}x{total_height})，回退到逐张处理")
                temp_path_obj = Path(temp_path)
                if temp_path_obj.exists():
                    temp_path_obj.unlink()
                return self._process_image_batch_fallback(group_images, prompt, progress_callback)

            # 创建合并图片
            cb(f"合并图片中...")
            combined = Image.new('RGB', (max_width, combined_height), (240, 240, 240))
            y_offset = 0
            for i, img in enumerate(imgs):
                x_offset = (max_width - img.width) // 2
                combined.paste(img, (x_offset, y_offset))
                y_offset += img.height
                if i < num_seps:
                    sep = Image.new('RGB', (max_width, sep_height), (200, 200, 200))
                    draw = ImageDraw.Draw(sep)
                    draw.line([(0, 0), (max_width, 0)], fill=(180, 180, 180), width=2)
                    _, _, text_w, text_h = draw.textbbox((0, 0), f"第 {img_info[i][1]} 页")
                    text_x = max_width // 2 - text_w // 2
                    text_y = sep_height // 2 - text_h // 2 + 2
                    draw.text((text_x, text_y), f"第 {img_info[i][1]} 页", fill=(120, 120, 120))
                    combined.paste(sep, (0, y_offset))
                    y_offset += sep_height
                cb(f"合并进度: {i+1}/{len(imgs)}")

            # 保存临时文件
            temp_path = group_images[0] + '_combined.jpg'
            combined.save(temp_path, quality=85, optimize=True)
            file_size_mb = Path(temp_path).stat().st_size / 1024 / 1024
            cb(f"合并完成, 文件大小: {file_size_mb:.2f}MB")

            if file_size_mb < MAX_MERGED_SIZE_MB:
                page_list = "\n".join(f"[图片 {i+1}] 对应原PDF第 {img_info[i][1]} 页" for i in range(len(imgs)))
                enhanced_prompt = f"""{prompt}

图片按从上到下顺序分别是：
{page_list}

请严格按以下格式返回，每张图片对应一个描述：

[图片 1]
第1张图片的详细描述

[图片 2]
第2张图片的详细描述

...

[图片 N]
第N张图片的详细描述
"""
                cb("AI 识别合并图片中...")
                description = self.understand_image(image_path=temp_path, prompt=enhanced_prompt)
                if description:
                    parsed_results = self._parse_batch_result(description, len(group_images))
                    if parsed_results and len(parsed_results) >= len(group_images):
                        for i, img_path in enumerate(group_images):
                            results[img_path] = parsed_results[i]
                        cb("解析成功，分配结果")
                    else:
                        cb("批量解析失败，回退到逐张识别")
                        temp_path_obj = Path(temp_path)
                        if temp_path_obj.exists():
                            temp_path_obj.unlink()
                        return self._process_image_batch_fallback(group_images, prompt, progress_callback)
            else:
                cb(f"文件过大({file_size_mb:.2f}MB>{MAX_MERGED_SIZE_MB}MB)，逐张处理")
                temp_path_obj = Path(temp_path)
                if temp_path_obj.exists():
                    temp_path_obj.unlink()
                return self._process_image_batch_fallback(group_images, prompt, progress_callback)

            temp_path_obj = Path(temp_path)
            if temp_path_obj.exists():
                temp_path_obj.unlink()

        except Exception as e:
            cb(f"处理异常: {e}，回退到逐张处理")
            return self._process_image_batch_fallback(group_images, prompt, progress_callback)

        return results

    def _process_image_batch_fallback(self, group_images, prompt, progress_callback=None):
        """逐张处理图片（降级方案）"""
        def cb(msg):
            if progress_callback:
                progress_callback(msg)

        results = {}
        for i, img_path in enumerate(group_images):
            cb(f"逐张识别中({i+1}/{len(group_images)})...")
            description = self.understand_image(image_path=img_path, prompt=prompt)
            if description:
                results[img_path] = description
        cb(f"逐张识别完成")
        return results
    
    def _parse_batch_result(self, result_text, image_count):
        """解析批量处理的结果，拆分出每张图片的描述
        
        Args:
            result_text: AI 返回的文本
            image_count: 图片数量
            
        Returns:
            列表：每张图片的描述
        """
        try:
            # 按 [图片 X] 模式拆分
            import re
            pattern = r'\[图片\s*(\d+)\]'
            parts = re.split(pattern, result_text)
            
            # 提取描述
            descriptions = []
            for i in range(1, len(parts), 2):
                # parts[i] 是数字，parts[i+1] 是描述
                description = parts[i+1].strip()
                if description:
                    descriptions.append(description)
            
            # 确保数量匹配
            if len(descriptions) >= image_count:
                return descriptions[:image_count]
            elif len(descriptions) > 0:
                # 数量不足，重复使用最后一个描述
                while len(descriptions) < image_count:
                    descriptions.append(descriptions[-1])
                return descriptions
            else:
                return None
                
        except Exception as e:
            print(f"解析结果失败：{e}")
            return None

    def generate_questions(self, knowledge_points, subject, grade, question_type="mixed", question_count=10):
        """基于知识点生成题目"""
        try:
            url = f"{self.api_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 根据题型生成不同描述
            type_map = {
                "mixed": "选择题、填空题、判断题",
                "choice": "选择题",
                "fill": "填空题",
                "judge": "判断题",
            }
            type_desc = type_map.get(question_type, "选择题、填空题、判断题")

            payload = {
                "model": "MiniMax-M2.7",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个教育专家，擅长根据知识点生成题目。"
                    },
                    {
                        "role": "user",
                        "content": f"基于以下知识点为{grade}年级{subject}学科生成{question_count}道{type_desc}，返回JSON格式数组:\n{knowledge_points}"
                    }
                ]
            }

            response = requests.post(url, headers=headers, json=payload, timeout=120)

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"AI API调用失败: {response.status_code}, {response.text}")
                return ""
        except Exception as e:
            print(f"AI生成题目错误: {e}")
            return ""

    def evaluate_answer(self, question, answer):
        """评估答案正确性"""
        try:
            url = f"{self.api_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "MiniMax-M2.7",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个教育专家，擅长评估学生答案的正确性。"
                    },
                    {
                        "role": "user",
                        "content": f"评估以下答案是否正确，并提供解析:\n题目: {question}\n答案: {answer}"
                    }
                ]
            }

            response = requests.post(url, headers=headers, json=payload, timeout=120)

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"AI API调用失败: {response.status_code}, {response.text}")
                return ""
        except Exception as e:
            print(f"AI评估答案错误: {e}")
            return ""