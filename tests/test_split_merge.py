# 测试分片和合并功能
import sys
sys.path.insert(0, "d:/code/AILearning")

from src.utils.text_splitter import TextSplitter

print("=== 测试分片和合并功能 ===")

# 创建分片器，设置较小的阈值便于测试
splitter = TextSplitter(max_tokens=1000)  # 约2000字符

# 生成测试文本
test_text = """
# 小学数学知识点

## 1. 数的认识
### 1.1 自然数
自然数是用来表示物体个数的数，包括0、1、2、3、4、5、6、7、8、9……
自然数的计数单位是"1"，任何自然数都是由若干个"1"组成的。

### 1.2 整数
整数包括正整数、0和负整数。
正整数：1、2、3、4、5……
0：表示一个也没有
负整数：-1、-2、-3、-4、-5……

## 2. 数的运算
### 2.1 加法
加法是将两个或多个数合并成一个数的运算。
加法的交换律：a + b = b + a
加法的结合律：(a + b) + c = a + (b + c)

### 2.2 减法
减法是已知两个加数的和与其中一个加数，求另一个加数的运算。
减法是加法的逆运算。

### 2.3 乘法
乘法是求几个相同加数的和的简便运算。
乘法的交换律：a × b = b × a
乘法的结合律：(a × b) × c = a × (b × c)
乘法的分配律：(a + b) × c = a × c + b × c

### 2.4 除法
除法是已知两个因数的积与其中一个因数，求另一个因数的运算。
除法是乘法的逆运算。
"""

# 生成较长的文本
extended_text = test_text * 5  # 5倍长度
print(f"原始文本长度: {len(test_text)} 字符")
print(f"扩展后文本长度: {len(extended_text)} 字符")
print(f"最大分片大小: {splitter.max_chars} 字符")

# 测试分片
print("\n--- 测试分片 ---\n")
chunks = splitter.split_text(extended_text)
print(f"分割为 {len(chunks)} 个分片")

total_length = 0
for i, chunk in enumerate(chunks):
    chunk_length = len(chunk)
    total_length += chunk_length
    print(f"分片 {i+1}: {chunk_length} 字符")
    print(f"前50字符: {chunk[:50]}...")
    print()

print(f"\n总字符数: {total_length}")
print(f"与原始长度一致: {total_length == len(extended_text)}")

# 测试合并功能
print("\n--- 测试合并功能 ---\n")
test_results = [
    '{"knowledge_points": [{"chapter": "1. 数的认识", "topics": [{"name": "1.1 自然数", "content": "自然数是用来表示物体个数的数"}]}]}',
    '{"knowledge_points": [{"chapter": "2. 数的运算", "topics": [{"name": "2.1 加法", "content": "加法是将两个或多个数合并成一个数的运算"}]}]}',
    '{"knowledge_points": [{"chapter": "1. 数的认识", "topics": [{"name": "1.1 自然数", "content": "自然数是用来表示物体个数的数"}]}]}'  # 重复内容
]

merged = splitter.merge_results(test_results)
print(f"合并后知识点数量: {merged.get('total_points', 0)}")
print(f"知识点: {merged.get('knowledge_points', [])}")

# 测试带代码块的结果
print("\n--- 测试带代码块的结果合并 ---\n")
code_block_result = '''
```json
{
  "knowledge_points": [
    {
      "chapter": "3. 小数",
      "topics": [
        {
          "name": "3.1 小数的意义",
          "content": "小数是分数的另一种表现形式"
        }
      ]
    }
  ]
}
```
'''

code_result = splitter.merge_results([code_block_result])
print(f"合并后知识点数量: {code_result.get('total_points', 0)}")
print(f"知识点: {code_result.get('knowledge_points', [])}")

print("\n=== 测试完成 ===")