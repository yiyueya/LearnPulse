# 缓存管理工具
import os
import json
import hashlib
import time
import threading
from config.config import JSON_DIR, CACHE_EXPIRY_DAYS, MAX_CACHE_SIZE_MB

# 缓存条目上限（超过则按时间淘汰最旧的）
MAX_CACHE_ENTRIES = 5000

class CacheManager:
    """缓存管理工具，用于缓存图片理解结果和处理状态

    改进点：
    - 懒写入： dirty flag 控制，仅在必要时写盘
    - 数量限制： 超过 MAX_CACHE_ENTRIES 条时淘汰最旧的
    - 线程安全： 写操作加锁
    - 大小控制： 超过 MAX_CACHE_SIZE_MB 时淘汰最旧的
    """

    def __init__(self):
        self.cache_dir = os.path.join(JSON_DIR, "cache")
        self.image_cache_file = os.path.join(self.cache_dir, "image_cache.json")
        self.process_cache_file = os.path.join(self.cache_dir, "process_cache.json")
        self.process_status_file = os.path.join(self.cache_dir, "process_status.json")
        self._lock = threading.Lock()
        self._image_dirty = False
        self._process_dirty = False
        self._status_dirty = False
        os.makedirs(self.cache_dir, exist_ok=True)

        self.image_cache = self._load_cache(self.image_cache_file)
        self.process_cache = self._load_cache(self.process_cache_file)
        self.process_status = self._load_cache(self.process_status_file)

        self._clean_expired_cache()
        self._enforce_limits()

    def _load_cache(self, cache_file):
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_soon(self, which):
        """标记为脏，下次轮询时写入（延迟写）"""
        if which == 'image':
            self._image_dirty = True
        elif which == 'process':
            self._process_dirty = True
        elif which == 'status':
            self._status_dirty = True

    def _flush(self):
        """强制写出所有脏缓存"""
        with self._lock:
            if self._image_dirty:
                self._write_cache(self.image_cache, self.image_cache_file)
                self._image_dirty = False
            if self._process_dirty:
                self._write_cache(self.process_cache, self.process_cache_file)
                self._process_dirty = False
            if self._status_dirty:
                self._write_cache(self.process_status, self.process_status_file)
                self._status_dirty = False

    def _write_cache(self, cache_data, cache_file):
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=1)

    def _get_timestamp(self, value):
        return value.get('timestamp', 0) if isinstance(value, dict) else 0

    def _evict_lru(self, cache_dict, max_size_bytes=None):
        """按最旧时间淘汰缓存，直到满足大小和数量限制"""
        changed = False
        while True:
            items = [(k, v, self._get_timestamp(v)) for k, v in cache_dict.items()]
            if not items:
                break
            total_size = len(json.dumps(cache_dict))
            size_ok = max_size_bytes is None or total_size <= max_size_bytes
            count_ok = len(cache_dict) <= MAX_CACHE_ENTRIES
            if size_ok and count_ok:
                break
            oldest = min(items, key=lambda x: x[2])
            del cache_dict[oldest[0]]
            changed = True
        return changed

    def _enforce_limits(self):
        max_size_bytes = MAX_CACHE_SIZE_MB * 1024 * 1024
        for cache_dict, file_path, key in [
            (self.image_cache, self.image_cache_file, 'image'),
            (self.process_cache, self.process_cache_file, 'process'),
        ]:
            changed = self._evict_lru(cache_dict, max_size_bytes)
            if changed:
                setattr(self, f'_{key}_dirty', True)
                self._write_cache(cache_dict, file_path)

    def _clean_expired_cache(self):
        expiry_seconds = CACHE_EXPIRY_DAYS * 24 * 3600
        current_time = time.time()
        for cache_dict, file_path, key in [
            (self.image_cache, self.image_cache_file, 'image'),
            (self.process_cache, self.process_cache_file, 'process'),
        ]:
            before = len(cache_dict)
            expired = [
                k for k, v in cache_dict.items()
                if current_time - self._get_timestamp(v) > expiry_seconds
            ]
            for k in expired:
                del cache_dict[k]
            if expired:
                setattr(self, f'_{key}_dirty', True)
                self._write_cache(cache_dict, file_path)
            if len(cache_dict) < before:
                print(f"清理了 {before - len(cache_dict)} 个过期缓存")

    def get_image_hash(self, image_path):
        hasher = hashlib.md5()
        try:
            with open(image_path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    def get_image_cache(self, image_path):
        image_hash = self.get_image_hash(image_path)
        if not image_hash:
            return None
        with self._lock:
            entry = self.image_cache.get(image_hash, {})
            if entry and isinstance(entry, dict) and 'content' in entry:
                return entry['content']
            elif entry and isinstance(entry, str):
                return entry
        return None

    def set_image_cache(self, image_path, description):
        image_hash = self.get_image_hash(image_path)
        if not image_hash:
            return
        with self._lock:
            self.image_cache[image_hash] = {
                'content': description,
                'timestamp': time.time()
            }
            self._image_dirty = True
            self._evict_lru(self.image_cache, MAX_CACHE_SIZE_MB * 1024 * 1024)

    def get_process_cache(self, file_path):
        with self._lock:
            entry = self.process_cache.get(file_path, {})
            if entry and isinstance(entry, dict) and 'data' in entry:
                return entry['data']
            elif entry:
                return entry
        return {}

    def set_process_cache(self, file_path, cache_data):
        with self._lock:
            self.process_cache[file_path] = {
                'data': cache_data,
                'timestamp': time.time()
            }
            self._process_dirty = True
            self._evict_lru(self.process_cache, MAX_CACHE_SIZE_MB * 1024 * 1024)

    def clear_process_cache(self, file_path):
        with self._lock:
            if file_path in self.process_cache:
                del self.process_cache[file_path]
                self._process_dirty = True

    def clear_all_cache(self):
        with self._lock:
            self.image_cache = {}
            self.process_cache = {}
            self._image_dirty = True
            self._process_dirty = True
        self._flush()
        print("所有缓存已清空")

    def clear_image_cache_only(self):
        with self._lock:
            self.image_cache = {}
            self._image_dirty = True
        self._flush()
        print("图片缓存已清空")

    def clear_process_cache_only(self):
        with self._lock:
            self.process_cache = {}
            self._process_dirty = True
        self._flush()
        print("处理缓存已清空")

    def flush(self):
        self._flush()

    def get_cache_stats(self):
        with self._lock:
            return {
                "image_cache_count": len(self.image_cache),
                "process_cache_count": len(self.process_cache),
                "process_status_count": len(self.process_status),
                "cache_dir": self.cache_dir
            }

    def set_process_status(self, file_path, status, current_step=None, total_steps=None, error_message=None):
        with self._lock:
            self.process_status[file_path] = {
                'status': status,
                'current_step': current_step,
                'total_steps': total_steps,
                'error_message': error_message,
                'timestamp': time.time()
            }
            self._status_dirty = True

    def get_process_status(self, file_path):
        with self._lock:
            return self.process_status.get(file_path)

    def set_process_result(self, file_path, result_data):
        with self._lock:
            self.process_cache[file_path] = {
                'data': result_data,
                'timestamp': time.time()
            }
            self._process_dirty = True
            self._evict_lru(self.process_cache, MAX_CACHE_SIZE_MB * 1024 * 1024)

    def get_process_result(self, file_path):
        with self._lock:
            entry = self.process_cache.get(file_path, {})
            if entry and isinstance(entry, dict) and 'data' in entry:
                return entry['data']
            elif entry:
                return entry
        return None

    def is_file_completed(self, file_path):
        status = self.get_process_status(file_path)
        return bool(status and status.get('status') == 'completed')

    def clear_process_status(self, file_path):
        with self._lock:
            if file_path in self.process_status:
                del self.process_status[file_path]
                self._status_dirty = True

    def clear_all_status(self):
        with self._lock:
            self.process_status = {}
            self._status_dirty = True
        self._flush()