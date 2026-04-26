# 知识图谱服务
import networkx as nx
import json
from pathlib import Path
from config.config import KNOWLEDGE_MAP_DIR

class KnowledgeGraph:
    """知识图谱管理"""

    def __init__(self):
        self.graph = nx.DiGraph()
        self.knowledge_map_dir = KNOWLEDGE_MAP_DIR
        self.knowledge_map_dir.mkdir(parents=True, exist_ok=True)
    
    def add_knowledge_point(self, node_id, name, subject, grade, content=""):
        """添加知识点"""
        self.graph.add_node(node_id, name=name, subject=subject, grade=grade, content=content)
    
    def add_relation(self, source_id, target_id, relation_type="关联"):
        """添加知识点之间的关系"""
        self.graph.add_edge(source_id, target_id, relation=relation_type)
    
    def save_graph(self, filename):
        """保存知识图谱"""
        data = {
            "nodes": [
                {
                    "id": node,
                    "data": self.graph.nodes[node]
                }
                for node in self.graph.nodes
            ],
            "edges": [
                {
                    "source": edge[0],
                    "target": edge[1],
                    "data": self.graph.edges[edge]
                }
                for edge in self.graph.edges
            ]
        }
        
        filepath = self.knowledge_map_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_graph(self, filename):
        """加载知识图谱"""
        filepath = self.knowledge_map_dir / filename
        if not filepath.exists():
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for node in data.get("nodes", []):
            self.graph.add_node(node["id"], **node["data"])
        
        for edge in data.get("edges", []):
            self.graph.add_edge(edge["source"], edge["target"], **edge["data"])
    
    def get_related_knowledge(self, node_id):
        """获取相关知识点"""
        if node_id not in self.graph.nodes:
            return []
        
        related = []
        # 获取直接关联的节点
        for neighbor in self.graph.neighbors(node_id):
            related.append({
                "id": neighbor,
                "name": self.graph.nodes[neighbor].get("name"),
                "relation": self.graph.edges[(node_id, neighbor)].get("relation")
            })
        return related
