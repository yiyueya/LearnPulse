# 知识图谱Agent
from src.services.knowledge_graph import KnowledgeGraph
import json
from pathlib import Path
from config.config import JSON_DIR

class KnowledgeGraphAgent:
    """知识图谱Agent，负责构建和维护知识地图"""

    def __init__(self):
        self.knowledge_graph = KnowledgeGraph()
        self.json_dir = JSON_DIR

    def build_knowledge_map(self, subject):
        """构建指定学科的知识地图"""
        # 加载该学科的所有知识点JSON文件
        subject_files = []
        for file in self.json_dir.iterdir():
            if subject in file.name and file.suffix == ".json":
                subject_files.append(file)
        
        if not subject_files:
            return {"status": "error", "message": f"未找到{subject}学科的知识点文件"}
        
        # 构建知识图谱
        node_id_counter = 1
        for file in subject_files:
            with open(file, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    # 假设data是知识点列表
                    if isinstance(data, list):
                        for item in data:
                            node_id = f"{subject}_{node_id_counter}"
                            node_id_counter += 1
                            self.knowledge_graph.add_knowledge_point(
                                node_id,
                                item.get("name", ""),
                                subject,
                                item.get("grade", ""),
                                item.get("content", "")
                            )
                    # 处理其他可能的JSON结构
                    elif isinstance(data, dict):
                        # 具体处理逻辑根据实际JSON结构调整
                        pass
                except json.JSONDecodeError:
                    continue
        
        # 保存知识图谱
        self.knowledge_graph.save_graph(f"{subject}_knowledge_map.json")
        return {"status": "success", "message": f"{subject}学科知识地图构建完成"}
    
    def build_all_knowledge_maps(self):
        """构建所有学科的知识地图"""
        subjects = ["数学", "语文"]
        return self.build_knowledge_maps(subjects)

    def build_knowledge_maps(self, subjects):
        """构建指定学科的知识地图"""
        results = {}

        for subject in subjects:
            result = self.build_knowledge_map(subject)
            results[subject] = result

        return results
