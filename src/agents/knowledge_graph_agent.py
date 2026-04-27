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

    def _extract_knowledge_items(self, data, subject):
        """递归从JSON数据中提取所有知识点项"""
        items = []
        if isinstance(data, list):
            for item in data:
                items.extend(self._extract_knowledge_items(item, subject))
        elif isinstance(data, dict):
            # 检查是否是知识点节点（有实质内容）
            # 匹配条件：name字段 + content/知识点字段（直接字段，非字符串搜索）
            has_name = bool(data.get("name") or data.get("标题") or data.get("知识点名称"))
            has_content = bool(data.get("content") or data.get("知识点") or data.get("内容"))
            if has_name and has_content:
                # 提取名称
                name = (data.get("标题") or data.get("name") or
                        data.get("知识点名称") or
                        str(data.get("单元", "")) + "_" + str(data.get("序号", "")))
                # 提取内容摘要
                knowledge_list = data.get("知识点", [])
                if isinstance(knowledge_list, list) and knowledge_list:
                    content = "; ".join(str(k) for k in knowledge_list[:3])
                else:
                    content = data.get("content") or data.get("内容") or ""
                # 提取年级
                grade = data.get("grade") or data.get("年级") or "一年级"
                items.append({"name": name, "content": content, "grade": grade})
            # 递归处理子节点
            for value in data.values():
                if isinstance(value, (dict, list)):
                    items.extend(self._extract_knowledge_items(value, subject))
        return items

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
        all_items = []
        for file in subject_files:
            with open(file, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    items = self._extract_knowledge_items(data, subject)
                    all_items.extend(items)
                except json.JSONDecodeError:
                    continue

        # 去重并添加节点
        seen_names = set()
        for item in all_items:
            name = item.get("name", "")
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            node_id = f"{subject}_{node_id_counter}"
            node_id_counter += 1
            self.knowledge_graph.add_knowledge_point(
                node_id,
                name,
                subject,
                item.get("grade", ""),
                item.get("content", "")
            )

        # 添加知识点之间的关联边（相邻节点之间）
        nodes_list = list(self.knowledge_graph.graph.nodes)
        for i in range(len(nodes_list) - 1):
            self.knowledge_graph.add_relation(nodes_list[i], nodes_list[i + 1], "后续关联")

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
