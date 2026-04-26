# 学习历史记录服务
import json
import os
from datetime import datetime
from config.config import DATA_DIR

class LearningHistoryManager:
    """学习历史管理"""

    def __init__(self):
        self.history_file = os.path.join(DATA_DIR, "learning_history.json")
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(self.history_file):
            self._save([])

    def _load(self):
        """加载历史记录"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save(self, records):
        """保存历史记录"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def add_record(self, subject, grade, question_type, score, total, accuracy, weak_knowledge, practice_answers=None):
        """添加学习记录"""
        records = self._load()
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "subject": subject,
            "grade": grade,
            "question_type": question_type,
            "score": score,
            "total": total,
            "accuracy": round(accuracy, 1),
            "weak_knowledge": weak_knowledge,
        }
        records.append(record)
        self._save(records)
        return record

    def get_history(self, subject=None, grade=None, limit=10):
        """获取历史记录"""
        records = self._load()
        if subject:
            records = [r for r in records if r["subject"] == subject]
        if grade:
            records = [r for r in records if r["grade"] == grade]
        return records[-limit:]

    def get_weak_point_trends(self, subject=None, grade=None, limit=10):
        """获取薄弱点趋势分析"""
        records = self.get_history(subject, grade, limit)
        weak_count = {}
        for record in records:
            for wp in record.get("weak_knowledge", []):
                knowledge = wp["knowledge"] if isinstance(wp, dict) else wp
                weak_count[knowledge] = weak_count.get(knowledge, 0) + 1
        sorted_weak = sorted(weak_count.items(), key=lambda x: x[1], reverse=True)
        return [
            {"knowledge": k, "appear_count": v, "trend": "持续薄弱" if v >= len(records) * 0.5 else "偶尔出错"}
            for k, v in sorted_weak
        ]

    def get_improvement(self, subject, grade, knowledge_point):
        """查看某个知识点的进步情况"""
        records = self._load()
        records = [r for r in records if r["subject"] == subject and r["grade"] == grade]
        history = []
        for record in records:
            weak = record.get("weak_knowledge", [])
            weak_names = [w["knowledge"] if isinstance(w, dict) else w for w in weak]
            history.append({
                "timestamp": record["timestamp"],
                "appeared": knowledge_point in weak_names,
                "accuracy": record["accuracy"]
            })
        return history
