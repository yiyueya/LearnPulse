# 测试AI服务
from src.services.ai_service import AIService

# 创建AI服务实例
ai_service = AIService()

# 测试提取知识点
print("测试AI服务...")
test_text = "小学数学第一单元：加减法。包括10以内的加减法，20以内的进位加法等知识点。"
result = ai_service.extract_knowledge(test_text)
print(f"AI提取结果: {result}")
print("测试完成！")