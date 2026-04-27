class CancellationRequested(Exception):
    """用户取消异常"""
    pass


# Agent调度中心
import concurrent.futures
import threading
from src.agents.content_extractor_agent import ContentExtractorAgent
from src.agents.knowledge_graph_agent import KnowledgeGraphAgent
from src.agents.question_generator_agent import QuestionGeneratorAgent
from src.agents.answer_evaluator_agent import AnswerEvaluatorAgent
from src.agents.analysis_agent import AnalysisAgent
from src.services.learning_history import LearningHistoryManager

class AgentCoordinator:
    """Agent调度中心，协调各个Agent的工作"""

    def __init__(self):
        self.content_extractor = ContentExtractorAgent()
        self.knowledge_graph = KnowledgeGraphAgent()
        self.question_generator = QuestionGeneratorAgent()
        self.answer_evaluator = AnswerEvaluatorAgent()
        self.analysis = AnalysisAgent()
        self.history_manager = LearningHistoryManager()
        self.progress_callback = None
        self._cancel_event = threading.Event()
        self.current_subject = None
        self.current_grade = None
        self.current_question_type = None

    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
        self.content_extractor.set_progress_callback(callback)

    def set_cancel_callback(self, cancel_check_fn):
        """设置取消检查函数"""
        self._cancel_check_fn = cancel_check_fn

    def check_cancel(self):
        """检查是否请求了取消，抛出异常"""
        if self._cancel_event.is_set():
            raise CancellationRequested("用户取消了处理")
        if hasattr(self, '_cancel_check_fn') and self._cancel_check_fn and self._cancel_check_fn():
            raise CancellationRequested("用户取消了处理")

    def request_cancel(self):
        """请求取消处理"""
        self._cancel_event.set()

    def reset_cancel(self):
        """重置取消状态"""
        self._cancel_event.clear()

    def _update_progress(self, message, progress=None):
        """更新进度"""
        self.check_cancel()
        if self.progress_callback:
            self.progress_callback({"message": message, "progress": progress})
    
    def process_pdf_documents(self):
        """处理PDF文档并构建知识地图"""
        self.reset_cancel()
        self.content_extractor.set_cancel_check(self.check_cancel)
        results = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            extraction_future = executor.submit(self.content_extractor.process_all_pdfs)

            try:
                extraction_results = extraction_future.result()
            except CancellationRequested:
                self.content_extractor.cancel()
                self._update_progress("处理已取消")
                return {"status": "cancelled", "message": "用户取消了处理"}

            results["extraction_results"] = extraction_results
            self.check_cancel()

            self._update_progress("开始构建知识地图")
            knowledge_map_future = executor.submit(self.knowledge_graph.build_all_knowledge_maps)

            try:
                knowledge_map_results = knowledge_map_future.result()
            except CancellationRequested:
                self._update_progress("处理已取消")
                return {"status": "cancelled", "message": "用户取消了处理"}

            self._update_progress("知识地图构建完成")
            results["knowledge_map_results"] = knowledge_map_results

        return results

    def process_selected_documents(self, selected_files):
        """处理选定的PDF文档并构建知识地图"""
        self.reset_cancel()
        self.content_extractor.set_cancel_check(self.check_cancel)
        results = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            extraction_future = executor.submit(self.content_extractor.process_selected_files, selected_files)

            try:
                extraction_results = extraction_future.result()
            except CancellationRequested:
                self.content_extractor.cancel()
                self._update_progress("处理已取消")
                return {"status": "cancelled", "message": "用户取消了处理"}

            results["extraction_results"] = extraction_results
            self.check_cancel()

            self._update_progress("开始构建知识地图")
            # Extract unique subjects from selected_files to build only needed subjects
            selected_subjects = list(set(f.get("subject") for f in selected_files if f.get("subject")))
            if selected_subjects:
                knowledge_map_future = executor.submit(self.knowledge_graph.build_knowledge_maps, selected_subjects)
            else:
                knowledge_map_future = executor.submit(self.knowledge_graph.build_all_knowledge_maps)

            try:
                knowledge_map_results = knowledge_map_future.result()
            except CancellationRequested:
                self._update_progress("处理已取消")
                return {"status": "cancelled", "message": "用户取消了处理"}

            self._update_progress("知识地图构建完成")
            results["knowledge_map_results"] = knowledge_map_results

        return results

    def get_pending_files(self):
        """获取待处理的文件列表"""
        return self.content_extractor.get_pending_files()
    
    def generate_diagnostic_test(self, subject, grade, question_type="mixed", question_count=10):
        """生成诊断测试"""
        self.current_subject = subject
        self.current_grade = grade
        self.current_question_type = question_type
        self._update_progress(f"开始生成{subject}{grade}{question_type}诊断测试")
        result = self.question_generator.generate_diagnostic_test(subject, grade, question_type, question_count)
        self._update_progress(f"{subject}{grade}诊断测试生成完成")
        return result
    
    def evaluate_test(self, test_questions, student_answers, subject=None, grade=None, question_type=None):
        """评估测试"""
        self._update_progress("开始评估测试")
        evaluation_result = self.answer_evaluator.evaluate_test(test_questions, student_answers)

        # 生成薄弱点报告
        if evaluation_result["status"] == "success":
            self._update_progress("开始生成薄弱点报告")
            analysis_result = self.analysis.analyze_performance(evaluation_result)
            evaluation_result["analysis"] = analysis_result.get("report", {})
            # 自动保存到历史记录
            subject = subject or self.current_subject
            grade = grade or self.current_grade
            question_type = question_type or self.current_question_type
            if subject and grade:
                weak_points = analysis_result.get("weak_knowledge_points", [])
                self.history_manager.add_record(
                    subject=subject,
                    grade=grade,
                    question_type=question_type or "mixed",
                    score=evaluation_result["score"],
                    total=evaluation_result["total"],
                    accuracy=evaluation_result["accuracy"],
                    weak_knowledge=evaluation_result["analysis"].get("weak_knowledge", [])
                )
            self._update_progress("薄弱点报告生成完成")

        return evaluation_result
    
    def get_weak_points(self, test_results):
        """获取薄弱点"""
        self._update_progress("开始分析薄弱点")
        result = self.analysis.analyze_performance(test_results)
        self._update_progress("薄弱点分析完成")
        return result

    def generate_weak_point_practice(self, subject, grade, weak_knowledge_points, question_type="mixed", question_count=5):
        """基于薄弱知识点生成针对性练习题"""
        self._update_progress(f"开始生成{subject}{grade}薄弱点练习")
        result = self.question_generator.generate_questions(
            subject=subject,
            grade=grade,
            question_type=question_type,
            question_count=question_count,
            knowledge_points=weak_knowledge_points
        )
        self._update_progress(f"薄弱点练习生成完成")
        return result