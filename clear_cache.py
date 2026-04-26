# 清理所有缓存的脚本
import os
import sys

# 自动获取项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def clear_all_caches():
    """清理所有缓存文件"""
    print("=" * 70)
    print("清理所有缓存")
    print("=" * 70)

    sys.path.insert(0, SCRIPT_DIR)
    os.chdir(SCRIPT_DIR)

    from src.utils.cache_manager import CacheManager

    print("\n📦 导入缓存管理器...")
    cache_manager = CacheManager()
    print("✓ 缓存管理器创建成功")

    print("\n🧹 开始清理缓存...")
    cache_manager.clear_all_cache()
    cache_manager.clear_all_status()
    print("✓ 缓存清理完成")

    print("\n🧹 清理临时目录...")
    temp_dir = os.path.join(SCRIPT_DIR, "temp")
    if os.path.exists(temp_dir):
        import shutil
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if item != ".gitkeep":
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
        print(f"✓ 临时目录已清空: {temp_dir}")
    else:
        print(f"⚠️ 临时目录不存在: {temp_dir}")

    print("\n" + "=" * 70)
    print("✅ 所有缓存清理完成！")
    print("=" * 70)

if __name__ == "__main__":
    clear_all_caches()
