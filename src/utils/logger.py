# 日志和性能监控模块
import logging
import time
from pathlib import Path
from datetime import datetime

class Logger:
    """日志和性能监控类"""

    def __init__(self):
        # 创建日志目录
        log_dir = Path(__file__).parent.parent.parent / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)

        # 配置日志
        log_file = log_dir / f"app_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        # 设置日志格式 - 更清晰的时间显示
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)

        # 创建日志记录器
        self.logger = logging.getLogger('AILearning')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 性能监控数据
        self.performance_data = {}
    
    def info(self, message):
        """记录信息日志"""
        self.logger.info(message)
    
    def error(self, message):
        """记录错误日志"""
        self.logger.error(message)
    
    def warning(self, message):
        """记录警告日志"""
        self.logger.warning(message)
    
    def debug(self, message):
        """记录调试日志"""
        self.logger.debug(message)
    
    def start_timer(self, key):
        """开始计时"""
        self.performance_data[key] = {
            'start_time': time.time(),
            'end_time': None,
            'duration': None
        }
    
    def stop_timer(self, key):
        """停止计时并返回耗时"""
        if key in self.performance_data:
            self.performance_data[key]['end_time'] = time.time()
            self.performance_data[key]['duration'] = self.performance_data[key]['end_time'] - self.performance_data[key]['start_time']
            return self.performance_data[key]['duration']
        return 0
    
    def log_performance(self, key, action, additional_info=None):
        """记录性能数据"""
        if key in self.performance_data:
            duration = self.performance_data[key]['duration']
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
            if data['duration'] is not None:
                stats[key] = data['duration']
        return stats
    
    def log_system_status(self):
        """记录系统状态"""
        import platform
        
        try:
            import psutil
            
            # 获取系统信息
            system_info = {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor()
            }
            
            # 获取内存信息
            memory = psutil.virtual_memory()
            memory_info = {
                'total': memory.total / 1024 / 1024 / 1024,  # GB
                'available': memory.available / 1024 / 1024 / 1024,  # GB
                'used': memory.used / 1024 / 1024 / 1024,  # GB
                'percent': memory.percent
            }
            
            # 获取CPU信息
            cpu_info = {
                'count': psutil.cpu_count(),
                'percent': psutil.cpu_percent(interval=1)
            }
            
            # 记录系统状态
            self.info(f"系统信息: {system_info}")
            self.info(f"内存信息: {memory_info}")
            self.info(f"CPU信息: {cpu_info}")
        except ImportError:
            # psutil库不存在时的处理
            system_info = {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor()
            }
            self.info(f"系统信息: {system_info}")
            self.info("psutil库未安装，无法获取内存和CPU信息")
        except Exception as e:
            # 其他异常处理
            self.error(f"获取系统状态失败: {e}")

# 创建全局日志实例
logger = Logger()