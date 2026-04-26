# 出题Agent
from src.services.ai_service import AIService
from src.services.knowledge_graph import KnowledgeGraph
import json
import os
from config.config import JSON_DIR

class QuestionGeneratorAgent:
    """出题Agent,负责基于知识点生成题目"""

    def __init__(self):
        self.ai_service = AIService()
        self.knowledge_graph = KnowledgeGraph()

    def generate_questions(self, subject, grade, question_type="mixed", question_count=10, knowledge_points=None):
        """生成题目"""
        if not knowledge_points:
            # 从知识图谱中获取知识点
            self.knowledge_graph.load_graph(f"{subject}_knowledge_map.json")
            knowledge_points = []
            for node in self.knowledge_graph.graph.nodes:
                node_data = self.knowledge_graph.graph.nodes[node]
                if node_data.get("grade") == grade:
                    knowledge_points.append(node_data.get("name"))

        if not knowledge_points:
            return {"status": "error", "message": "未找到知识点"}

        # 使用AI生成题目
        knowledge_str = "\n".join(knowledge_points)
        questions_json = self.ai_service.generate_questions(knowledge_str, subject, grade, question_type, question_count)

        if not questions_json:
            return {"status": "error", "message": "题目生成失败"}

        try:
            # 尝试解析AI返回的JSON
            questions = json.loads(questions_json)
            return {"status": "success", "questions": questions}
        except json.JSONDecodeError:
            return {"status": "warning", "message": "AI返回的不是有效JSON", "content": questions_json}

    def generate_diagnostic_test(self, subject, grade, question_type="mixed", question_count=15):
        """生成诊断测试题目"""
        return self.generate_questions(subject, grade, question_type, question_count)
