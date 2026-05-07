# 日志和性能监控模块
import logging
import time
from pathlib import Path
from datetime import datetime


class Logger:
    """日志和性能监控类"""

    def __init__(self):
        # 创建日志目录
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # 每日日志文件
        log_file = log_dir / f"app_{datetime.now().strftime('%Y-%m-%d')}.log"

        # 格式: 时间 | 模块名 | 级别 | 消息
        formatter = logging.Formatter(
            "%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 文件处理器 - DEBUG级别，写入当天的日志文件
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        # 控制台处理器 - INFO级别
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)

        # 根日志记录器
        self.logger = logging.getLogger("LearnPulse")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []  # 避免重复handler
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # 性能监控数据
        self.performance_data = {}

    def debug(self, message):
        """记录调试日志"""
        self.logger.debug(message)

    def info(self, message):
        """记录信息日志"""
        self.logger.info(message)

    def warning(self, message):
        """记录警告日志"""
        self.logger.warning(message)

    def error(self, message, exc_info=False):
        """记录错误日志"""
        if exc_info:
            self.logger.exception(message)
        else:
            self.logger.error(message)

    def start_timer(self, key):
        """开始计时"""
        self.performance_data[key] = {
            "start_time": time.time(),
            "end_time": None,
            "duration": None,
        }

    def stop_timer(self, key):
        """停止计时并返回耗时"""
        if key in self.performance_data:
            self.performance_data[key]["end_time"] = time.time()
            self.performance_data[key]["duration"] = (
                self.performance_data[key]["end_time"]
                - self.performance_data[key]["start_time"]
            )
            return self.performance_data[key]["duration"]
        return 0

    def log_performance(self, key, action, additional_info=None):
        """记录性能数据"""
        if key in self.performance_data:
            duration = self.performance_data[key]["duration"]
            if duration is not None:
                message = f"{action} 耗时: {duration:.2f}秒"
                if additional_info:
                    message += f" | {additional_info}"
                self.info(message)
            return duration
        return 0

    def get_performance_stats(self):
        """获取性能统计信息"""
        stats = {}
        for key, data in self.performance_data.items():
            if data["duration"] is not None:
                stats[key] = data["duration"]
        return stats

    def log_system_status(self):
        """记录系统状态"""
        import platform

        try:
            import psutil

            memory = psutil.virtual_memory()
            memory_info = {
                "total": memory.total / 1024 / 1024 / 1024,
                "available": memory.available / 1024 / 1024 / 1024,
                "used": memory.used / 1024 / 1024 / 1024,
                "percent": memory.percent,
            }

            cpu_info = {"count": psutil.cpu_count(), "percent": psutil.cpu_percent(interval=1)}

            self.info(f"系统: {platform.system()} {platform.release()}")
            self.info(f"内存: {memory_info['used']:.1f}GB / {memory_info['total']:.1f}GB ({memory_info['percent']}%)")
            self.info(f"CPU: {cpu_info['count']}核, {cpu_info['percent']}%")
        except ImportError:
            self.info(f"系统: {platform.system()} {platform.release()}")
        except Exception as e:
            self.error(f"获取系统状态失败: {e}")


# 全局日志实例
logger = Logger()
