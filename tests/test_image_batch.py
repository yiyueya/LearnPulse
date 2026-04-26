# 测试 MiniMax 图片处理限制
import os
import sys
import requests
import base64
from PIL import Image
import io

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.config import MINIMAX_API_KEY

def test_image_size_limit():
    """测试 MiniMax 图片大小限制"""
    print("=" * 60)
    print("MiniMax 图片处理限制测试")
    print("=" * 60)
    
    # MiniMax 官方文档限制
    print("\nMiniMax 图片处理限制：")
    print("- 最大支持：20MB")
    print("- 支持格式：JPEG, PNG, GIF, WebP")
    print("- 推荐尺寸：小于 5MB")
    
    # 测试批量处理
    print("\n" + "=" * 60)
    print("批量处理图片测试")
    print("=" * 60)
    
    api_key = MINIMAX_API_KEY
    url = "https://api.minimaxi.com/v1/coding_plan/vlm"
    
    # 获取测试图片
    test_dir = os.path.join(os.path.dirname(__file__), '..', 'temp')
    if not os.path.exists(test_dir):
        print(f"临时目录不存在：{test_dir}")
        return
    
    image_files = [f for f in os.listdir(test_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
    
    if not image_files:
        print("没有找到测试图片")
        return
    
    print(f"\n找到 {len(image_files)} 张测试图片")
    
    # 测试单张图片
    if image_files:
        test_image = os.path.join(test_dir, image_files[0])
        file_size = os.path.getsize(test_image) / 1024 / 1024  # MB
        print(f"\n测试图片：{image_files[0]}")
        print(f"文件大小：{file_size:.2f} MB")
        
        # 打开图片获取尺寸
        with Image.open(test_image) as img:
            print(f"图片尺寸：{img.width} x {img.height}")
    
    # 测试批量处理策略
    print("\n" + "=" * 60)
    print("批量处理策略建议")
    print("=" * 60)
    
    print("""
1. 单张图片处理：
   - 优点：简单可靠，错误隔离
   - 缺点：API 调用次数多，速度慢
   
2. 图片拼接后处理：
   - 优点：减少 API 调用次数
   - 缺点：
     * 需要额外的图片处理
     * 可能超出 20MB 限制
     * 图片过多会导致识别质量下降

3. 智能分组处理（推荐）：
   - 按页面分组，每页图片合并
   - 控制每组总大小在 5MB 以内
   - 平衡速度和识别质量

推荐方案：
- 每页图片合并成一张图
- 每组不超过 5MB
- 每组不超过 5 张图片
- 保持单张处理作为备选
    """)
    
    # 测试图片拼接
    print("\n" + "=" * 60)
    print("测试图片拼接功能")
    print("=" * 60)
    
    if len(image_files) >= 2:
        # 读取前两张图片
        img1_path = os.path.join(test_dir, image_files[0])
        img2_path = os.path.join(test_dir, image_files[1])
        
        try:
            img1 = Image.open(img1_path)
            img2 = Image.open(img2_path)
            
            # 计算拼接后的尺寸
            max_width = max(img1.width, img2.width)
            total_height = img1.height + img2.height
            
            print(f"\n拼接后尺寸：{max_width} x {total_height}")
            
            # 创建拼接图片
            combined = Image.new('RGB', (max_width, total_height))
            combined.paste(img1, (0, 0))
            combined.paste(img2, (0, img1.height))
            
            # 保存测试
            output_path = os.path.join(test_dir, 'combined_test.jpg')
            combined.save(output_path, quality=85)
            
            combined_size = os.path.getsize(output_path) / 1024 / 1024
            print(f"拼接后大小：{combined_size:.2f} MB")
            
            if combined_size < 20:
                print("✓ 拼接图片大小在限制范围内")
            else:
                print("⚠ 拼接图片超出 20MB 限制")
                
        except Exception as e:
            print(f"拼接失败：{e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_image_size_limit()
