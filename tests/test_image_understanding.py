# 测试PDF图片提取和MiniMax图片理解
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.pdf_parser import PDFParser
from src.services.ai_service import AIService
import os

print("=== 测试PDF图片提取 ===")
parser = PDFParser()
ai_service = AIService()

pdf_files = parser.get_pdf_files("数学")
if pdf_files:
    pdf_path = pdf_files[0]
    print(f"测试文件: {pdf_path}")
    print(f"文件存在: {os.path.exists(pdf_path)}")

    print("\n--- 提取文本 ---")
    text = parser.extract_text(pdf_path)
    print(f"提取文本长度: {len(text)} 字符")
    if text:
        print(f"前200字符:\n{text[:200]}")

    print("\n--- 提取图片 ---")
    images = parser.extract_images(pdf_path)
    print(f"发现图片数量: {len(images)}")

    if images:
        print(f"\n第一张图片信息:")
        img = images[0]
        print(f"  页码: {img['page']}")
        print(f"  索引: {img['index']}")
        print(f"  格式: {img['ext']}")
        print(f"  尺寸: {img['width']}x{img['height']}")
        print(f"  大小: {img['size']} bytes")

        print("\n--- 保存并理解第一张图片 ---")
        temp_path = parser.save_image_to_temp(img)
        if temp_path:
            print(f"临时文件路径: {temp_path}")

            description = ai_service.understand_image(
                image_path=temp_path,
                prompt="这是一张小学教材的图片。请描述图片中的内容，如果是数学题目或知识点，请详细说明。"
            )
            print(f"\n图片理解结果:\n{description}")

            os.remove(temp_path)
            print("\n临时文件已删除")
else:
    print("没有找到PDF文件")