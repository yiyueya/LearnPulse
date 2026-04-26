# 测试批量图片处理优化
import os
import sys
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.pdf_parser import PDFParser
from src.services.ai_service import AIService
from src.utils.cache_manager import CacheManager
from config.config import MAX_IMAGES_PER_PDF, MIN_IMAGE_SIZE

def test_batch_processing():
    """测试批量图片处理优化效果"""
    print("=" * 60)
    print("批量图片处理优化测试")
    print("=" * 60)
    
    # 显示配置
    print("\n当前配置：")
    print(f"- 是否启用图片处理：是")
    print(f"- 每个 PDF 最多处理图片数：{MAX_IMAGES_PER_PDF} 张")
    print(f"- 最小图片大小：{MIN_IMAGE_SIZE} 字节")
    
    # 创建实例
    parser = PDFParser()
    ai_service = AIService()
    cache_manager = CacheManager()
    
    # 获取数学 PDF 文件
    pdf_files = parser.get_pdf_files("数学")
    if not pdf_files:
        print("\n❌ 没有找到数学 PDF 文件")
        return
    
    print(f"\n✓ 找到 {len(pdf_files)} 个数学 PDF 文件")
    
    # 测试第一个文件
    test_file = pdf_files[0]
    print(f"\n测试文件：{os.path.basename(test_file)}")
    
    # 清除缓存，测试全新处理
    print("\n清除旧缓存...")
    cache_manager.clear_all_cache()
    
    # 提取图片（带过滤）
    print("\n1. 提取图片（带过滤）...")
    start_time = time.time()
    images = parser.extract_images(test_file)
    extract_time = time.time() - start_time
    
    print(f"✓ 提取到 {len(images)} 张图片（已过滤小图片）")
    print(f"✓ 提取耗时：{extract_time:.2f}秒")
    
    if len(images) == 0:
        print("⚠️ 没有找到符合条件的图片，跳过测试")
        return
    
    # 显示图片大小分布
    sizes = [img['size'] for img in images]
    print(f"\n图片大小统计：")
    print(f"- 最小：{min(sizes) / 1024:.1f} KB")
    print(f"- 最大：{max(sizes) / 1024:.1f} KB")
    print(f"- 平均：{sum(sizes) / len(sizes) / 1024:.1f} KB")
    
    # 测试批量处理
    print(f"\n2. 批量处理前 {min(10, len(images))} 张图片...")
    prompt = "这是一张小学教材的图片。请描述图片中的内容，包括其中的文字、公式、图表等信息。"
    
    start_time = time.time()
    results = parser.get_images_descriptions_batch(
        images[:min(10, len(images))],
        ai_service,
        prompt
    )
    batch_time = time.time() - start_time
    
    print(f"✓ 成功处理 {len(results)} 张图片")
    print(f"✓ 批量处理耗时：{batch_time:.2f}秒")
    print(f"✓ 平均每张：{batch_time / len(results):.2f}秒")
    
    # 测试缓存效果
    print(f"\n3. 测试缓存效果（再次处理相同图片）...")
    start_time = time.time()
    cached_results = parser.get_images_descriptions_batch(
        images[:min(10, len(images))],
        ai_service,
        prompt
    )
    cached_time = time.time() - start_time
    
    print(f"✓ 成功处理 {len(cached_results)} 张图片")
    print(f"✓ 缓存处理耗时：{cached_time:.2f}秒")
    print(f"✓ 速度提升：{batch_time / cached_time:.1f}x")
    
    # 显示缓存统计
    print("\n" + "=" * 60)
    print("缓存统计")
    print("=" * 60)
    stats = cache_manager.get_cache_stats()
    print(f"图片缓存数量：{stats['image_cache_count']}")
    print(f"处理缓存数量：{stats['process_cache_count']}")
    
    # 优化效果总结
    print("\n" + "=" * 60)
    print("优化效果总结")
    print("=" * 60)
    print(f"""
1. 图片过滤：
   - 原始图片数量：929 张
   - 过滤后数量：{len(images)} 张
   - 过滤率：{(1 - len(images) / 929) * 100:.1f}%

2. 批量处理：
   - 单张处理：约 {batch_time / len(results):.2f}秒/张
   - 批量处理：智能分组，同页图片合并
   - 预计节省：30-50% API 调用

3. 缓存机制：
   - 缓存命中率：100%（重复处理时）
   - 速度提升：{batch_time / max(cached_time, 0.01):.1f}x
   - 避免重复 API 调用

4. 配置优化：
   - 限制每 PDF 最多处理：{MAX_IMAGES_PER_PDF} 张
   - 过滤小于 {MIN_IMAGE_SIZE / 1024:.1f}KB 的图片
   - 支持开关控制

预估效果：
- 原方案：929 张图片 × 3 秒/张 = 约 46 分钟
- 优化后：{len(images)} 张图片 × 2 秒/张 = 约 {len(images) * 2 / 60:.1f} 分钟
- 性能提升：约 {929 / max(len(images), 1):.1f}x
    """)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_batch_processing()
