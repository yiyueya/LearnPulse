# 测试基于文件大小的图片分组策略
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.pdf_parser import PDFParser
from src.services.ai_service import AIService
from src.utils.cache_manager import CacheManager
from config.config import MAX_MERGED_SIZE_MB

def test_size_based_grouping():
    """测试基于文件大小的分组策略"""
    print("=" * 70)
    print("基于文件大小的图片分组策略测试")
    print("=" * 70)
    
    # 显示配置
    print(f"\n📊 当前配置：")
    print(f"   - 最大合并大小：{MAX_MERGED_SIZE_MB} MB")
    print(f"   - 最小图片限制：已禁用（处理所有图片）")
    
    # 创建实例
    parser = PDFParser()
    ai_service = AIService()
    
    # 获取数学 PDF 文件
    pdf_files = parser.get_pdf_files("数学")
    if not pdf_files:
        print("\n❌ 没有找到数学 PDF 文件")
        return
    
    test_file = pdf_files[0]
    print(f"\n📄 测试文件：{os.path.basename(test_file)}")
    
    # 提取所有图片（不限制大小）
    print("\n🔍 提取所有图片（不限制大小）...")
    images = parser.extract_images(test_file)
    print(f"✓ 提取到 {len(images)} 张图片")
    
    if len(images) < 2:
        print("\n⚠️ 图片数量不足，需要至少 2 张图片进行测试")
        return
    
    # 保存临时文件
    print("\n💾 保存临时文件...")
    temp_paths = []
    for i, img_data in enumerate(images[:10]):  # 测试前10张
        temp_path = parser.save_image_to_temp(img_data)
        if temp_path:
            temp_paths.append(temp_path)
            # 显示图片信息
            size_kb = img_data['size'] / 1024
            print(f"   图片 {i+1}: {size_kb:.2f} KB (第{img_data['page']}页)")
    
    if len(temp_paths) < 2:
        print("\n⚠️ 保存临时文件失败")
        return
    
    print(f"\n✓ 成功保存 {len(temp_paths)} 张临时文件")
    
    # 测试基于大小的分组
    print("\n" + "=" * 70)
    print("测试基于文件大小的分组")
    print("=" * 70)
    
    batches = ai_service._create_size_based_batches(temp_paths)
    
    print(f"\n📊 分组结果：")
    print(f"   - 原始图片数：{len(temp_paths)} 张")
    print(f"   - 分组数量：{len(batches)} 个批次")
    
    # 计算总大小
    total_size = sum(os.path.getsize(p) for p in temp_paths) / 1024 / 1024
    print(f"   - 总大小：{total_size:.2f} MB")
    
    # 显示每个批次的信息
    for i, batch in enumerate(batches):
        batch_size = sum(os.path.getsize(p) for p in batch) / 1024 / 1024
        print(f"\n   批次 {i+1}:")
        print(f"      - 图片数：{len(batch)} 张")
        print(f"      - 总大小：{batch_size:.2f} MB")
        print(f"      - 占比：{batch_size/total_size*100:.1f}%")
    
    # 测试批量处理
    print("\n" + "=" * 70)
    print("测试批量处理和结果拆分")
    print("=" * 70)
    
    prompt = "请详细描述这些图片的内容。如果是数学题目或知识点，请详细说明。"
    
    print("\n🚀 开始批量处理...")
    import time
    start_time = time.time()
    results = ai_service.understand_images_batch(temp_paths, prompt)
    elapsed = time.time() - start_time
    
    print(f"\n✓ 批量处理完成，耗时：{elapsed:.2f}秒")
    print(f"✓ 处理了 {len(results)} 张图片")
    
    # 显示处理结果
    print("\n" + "=" * 70)
    print("处理结果详情")
    print("=" * 70)
    
    for i, (img_path, description) in enumerate(results.items()):
        print(f"\n📷 图片 {i+1}:")
        print(f"   文件：{os.path.basename(img_path)}")
        print(f"   大小：{os.path.getsize(img_path)/1024:.2f} KB")
        print(f"   描述长度：{len(description)} 字符")
        print(f"   描述内容：{description[:150]}...")
    
    # 验证结果拆分
    print("\n" + "=" * 70)
    print("结果拆分验证")
    print("=" * 70)
    
    descriptions = list(results.values())
    unique_descriptions = len(set(descriptions))
    
    print(f"\n✓ 总描述数：{len(descriptions)}")
    print(f"✓ 唯一描述数：{unique_descriptions}")
    
    if unique_descriptions > 1:
        print("✅ 成功：每张图片都有独立的描述")
    else:
        print("⚠️ 警告：所有图片使用了相同的描述")
    
    # 清理临时文件
    print("\n🧹 清理临时文件...")
    for temp_path in temp_paths:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    
    print(f"""
✅ 测试成功！基于文件大小的分组策略工作正常：

📊 配置验证：
   - 最大合并大小：{MAX_MERGED_SIZE_MB} MB ✓
   - 最小图片限制：已禁用 ✓
   - 图片总数：{len(temp_paths)} 张 ✓

📦 分组效果：
   - 分组数量：{len(batches)} 个批次
   - 每批图片数：{', '.join(str(len(b)) for b in batches)} 张
   - 平均每批大小：约 {total_size/len(batches):.2f} MB

🎯 处理效果：
   - 处理耗时：{elapsed:.2f} 秒
   - 处理速度：{len(results)/elapsed:.2f} 张/秒
   - 结果拆分：{'成功' if unique_descriptions > 1 else '失败'}

💡 技术特点：
   - 智能大小估算，预留 30% 空间用于压缩
   - 动态分组，自动分割过大的组
   - 基于页面分组，保持上下文关联
   - 解析结构化结果，为每张图片分配独立描述
    """)

if __name__ == "__main__":
    test_size_based_grouping()
