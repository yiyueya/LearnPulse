# 测试图片合并策略对比
import os
import sys
import time
from PIL import Image
import requests
import base64
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.pdf_parser import PDFParser
from src.services.ai_service import AIService
from config.config import MINIMAX_API_KEY

def calculate_image_size(img_path):
    """计算图片文件大小（MB）"""
    return os.path.getsize(img_path) / 1024 / 1024

def merge_images_vertically(image_paths, output_path, max_height=10000):
    """垂直合并图片
    
    Args:
        image_paths: 图片路径列表
        output_path: 输出文件路径
        max_height: 最大高度限制
        
    Returns:
        输出文件路径，是否成功
    """
    try:
        imgs = [Image.open(path) for path in image_paths]
        
        # 计算合并后的尺寸
        max_width = max(img.width for img in imgs)
        total_height = sum(img.height for img in imgs)
        
        # 如果超过最大高度，需要分组
        if total_height > max_height:
            return None, False
        
        # 创建合并图片
        combined = Image.new('RGB', (max_width, total_height))
        y_offset = 0
        for img in imgs:
            combined.paste(img, (0, y_offset))
            y_offset += img.height
        
        # 保存
        combined.save(output_path, quality=85, optimize=True)
        return output_path, True
        
    except Exception as e:
        print(f"合并失败：{e}")
        return None, False

def test_single_image(api_service, image_path, prompt):
    """单张图片处理"""
    start = time.time()
    result = api_service.understand_image(image_path=image_path, prompt=prompt)
    elapsed = time.time() - start
    return result, elapsed

def test_merged_images(api_service, image_paths, prompt, test_name):
    """合并图片处理"""
    # 合并图片
    temp_path = image_paths[0] + f'_{test_name}.jpg'
    merged_path, success = merge_images_vertically(image_paths, temp_path)
    
    if not success or not os.path.exists(merged_path):
        print(f"  ❌ {test_name}: 合并失败")
        return None, 0, 0
    
    # 计算大小
    file_size = calculate_image_size(merged_path)
    
    # 处理合并后的图片
    start = time.time()
    result = api_service.understand_image(image_path=merged_path, prompt=prompt)
    elapsed = time.time() - start
    
    # 清理临时文件
    if os.path.exists(temp_path):
        os.remove(temp_path)
    
    return result, elapsed, file_size

def test_progressive_merge(pdf_parser, ai_service, images_data, temp_dir):
    """逐步合并测试：1 张、2 张、3 张...直到接近 20MB"""
    
    print("\n" + "=" * 60)
    print("逐步合并测试")
    print("=" * 60)
    
    prompt = "请详细描述这些图片的内容，包括其中的文字、公式、图表等信息"
    results = []
    
    # 保存所有图片到临时文件
    temp_paths = []
    for i, img_data in enumerate(images_data[:20]):  # 最多测试 20 张
        temp_path = pdf_parser.save_image_to_temp(img_data)
        if temp_path:
            temp_paths.append(temp_path)
    
    if len(temp_paths) < 2:
        print("图片数量不足，跳过测试")
        return
    
    print(f"\n使用 {len(temp_paths)} 张图片进行测试")
    
    # 测试不同合并数量
    for count in [1, 2, 3, 5, 8, 10, 15, 20]:
        if count > len(temp_paths):
            break
        
        test_paths = temp_paths[:count]
        
        # 尝试合并
        test_output = temp_paths[0] + f'_merge{count}.jpg'
        merged_path, success = merge_images_vertically(test_paths, test_output)
        
        if not success:
            print(f"\n{count} 张图片合并：❌ 失败")
            continue
        
        # 检查文件大小
        file_size = calculate_image_size(merged_path)
        
        # 检查是否超过 20MB
        if file_size > 20:
            print(f"\n{count} 张图片合并：⚠️ 超出 20MB 限制 ({file_size:.2f}MB)")
            if os.path.exists(test_output):
                os.remove(test_output)
            break
        
        # 处理合并后的图片
        start = time.time()
        result = ai_service.understand_image(image_path=merged_path, prompt=prompt)
        elapsed = time.time() - start
        
        # 计算平均每张时间
        avg_time = elapsed / count
        
        results.append({
            'count': count,
            'size_mb': file_size,
            'total_time': elapsed,
            'avg_time': avg_time,
            'success': result is not None and len(result) > 0
        })
        
        status = "✓" if results[-1]['success'] else "❌"
        print(f"\n{count} 张图片合并：{status}")
        print(f"  文件大小：{file_size:.2f}MB")
        print(f"  总耗时：{elapsed:.2f}秒")
        print(f"  平均每张：{avg_time:.2f}秒")
        print(f"  识别结果：{'成功' if results[-1]['success'] else '失败'}")
        
        # 清理临时文件
        if os.path.exists(test_output):
            os.remove(test_output)
    
    # 清理所有临时图片
    for path in temp_paths:
        if os.path.exists(path):
            os.remove(path)
    
    # 总结最佳策略
    print("\n" + "=" * 60)
    print("最佳策略分析")
    print("=" * 60)
    
    if results:
        # 找出最接近 20MB 但不超过的配置
        valid_results = [r for r in results if r['size_mb'] < 20 and r['success']]
        
        if valid_results:
            best = max(valid_results, key=lambda x: x['count'])
            print(f"\n✓ 推荐策略：每次合并 {best['count']} 张图片")
            print(f"  文件大小：{best['size_mb']:.2f}MB")
            print(f"  平均每张：{best['avg_time']:.2f}秒")
            print(f"  效率提升：相比单张处理提升约 {(1 - best['avg_time'] / (results[0]['avg_time'] if results[0]['avg_time'] > 0 else 1)) * 100:.1f}%")
        else:
            print("\n⚠️ 所有合并测试都失败了，建议使用单张处理")
    else:
        print("\n⚠️ 没有有效的测试结果")

def test_page_based_merge(pdf_parser, ai_service, images_data, temp_dir):
    """按页面合并测试"""
    
    print("\n" + "=" * 60)
    print("按页面合并测试")
    print("=" * 60)
    
    # 按页码分组
    page_groups = {}
    for img_data in images_data:
        page = img_data['page']
        if page not in page_groups:
            page_groups[page] = []
        page_groups[page].append(img_data)
    
    print(f"\n总页数：{len(page_groups)}")
    print(f"总图片数：{len(images_data)}")
    
    # 统计每页图片数量
    img_counts = [len(imgs) for imgs in page_groups.values()]
    print(f"\n每页图片统计：")
    print(f"- 最多：{max(img_counts)} 张")
    print(f"- 最少：{min(img_counts)} 张")
    print(f"- 平均：{sum(img_counts) / len(img_counts):.1f} 张")
    
    # 测试几页有多个图片的页面
    multi_img_pages = [(page, imgs) for page, imgs in page_groups.items() if len(imgs) > 1]
    
    if not multi_img_pages:
        print("\n✓ 所有页面都只有 1 张图片，无需按页面合并")
        return
    
    print(f"\n测试 {len(multi_img_pages)} 个多图片页面...")
    
    prompt = "请详细描述这些图片的内容"
    total_single_time = 0
    total_merge_time = 0
    
    for page, imgs in multi_img_pages[:5]:  # 测试前 5 页
        # 保存临时文件
        temp_paths = []
        for img_data in imgs:
            temp_path = pdf_parser.save_image_to_temp(img_data)
            if temp_path:
                temp_paths.append(temp_path)
        
        if len(temp_paths) < 2:
            continue
        
        # 单张处理
        print(f"\n第{page}页 ({len(temp_paths)} 张图片):")
        start = time.time()
        for temp_path in temp_paths:
            result = ai_service.understand_image(image_path=temp_path, prompt=prompt)
        single_time = time.time() - start
        total_single_time += single_time
        print(f"  单张处理：{single_time:.2f}秒")
        
        # 合并处理
        merged_path = temp_paths[0] + '_page_merge.jpg'
        merged_path, success = merge_images_vertically(temp_paths, merged_path)
        
        if success and os.path.exists(merged_path):
            file_size = calculate_image_size(merged_path)
            start = time.time()
            result = ai_service.understand_image(image_path=merged_path, prompt=prompt)
            merge_time = time.time() - start
            total_merge_time += merge_time
            
            print(f"  合并处理：{merge_time:.2f}秒 ({file_size:.2f}MB)")
            print(f"  效率提升：{(1 - merge_time / single_time) * 100:.1f}%")
            
            os.remove(merged_path)
        
        # 清理临时文件
        for temp_path in temp_paths:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    if total_single_time > 0 and total_merge_time > 0:
        print(f"\n总计：")
        print(f"- 单张处理：{total_single_time:.2f}秒")
        print(f"- 合并处理：{total_merge_time:.2f}秒")
        print(f"- 效率提升：{(1 - total_merge_time / total_single_time) * 100:.1f}%")

def main():
    """主测试函数"""
    print("=" * 60)
    print("图片合并策略对比测试")
    print("=" * 60)
    
    # 创建实例
    pdf_parser = PDFParser()
    ai_service = AIService()
    
    # 获取测试文件
    pdf_files = pdf_parser.get_pdf_files("数学")
    if not pdf_files:
        print("\n❌ 没有找到 PDF 文件")
        return
    
    test_file = pdf_files[0]
    print(f"\n测试文件：{os.path.basename(test_file)}")
    
    # 提取图片
    print("\n提取图片...")
    images = pdf_parser.extract_images(test_file)
    print(f"✓ 提取到 {len(images)} 张图片")
    
    if len(images) < 10:
        print("图片数量不足，跳过测试")
        return
    
    # 创建临时目录
    temp_dir = os.path.join(os.path.dirname(__file__), '..', 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # 测试 1: 逐步合并
    test_progressive_merge(pdf_parser, ai_service, images, temp_dir)
    
    # 测试 2: 按页面合并
    test_page_based_merge(pdf_parser, ai_service, images, temp_dir)
    
    # 最终建议
    print("\n" + "=" * 60)
    print("最终建议")
    print("=" * 60)
    print("""
根据测试结果，推荐以下策略：

1. 单张图片 (< 5MB):
   - 直接调用 API 处理
   - 简单快速，无额外开销

2. 同页多张图片:
   - 垂直合并后处理
   - 减少 API 调用次数
   - 注意总大小不超过 20MB

3. 跨页图片:
   - 不建议合并
   - 保持独立处理

4. 大图片 (> 15MB):
   - 压缩后处理
   - 或保持单张处理

实现建议：
- 优先使用按页面合并
- 合并前检查总大小
- 超过 18MB 时回退到单张
- 保留缓存机制避免重复处理
    """)
    
    print("\n测试完成！")

if __name__ == "__main__":
    main()
