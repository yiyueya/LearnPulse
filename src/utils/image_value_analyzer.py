# Image Value Analyzer - classifies images by processing value (A/B/C)
import base64
import requests
from pathlib import Path
from PIL import Image
import io

from config.config import MINIMAX_API_KEY, MINIMAX_API_URL
from src.utils.logger import logger


class ImageValueAnalyzer:
    """Classifies images by processing value using rule-based pre-filter and AI quick-check."""

    def __init__(self):
        self.api_key = MINIMAX_API_KEY
        self.api_url = MINIMAX_API_URL

    def analyze(self, image_path: str) -> dict:
        """Analyze image and return classification result.

        Args:
            image_path: Path to the image file

        Returns:
            dict with keys: value_class (A/B/C), reason, width, height, file_size, aspect_ratio
        """
        path = Path(image_path)
        if not path.exists():
            return {
                "value_class": "C",
                "reason": "file_not_found",
                "width": 0,
                "height": 0,
                "file_size": 0,
                "aspect_ratio": 0.0
            }

        file_size = path.stat().st_size
        file_size_kb = file_size / 1024

        try:
            img = Image.open(path)
            width, height = img.size
            aspect_ratio = width / height if height > 0 else 0.0
        except Exception as e:
            logger.warning(f"Failed to open image {image_path}: {e}")
            width, height, aspect_ratio = 0, 0, 0.0

        # Pre-filter rules → classify as B
        if file_size_kb < 15:
            return {
                "value_class": "B",
                "reason": f"file_size_small={file_size_kb:.1f}KB",
                "width": width,
                "height": height,
                "file_size": file_size,
                "aspect_ratio": aspect_ratio
            }

        if width > 0 and width < 100:
            return {
                "value_class": "B",
                "reason": f"width_small={width}px",
                "width": width,
                "height": height,
                "file_size": file_size,
                "aspect_ratio": aspect_ratio
            }

        if aspect_ratio > 0 and aspect_ratio < 0.2:
            return {
                "value_class": "B",
                "reason": f"aspect_ratio_extreme={aspect_ratio:.3f}",
                "width": width,
                "height": height,
                "file_size": file_size,
                "aspect_ratio": aspect_ratio
            }

        # Remaining images get quick AI check via MiniMax coding_plan/vlm
        ai_result = self._quick_ai_check(image_path)
        if ai_result.get("low_value", False):
            return {
                "value_class": "B",
                "reason": ai_result.get("reason", "ai_flagged_low_value"),
                "width": width,
                "height": height,
                "file_size": file_size,
                "aspect_ratio": aspect_ratio
            }

        return {
            "value_class": "A",
            "reason": ai_result.get("reason", "passed_all_filters"),
            "width": width,
            "height": height,
            "file_size": file_size,
            "aspect_ratio": aspect_ratio
        }

    def _quick_ai_check(self, image_path: str) -> dict:
        """Quick AI check using MiniMax coding_plan/vlm to detect low-value images.

        Returns:
            dict with keys: low_value (bool), reason (str)
        """
        try:
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

            prompt = """你是一个图片价值评估专家。请判断这张图片是否值得进行深入的AI知识提取。

图片价值判断标准：
- A类（高价值）：包含重要知识内容，如数学公式、图表、知识点讲解、重要文字内容
- B类（低价值）：装饰性图片、图标、背景图、水印、纯色块、验证码等无知识价值的图片

请用JSON格式返回分析结果：
{
    "value_class": "A" 或 "B",
    "reason": "判断理由（10字以内）"
}

注意：只需返回JSON，不要其他文字。"""

            url = f"{self.api_url}/coding_plan/vlm"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "prompt": prompt,
                "image_url": image_data
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                content = result.get("content", "")
                try:
                    parsed = json.loads(content)
                    return {
                        "low_value": parsed.get("value_class") == "B",
                        "reason": parsed.get("reason", "")
                    }
                except json.JSONDecodeError:
                    # If AI returns non-JSON, be conservative and allow the image through
                    return {"low_value": False, "reason": "ai_response_parse_failed"}
            else:
                # On API failure, allow the image to proceed (conservative)
                logger.warning(f"Quick AI check failed: {response.status_code}")
                return {"low_value": False, "reason": f"api_error_{response.status_code}"}

        except Exception as e:
            logger.warning(f"Quick AI check exception: {e}")
            return {"low_value": False, "reason": "exception_allowing_image"}
