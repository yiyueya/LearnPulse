# 分析Agent
import json
import os
from config.config import JSON_DIR

class AnalysisAgent:
    """分析Agent,负责分析学习数据并生成薄弱点报告"""

    def __init__(self):
        pass

    def analyze_performance(self, test_results):
        """分析测试表现"""
        if "results" not in test_results:
            return {"status": "error", "message": "测试结果格式错误"}

        # 分析错误题目
        wrong_questions = []
        for result in test_results["results"]:
            if not result["evaluation"]["is_correct"]:
                wrong_questions.append(result)

        # 统计薄弱知识点
        weak_knowledge = {}
        for question in wrong_questions:
            # 这里简化处理,实际应从题目中提取知识点
            # 假设题目中包含知识点信息
            if "知识点" in question["question"]:
                knowledge = question["question"].split("知识点:")[1].split("\n")[0].strip()
                weak_knowledge[knowledge] = weak_knowledge.get(knowledge, 0) + 1

        # 生成薄弱点报告
        weak_list = [
            {"knowledge": k, "count": v}
            for k, v in sorted(weak_knowledge.items(), key=lambda x: x[1], reverse=True)
        ]

        report = {
            "total_questions": test_results["total"],
            "correct_count": test_results["score"],
            "wrong_count": len(wrong_questions),
            "accuracy": test_results["accuracy"],
            "weak_knowledge": weak_list,
            "suggestions": self.generate_suggestions(weak_knowledge)
        }

        return {
            "status": "success",
            "report": report,
            "weak_knowledge_points": [item["knowledge"] for item in weak_list]
        }

    def generate_suggestions(self, weak_knowledge):
        """生成学习建议"""
        suggestions = []
        for knowledge, count in weak_knowledge.items():
            suggestions.append(f"加强{knowledge}的练习,建议每天练习相关题目")
        return suggestions

    def generate_progress_report(self, historical_data):
        """生成学习进度报告"""
        # 简化实现,实际应根据历史数据进行分析
        report = {
            "overall_progress": "稳步提升",
            "recent_performance": "有所进步",
            "areas_for_improvement": ["应用题", "阅读理解"],
            "recommended_practice": "每天练习10道题目"
        }
        return {"status": "success", "report": report}
