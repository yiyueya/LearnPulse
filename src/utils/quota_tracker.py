# MiniMax VLM 额度追踪器
# 跟踪 coding_plan/vlm API 调用额度，防止超额使用
from pathlib import Path
from datetime import datetime, timedelta
import json

class MiniMaxVLMError(Exception):
    """MiniMax VLM 相关错误"""
    pass

class QuotaExhaustedError(MiniMaxVLMError):
    """额度用尽错误"""
    pass

class MiniMaxQuotaTracker:
    """MiniMax 图片理解 API 额度追踪器"""
    
    # MiniMax coding-plan-vlm 每5小时150张图片
    HOURLY_LIMIT = 150
    WINDOW_HOURS = 5
    WARN_THRESHOLD = 0.8  # 80% 发出警告
    
    def __init__(self, state_file=None):
        if state_file is None:
            state_file = Path(__file__).parent.parent.parent / "data" / "json" / "quota_state.json"
        else:
            state_file = Path(state_file)
        
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.state = self._load_state()
    
    def _load_state(self) -> dict:
        """从文件加载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        "used": data.get("used", 0),
                        "window_start": data.get("window_start", None),
                        "last_exhausted_at": data.get("last_exhausted_at", None),
                        "warned_at": data.get("warned_at", None)
                    }
            except Exception:
                pass
        
        return {
            "used": 0,
            "window_start": None,
            "last_exhausted_at": None,
            "warned_at": None
        }
    
    def _save_state(self):
        """保存状态到文件"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _now(self) -> datetime:
        return datetime.now()
    
    def _get_window_start(self) -> datetime:
        """获取当前窗口起始时间"""
        if self.state["window_start"]:
            return datetime.fromisoformat(self.state["window_start"])
        return self._now()
    
    def reset_if_needed(self):
        """检查是否需要重置计数器（5小时窗口已过）"""
        window_start = self._get_window_start()
        elapsed = self._now() - window_start
        
        if elapsed >= timedelta(hours=self.WINDOW_HOURS):
            self.state["used"] = 0
            self.state["window_start"] = self._now().isoformat()
            self.state["warned_at"] = None
            self._save_state()
            return True
        return False
    
    def record_usage(self, image_count=1):
        """记录已使用的额度"""
        # 确保窗口是新鲜的
        self.reset_if_needed()
        
        # 初始化窗口起始时间（第一个请求时）
        if self.state["window_start"] is None:
            self.state["window_start"] = self._now().isoformat()
        
        self.state["used"] += image_count
        self._save_state()
        
        # 检查是否超过额度
        if self.state["used"] > self.HOURLY_LIMIT:
            self.state["last_exhausted_at"] = self._now().isoformat()
    
    def can_process(self, image_count=1) -> bool:
        """检查是否可以处理指定数量的图片"""
        self.reset_if_needed()
        
        return (self.state["used"] + image_count) <= self.HOURLY_LIMIT
    
    def get_status(self) -> dict:
        """获取当前额度状态"""
        self.reset_if_needed()
        
        remaining = max(0, self.HOURLY_LIMIT - self.state["used"])
        percent = (self.state["used"] / self.HOURLY_LIMIT) * 100 if self.HOURLY_LIMIT > 0 else 0
        exhausted = self.state["used"] >= self.HOURLY_LIMIT
        
        window_start = self._get_window_start()
        next_reset = window_start + timedelta(hours=self.WINDOW_HOURS)
        next_reset_str = next_reset.strftime("%H:%M") if next_reset else "N/A"
        
        return {
            "used": self.state["used"],
            "limit": self.HOURLY_LIMIT,
            "remaining": remaining,
            "percent": round(percent, 1),
            "exhausted": exhausted,
            "window_start": self.state["window_start"],
            "next_reset_at": next_reset_str,
            "warn_triggered": self.state["used"] >= (self.HOURLY_LIMIT * self.WARN_THRESHOLD)
        }
    
    def mark_exhausted(self):
        """标记额度已用尽（API返回529时调用）"""
        self.state["last_exhausted_at"] = self._now().isoformat()
        self.state["used"] = self.HOURLY_LIMIT  # 强制标记为已用尽
        self._save_state()
    
    def check_and_raise(self, image_count=1):
        """检查额度，不够则抛出异常"""
        if not self.can_process(image_count):
            status = self.get_status()
            raise QuotaExhaustedError(
                f"图片额度已用完（已用 {status['used']}/{status['limit']}），"
                f"将在 {status['next_reset_at']} 额度重置后继续处理"
            )
    
    def should_warn(self) -> bool:
        """是否应该发出警告（达到80%阈值）"""
        self.reset_if_needed()
        return self.state["used"] >= (self.HOURLY_LIMIT * self.WARN_THRESHOLD) and self.state.get("warned_at") is None
    
    def mark_warned(self):
        """标记已发出警告"""
        self.state["warned_at"] = self._now().isoformat()
        self._save_state()


# 全局单例
_quota_tracker = None

def get_quota_tracker() -> MiniMaxQuotaTracker:
    """获取全局额度追踪器单例"""
    global _quota_tracker
    if _quota_tracker is None:
        _quota_tracker = MiniMaxQuotaTracker()
    return _quota_tracker