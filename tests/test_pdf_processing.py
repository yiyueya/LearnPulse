# 测试PDF处理功能
from src.agents.content_extractor_agent import ContentExtractorAgent

# 创建ContentExtractorAgent实例	extractor = ContentExtractorAgent()

# 定义进度回调函数
def progress_callback(progress):
    print(f"进度: {progress['message']} - {progress.get('progress', 'N/A')}%")

# 设置进度回调	extractor.set_progress_callback(progress_callback)

# 处理PDF文档
print("开始处理PDF文档...")
result = extractor.process_all_pdfs()
print("处理完成！")
print(f"结果: {result}")