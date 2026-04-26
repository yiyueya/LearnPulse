# 文件状态管理工具
import os
import json
import hashlib
from config.config import DATA_DIR, JSON_DIR
from src.utils.logger import logger

class FileStatusManager:
    """文件状态管理，用于记录PDF文档的读取状态"""
    
    def __init__(self):
        self.status_file = os.path.join(JSON_DIR, "file_status.json")
        os.makedirs(JSON_DIR, exist_ok=True)
        self.status_data = self._load_status()
    
    def _load_status(self):
        """加载文件状态"""
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def _save_status(self):
        """保存文件状态"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(self.status_data, f, ensure_ascii=False, indent=2)
    
    def get_file_hash(self, file_path):
        """计算文件哈希值"""
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(65536)
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        except Exception:
            return None
    
    def is_file_modified(self, file_path):
        """检查文件是否被修改"""
        file_hash = self.get_file_hash(file_path)
        if not file_hash:
            return True
        
        if file_path not in self.status_data:
            return True
        
        return self.status_data[file_path] != file_hash
    
    def update_file_status(self, file_path):
        """更新文件状态"""
        file_hash = self.get_file_hash(file_path)
        if file_hash:
            self.status_data[file_path] = file_hash
            self._save_status()
    
    def get_modified_files(self, subject):
        """获取指定学科的修改文件列表"""
        try:
            subject_dir = os.path.join(DATA_DIR, subject)
            if not os.path.exists(subject_dir):
                return []
            
            modified_files = []
            for file in os.listdir(subject_dir):
                if file.endswith(".pdf"):
                    file_path = os.path.join(subject_dir, file)
                    if self.is_file_modified(file_path):
                        modified_files.append(file_path)
            return modified_files
        except Exception as e:
            logger.error(f"获取修改文件列表错误: {e}")
            return []
    
    def get_all_modified_files(self):
        """获取所有学科的修改文件列表"""
        try:
            subjects = ["数学", "语文"]
            all_modified_files = []
            
            for subject in subjects:
                subject_files = self.get_modified_files(subject)
                for file_path in subject_files:
                    filename = os.path.basename(file_path)
                    all_modified_files.append({
                        "path": file_path,
                        "filename": filename,
                        "subject": subject,
                        "grade": "一年级" if "一年级" in filename else "二年级"
                    })
            
            return all_modified_files
        except Exception as e:
            logger.error(f"获取所有修改文件错误: {e}")
            return []