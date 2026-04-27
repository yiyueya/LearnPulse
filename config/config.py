# 配置文件
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
load_dotenv()

# MiniMax API 配置
# 从环境变量获取，如果未设置则返回 None
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_API_URL = os.getenv("MINIMAX_API_URL", "https://api.minimaxi.com/v1")

# 数据存储配置
DATA_DIR = Path("data")
JSON_DIR = DATA_DIR / "json"
KNOWLEDGE_MAP_DIR = DATA_DIR / "knowledge_map"
CACHE_DIR = DATA_DIR / "cache"  # 缓存目录

# PDF 解析配置
PDF_PARSER = "pdfplumber"

# 图片处理配置
IMAGE_PROCESSING_ENABLED = True  # 是否启用图片理解
IMAGE_SMART_FILTER = True  # 是否启用智能图片价值过滤
IMAGE_OCR_THRESHOLD = 0.3  # OCR阈值，C类图片(可OCR)超过此比例则启用OCR
IMAGE_AI_MIN_SIZE = 100  # 需要AI处理的最小图片尺寸(像素)
MIN_IMAGE_SIZE = 0  # 最小图片大小（字节），设置为0表示不限制
MAX_MERGED_SIZE_MB = 5  # 合并后图片的最大大小（MB），MiniMax推荐值
MAX_IMAGES_PER_PDF = 99999  # 每个PDF处理的最大图片数（已移除限制，改为流式处理）
MAX_IMAGE_BATCH_WORKERS = 2  # 图片批处理并发数（WSL 内存受限）

# 缓存配置
CACHE_EXPIRY_DAYS = 7  # 缓存过期天数
MAX_CACHE_SIZE_MB = 100  # 最大缓存大小（MB）

# 知识图谱配置
KNOWLEDGE_GRAPH_TYPE = "networkx"

# 服务配置
HOST = "0.0.0.0"
PORT = 8000

# 日志配置
LOG_LEVEL = "INFO"