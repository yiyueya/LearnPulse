# 测试PDF解析功能
from src.utils.pdf_parser import PDFParser
import os

# 创建PDFParser实例
parser = PDFParser()

# 获取数学PDF文件列表
pdf_files = parser.get_pdf_files("数学")
print(f"找到 {len(pdf_files)} 个数学PDF文件:")

# 测试提取第一个文件的文本
if pdf_files:
    first_file = pdf_files[0]
    print(f"\n测试文件: {first_file}")
    print(f"文件是否存在: {os.path.exists(first_file)}")

    text = parser.extract_text(first_file)
    print(f"提取文本长度: {len(text)} 字符")

    if text:
        print(f"前200个字符:\n{text[:200]}")
    else:
        print("文本提取失败！")
else:
    print("没有找到PDF文件")