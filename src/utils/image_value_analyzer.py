# 图片价值分析器 - 纯规则版本
# 通过视觉特征分析（颜色复杂度、边缘密度、线条检测）判断图片类型
# A = 知识图示 B = 装饰插画 C = 文字/公式
# 原则：宁可把B判成A，也不要把A判成B（保守策略）

from pathlib import Path
from PIL import Image
import json
import hashlib

class ImageValueAnalyzer:
    """图片价值分析器 - 纯规则版本"""
    
    # 保守阈值：宁可误判为A也不漏判真实A类
    COLOR_COMPLEXITY_HIGH = 50    # 颜色数>50视为复杂装饰图
    COLOR_COMPLEXITY_LOW = 20     # 颜色数<20视为简单知识图
    EDGE_DENSITY_LINE_THRESHOLD = 0.15  # 直线边缘密度阈值
    ASPECT_RATIO_MIN = 0.2        # 长宽比极端值
    ASPECT_RATIO_MAX = 5.0
    MIN_FILE_SIZE_KB = 15
    MIN_DIMENSION = 100
    
    def __init__(self, 
                 color_complexity_threshold=COLOR_COMPLEXITY_HIGH,
                 min_dimension=MIN_DIMENSION,
                 min_file_size_kb=MIN_FILE_SIZE_KB):
        self.color_complexity_threshold = color_complexity_threshold
        self.min_dimension = min_dimension
        self.min_file_size_kb = min_file_size_kb
    
    def analyze(self, image_path) -> dict:
        """分析图片价值（纯规则，无需AI）
        
        Returns:
            dict: {
                "value_class": "A" | "B" | "C",
                "reason": str,
                "width": int,
                "height": int,
                "file_size": int,
                "color_count": int,
                "edge_density": float
            }
        """
        path = Path(image_path)
        result = {
            "path": str(path),
            "width": 0,
            "height": 0,
            "file_size": 0,
            "color_count": 0,
            "edge_density": 0.0,
            "aspect_ratio": 0.0,
            "value_class": "B",
            "reason": ""
        }
        
        # 1. 文件大小检查
        try:
            result["file_size"] = path.stat().st_size
        except Exception:
            result["reason"] = "无法获取文件大小"
            return result
        
        if result["file_size"] < self.min_file_size_kb * 1024:
            result["reason"] = f"文件过小({result['file_size']/1024:.1f}KB)，装饰图标"
            return result
        
        # 2. 图片尺寸和基本信息
        try:
            with Image.open(path) as img:
                result["width"], result["height"] = img.size
        except Exception:
            result["reason"] = "无法读取图片"
            return result
        
        if result["width"] < self.min_dimension or result["height"] < self.min_dimension:
            result["reason"] = f"尺寸过小({result['width']}x{result['height']})"
            return result
        
        # 3. 长宽比检查
        aspect_ratio = result["width"] / result["height"] if result["height"] > 0 else 0
        result["aspect_ratio"] = aspect_ratio
        
        if aspect_ratio < self.ASPECT_RATIO_MIN or aspect_ratio > self.ASPECT_RATIO_MAX:
            result["reason"] = f"长宽比极端({aspect_ratio:.2f})，横幅/超窄图"
            return result
        
        # 4. 颜色复杂度分析
        color_count = self._analyze_color_complexity(path)
        result["color_count"] = color_count
        
        # 5. 边缘密度分析（判断是否知识图）
        edge_density = self._analyze_edge_density(path)
        result["edge_density"] = edge_density
        
        # 6. 综合判断
        return self._make_classification(result, color_count, edge_density)
    
    def _analyze_color_complexity(self, image_path) -> int:
        """分析颜色复杂度
        装饰图（照片/插画）通常颜色丰富、渐变多
        知识图（几何/表格）通常颜色少、色块分明
        """
        try:
            with Image.open(image_path) as img:
                # 缩小到 64x64 加速分析
                img = img.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS)
                
                # 统计颜色数量（量子化减少误差）
                pixels = img.getdata()
                
                # 颜色量子化：将RGB每个通道分成8级
                color_buckets = {}
                for r, g, b in pixels:
                    qr = r // 32
                    qg = g // 32
                    qb = b // 32
                    key = (qr, qg, qb)
                    color_buckets[key] = color_buckets.get(key, 0) + 1
                
                # 考虑颜色分布的均匀度
                unique_colors = len(color_buckets)
                
                # 检查是否有大量渐变（颜色逐渐变化）
                # 如果相邻像素颜色相近度高，说明是渐变（装饰图特征）
                diff_count = 0
                pixels_list = list(pixels)
                for i in range(len(pixels_list) - 1):
                    r1, g1, b1 = pixels_list[i]
                    r2, g2, b2 = pixels_list[i+1]
                    # 计算颜色差异
                    diff = abs(r1-r2) + abs(g1-g2) + abs(b1-b2)
                    if diff > 30:  # 差异明显
                        diff_count += 1
                
                gradient_ratio = diff_count / max(len(pixels_list) - 1, 1)
                
                # 综合判断：颜色多+渐变多 = 装饰图
                # 颜色少+渐变少 = 知识图
                is_gradient_heavy = gradient_ratio > 0.4
                
                if is_gradient_heavy and unique_colors > 40:
                    return unique_colors  # 装饰图特征
                else:
                    return unique_colors
                    
        except Exception as e:
            return 0
    
    def _analyze_edge_density(self, image_path) -> float:
        """分析边缘密度
        知识图（几何、表格）有大量直线和规则边缘
        装饰图（照片、插画）边缘复杂、曲线多
        """
        try:
            with Image.open(image_path) as img:
                # 转为灰度
                gray = img.convert("L").resize((100, 100), Image.Resampling.LANCZOS)
                
                # 简单的边缘检测：Sobel-like 算子
                pixels = list(gray.getdata())
                width, height = 100, 100
                
                # 计算水平梯度Gx和垂直梯度Gy
                edge_energy = 0
                line_score = 0  # 直线得分
                
                for y in range(1, height - 1):
                    for x in range(1, width - 1):
                        idx = y * width + x
                        # Sobel算子
                        Gx = (pixels[idx - width + 1] + 2 * pixels[idx + 1] + pixels[idx + width + 1]) - \
                             (pixels[idx - width - 1] + 2 * pixels[idx - 1] + pixels[idx + width - 1])
                        Gy = (pixels[idx + width - 1] + 2 * pixels[idx + width] + pixels[idx + width + 1]) - \
                             (pixels[idx - width - 1] + 2 * pixels[idx - width] + pixels[idx - width + 1])
                        
                        edge_magnitude = (Gx**2 + Gy**2) ** 0.5
                        edge_energy += edge_magnitude
                        
                        # 检测是否为直线边缘（梯度方向一致性好）
                        if edge_magnitude > 50:
                            angle = abs(Gx) / max(abs(Gy), 0.001)
                            # 接近0度或90度的角度视为直线
                            if angle < 0.3 or angle > 3.0:
                                line_score += 1
                
                # 归一化
                total_pixels = (width - 2) * (height - 2)
                edge_density = edge_energy / (total_pixels * 500)  # 归一化到0-1
                line_ratio = line_score / max(total_pixels * 0.1, 1)
                
                # 综合得分：高边缘密度+高直线比=知识图
                return min(edge_density * 2 + line_ratio * 0.5, 1.0)
                
        except Exception:
            return 0.0
    
    def _make_classification(self, result, color_count, edge_density) -> dict:
        """综合判断图片类型
        
        判断逻辑：
        1. 颜色极度丰富(>60) → B类装饰图（照片级复杂插画）
        2. 颜色很少(<20) 且 边缘密度高 → A类知识图
        3. 颜色适中但边缘密度高 → A类知识图（可能是表格/几何图）
        4. 颜色丰富但边缘也高 → C类文字图（可能是截图）
        5. 其他情况 → A类（保守策略，不漏掉知识图）
        """
        
        # 装饰图特征：颜色非常丰富（照片/精美插画）
        if color_count > self.COLOR_COMPLEXITY_HIGH:
            result["value_class"] = "B"
            result["reason"] = f"颜色丰富({color_count}种)，判定为装饰插画"
            return result
        
        # 知识图特征：颜色少 + 边缘清晰/规则
        if color_count <= self.COLOR_COMPLEXITY_LOW and edge_density > 0.1:
            result["value_class"] = "A"
            result["reason"] = f"颜色简洁({color_count}种)+边缘清晰，判定为知识图示"
            return result
        
        # 边缘密度高（可能有线条/图表）
        if edge_density > self.EDGE_DENSITY_LINE_THRESHOLD:
            if color_count < 40:
                result["value_class"] = "A"
                result["reason"] = f"线条/边缘密集(edge={edge_density:.2f})，判定为知识图示"
                return result
            else:
                # 颜色多但边缘规则，可能是文字截图
                result["value_class"] = "C"
                result["reason"] = f"颜色中等({color_count}种)+边缘规则，疑似文字截图"
                return result
        
        # 默认保守策略：判为A，不漏掉知识图
        result["value_class"] = "A"
        if color_count < 30:
            result["reason"] = f"颜色适中({color_count}种)，归类为知识图示"
        else:
            result["reason"] = f"无法明确判断，保守归类为A类"
        
        return result
    
    def classify(self, image_path) -> str:
        """快速分类，仅返回类型字母"""
        result = self.analyze(image_path)
        return result["value_class"]


def quick_classify(image_path) -> str:
    """快速分类函数"""
    analyzer = ImageValueAnalyzer()
    return analyzer.classify(image_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python image_value_analyzer.py <图片路径>")
        sys.exit(1)
    
    path = sys.argv[1]
    analyzer = ImageValueAnalyzer()
    result = analyzer.analyze(path)
    
    print(f"图片: {result['path']}")
    print(f"尺寸: {result['width']}x{result['height']}")
    print(f"文件大小: {result['file_size']/1024:.1f}KB")
    print(f"颜色数: {result['color_count']}")
    print(f"边缘密度: {result['edge_density']:.3f}")
    print(f"长宽比: {result['aspect_ratio']:.2f}")
    print(f"分类: {result['value_class']} - {result['reason']}")