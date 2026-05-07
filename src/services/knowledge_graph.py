# 知识图谱服务 - 保留接口，内部使用SQLite实现
from src.services.knowledge_graph_sqlite import SQLiteKnowledgeGraph

class KnowledgeGraph:
    """知识图谱管理 - 兼容旧接口，内部使用SQLite"""

    def __init__(self):
        self.kg = SQLiteKnowledgeGraph()
        self.graph = None  # 保留兼容性

    def add_knowledge_point(self, node_id, name, subject, grade, content=""):
        """添加知识点"""
        self.kg.add_knowledge_point(
            node_id=node_id,
            name=name,
            subject=subject,
            grade=grade,
            unit=None,
            content=content
        )

    def add_relation(self, source_id, target_id, relation_type="关联"):
        """添加知识点之间的关系"""
        self.kg.add_relation(source_id, target_id, relation_type)

    def save_graph(self, filename):
        """保存知识图谱"""
        data = self.kg.export_to_json()
        import json
        from pathlib import Path
        from config.config import KNOWLEDGE_MAP_DIR

        filepath = KNOWLEDGE_MAP_DIR / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_graph(self, filename):
        """加载知识图谱"""
        # SQLite版本已加载，不需要额外操作
        pass

    def get_related_knowledge(self, node_id):
        """获取相关知识点"""
        related = self.kg.get_related_nodes(node_id)
        return [
            {
                "id": node['id'],
                "name": node['name'],
                "relation": node.get('relation_type', '关联')
            }
            for node in related
        ]