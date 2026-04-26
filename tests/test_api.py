# 测试API的脚本
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    response = requests.get(f"{BASE_URL}/health")
    print("健康检查:", response.json())

def test_process_pdfs():
    """测试PDF处理"""
    print("\n开始处理PDF文档...")
    response = requests.post(f"{BASE_URL}/process_pdfs")
    print("PDF处理结果:", json.dumps(response.json(), ensure_ascii=False, indent=2))

def test_generate_test():
    """测试生成题目"""
    print("\n开始生成测试题目...")
    data = {
        "subject": "数学",
        "grade": "一年级"
    }
    response = requests.post(f"{BASE_URL}/generate_test", json=data)
    print("题目生成结果:", json.dumps(response.json(), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    test_health()
    # test_process_pdfs()  # 注释掉，因为需要AI调用
    # test_generate_test()  # 注释掉，因为需要AI调用