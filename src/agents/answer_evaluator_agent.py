# 判题Agent
from src.services.ai_service import AIService

class AnswerEvaluatorAgent:
    """判题Agent，负责评估学生的答案"""
    
    def __init__(self):
        self.ai_service = AIService()
    
    def evaluate_answer(self, question, student_answer, correct_answer=None):
        """评估答案"""
        # 使用AI评估答案
        evaluation = self.ai_service.evaluate_answer(question, student_answer)
        
        if not evaluation:
            return {"status": "error", "message": "答案评估失败"}
        
        # 解析评估结果
        # 这里简化处理，实际应根据AI返回的格式进行解析
        result = {
            "evaluation": evaluation,
            "is_correct": "正确" in evaluation,
            "feedback": evaluation
        }
        
        return {"status": "success", "result": result}
    
    def evaluate_test(self, test_questions, student_answers):
        """评估整个测试"""
        results = []
        score = 0
        
        for i, (question, answer) in enumerate(zip(test_questions, student_answers)):
            evaluation = self.evaluate_answer(question, answer)
            if evaluation["status"] == "success":
                results.append({
                    "question": question,
                    "student_answer": answer,
                    "evaluation": evaluation["result"]
                })
                if evaluation["result"]["is_correct"]:
                    score += 1
        
        total_questions = len(test_questions)
        accuracy = (score / total_questions) * 100 if total_questions > 0 else 0
        
        return {
            "status": "success",
            "results": results,
            "score": score,
            "total": total_questions,
            "accuracy": accuracy
        }
