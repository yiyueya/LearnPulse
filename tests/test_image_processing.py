# 测试图片处理流程
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.pdf_parser import PDFParser
from src.services.ai_service import AIService
from src.utils.cache_manager import CacheManager

def test_image_processing():
    """测试图片处理流程"""
    print("=" * 60)
    print("图片处理流程测试")
    print("=" * 60)
    
    # 创建实例
    parser = PDFParser()
    ai_service = AIService()
    cache_manager = CacheManager()
    
    # 获取数学 PDF 文件
    pdf_files = parser.get_pdf_files("数学")
    if not pdf_files:
        print("❌ 没有找到数学 PDF 文件")
        return
    
    print(f"✓ 找到 {len(pdf_files)} 个数学 PDF 文件")
    
    # 测试第一个文件
    test_file = pdf_files[0]
    print(f"\n测试文件：{os.path.basename(test_file)}")
    
    # 提取图片
    print("\n1. 提取图片...")
    images = parser.extract_images(test_file)
    print(f"✓ 提取到 {len(images)} 张图片")
    
    if len(images) == 0:
        print("⚠️  没有找到图片，跳过测试")
        return
    
    # 处理前 3 张图片
    test_count = min(3, len(images))
    print(f"\n2. 处理前 {test_count} 张图片...")
    
    for i, img_data in enumerate(images[:test_count]):
        print(f"\n--- 图片 {i+1}/{test_count} ---")
        print(f"页码：{img_data['page']}, 索引：{img_data['index']}, 格式：{img_data['ext']}")
        
        # 保存图片到临时文件
        temp_path = parser.save_image_to_temp(img_data)
        if not temp_path:
            print("❌ 保存图片失败")
            continue
        
        print(f"临时文件：{os.path.basename(temp_path)}")
        print(f"文件大小：{os.path.getsize(temp_path)} 字节")
        
        # 检查缓存
        cached = cache_manager.get_image_cache(temp_path)
        if cached:
            print("✓ 使用缓存结果")
            print(f"描述：{cached[:100]}...")
        else:
            print("⚡ 调用 AI 服务...")
            # 调用 AI 服务
            prompt = "请详细描述这张图片的内容，包括其中的文字、公式、图表等信息"
            description = ai_service.understand_image(
                image_path=temp_path,
                prompt=prompt
            )
            
            if description:
                print(f"✓ AI 返回结果：{description[:100]}...")
                # 保存缓存
                cache_manager.set_image_cache(temp_path, description)
                print("✓ 缓存已保存")
            else:
                print("❌ AI 返回空结果")
        
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    # 显示缓存统计
    print("\n" + "=" * 60)
    print("缓存统计")
    print("=" * 60)
    stats = cache_manager.get_cache_stats()
    print(f"图片缓存数量：{stats['image_cache_count']}")
    print(f"处理缓存数量：{stats['process_cache_count']}")
    print(f"缓存目录：{stats['cache_dir']}")
    
    # 检查缓存文件
    if os.path.exists(stats['cache_dir'] + '/image_cache.json'):
        cache_file = stats['cache_dir'] + '/image_cache.json'
        print(f"\n缓存文件大小：{os.path.getsize(cache_file)} 字节")
        
        # 读取并显示缓存内容
        import json
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            print(f"缓存条目数：{len(cache_data)}")
            if cache_data:
                print("\n缓存内容示例:")
                for hash_key, value in list(cache_data.items())[:2]:
                    print(f"  哈希：{hash_key[:16]}...")
                    print(f"  描述：{value[:100]}...")

if __name__ == "__main__":
    test_image_processing()
