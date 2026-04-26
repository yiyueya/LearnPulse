# 主应用文件
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, field_validator
from config.config import HOST, PORT, MINIMAX_API_KEY
from src.agents.agent_coordinator import AgentCoordinator
from src.utils.logger import logger
import asyncio
import json
from typing import AsyncGenerator, List, Dict, Optional

logger.info("应用启动中...")

# 创建FastAPI应用
app = FastAPI(
    title="AI智能学习助手",
    description="基于AI的小学生语数学习助手",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 创建Agent协调器
coordinator = AgentCoordinator()

# 自定义异常类
class APIKeyMissingError(Exception):
    """API密钥未配置错误"""
    pass

class ProcessingError(Exception):
    """处理过程中的错误"""
    pass

# 全局异常处理器
@app.exception_handler(APIKeyMissingError)
async def api_key_missing_handler(request: Request, exc: APIKeyMissingError):
    logger.error(f"API密钥未配置: {request.url}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_type": "API_KEY_MISSING",
            "message": "API密钥未配置，请检查环境变量设置"
        }
    )

@app.exception_handler(ProcessingError)
async def processing_error_handler(request: Request, exc: ProcessingError):
    logger.error(f"处理错误: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_type": "PROCESSING_ERROR",
            "message": str(exc)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_type": "INTERNAL_ERROR",
            "message": f"服务器内部错误: {str(exc)}"
        }
    )

# 前端页面路由
@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# 健康检查端点
@app.get("/health")
def health_check():
    api_key_status = "configured" if MINIMAX_API_KEY else "missing"
    status = {
        "status": "healthy",
        "api_key_status": api_key_status,
        "version": "1.0.0"
    }
    logger.info("健康检查请求")
    return status

# 存储处理状态
processing_status = {
    "is_processing": False,
    "cancel_requested": False,
    "progress": 0,
    "message": "",
    "result": None
}

# 异步处理PDF
async def process_pdfs_async(selected_files=None):
    global processing_status

    processing_status["is_processing"] = True
    processing_status["cancel_requested"] = False
    processing_status["progress"] = 0
    processing_status["message"] = "准备开始处理..."
    processing_status["result"] = None

    progress_updates = []

    def progress_callback(progress_data):
        nonlocal progress_updates
        progress_updates.append(progress_data)
        processing_status["message"] = progress_data.get("message", "")
        if progress_data.get("progress") is not None:
            processing_status["progress"] = progress_data.get("progress")

    coordinator.set_progress_callback(progress_callback)
    coordinator.set_cancel_callback(lambda: processing_status.get("cancel_requested", False))

    try:
        loop = asyncio.get_event_loop()
        if selected_files:
            result = await loop.run_in_executor(None, coordinator.process_selected_documents, selected_files)
        else:
            result = await loop.run_in_executor(None, coordinator.process_pdf_documents)

        processing_status["result"] = result
        processing_status["progress"] = 100
        processing_status["message"] = "处理完成！"
    except Exception as e:
        from src.agents.agent_coordinator import CancellationRequested
        if isinstance(e, CancellationRequested):
            processing_status["result"] = {"status": "cancelled", "message": "用户取消了处理"}
            processing_status["progress"] = 100
            processing_status["message"] = "处理已取消"
        else:
            processing_status["result"] = {"status": "error", "message": str(e)}
            processing_status["progress"] = 100
            processing_status["message"] = f"处理失败: {str(e)}"
    finally:
        processing_status["is_processing"] = False

# SSE端点，返回实时进度
@app.get("/process_pdfs_stream")
async def process_pdfs_stream() -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        # 发送初始状态
        yield f"data: {json.dumps(processing_status)}\n\n"

        cancelled = False

        # 如果已经在处理，持续发送状态更新
        if processing_status["is_processing"]:
            last_message = ""
            while processing_status["is_processing"]:
                if processing_status["cancel_requested"]:
                    cancelled = True
                    break
                if processing_status["message"] != last_message:
                    yield f"data: {json.dumps(processing_status)}\n\n"
                    last_message = processing_status["message"]
                await asyncio.sleep(0.1)

            # 等 finally 执行完
            while processing_status["is_processing"]:
                await asyncio.sleep(0.05)
            if cancelled:
                processing_status["message"] = "处理已取消"
            yield f"data: {json.dumps(processing_status)}\n\n"
            return

        # 否则开始新的处理
        asyncio.create_task(process_pdfs_async())
        
        # 等待处理开始
        while not processing_status["is_processing"]:
            await asyncio.sleep(0.1)
        
        # 发送进度更新
        last_message = ""
        cancelled = False
        while processing_status["is_processing"]:
            if processing_status["cancel_requested"]:
                cancelled = True
                break
            if processing_status["message"] != last_message:
                yield f"data: {json.dumps(processing_status)}\n\n"
                last_message = processing_status["message"]
            await asyncio.sleep(0.1)

        # 等 finally 执行完再发最终结果，确保 is_processing=false
        while processing_status["is_processing"]:
            await asyncio.sleep(0.05)

        if cancelled:
            processing_status["message"] = "处理已取消"
        yield f"data: {json.dumps(processing_status)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.post("/cancel_process")
def cancel_process():
    """取消正在进行的PDF处理"""
    global processing_status
    if not processing_status.get("is_processing"):
        return {"status": "success", "message": "当前没有正在进行的处理"}
    processing_status["cancel_requested"] = True
    processing_status["message"] = "正在取消处理..."
    return {"status": "success", "message": "取消请求已发送"}

# 处理PDF文档并构建知识地图（保留原接口）
@app.post("/process_pdfs")
def process_pdfs():
    try:
        logger.info("开始处理PDF文档")
        result = coordinator.process_pdf_documents()
        logger.info(f"PDF处理完成: {result.get('status', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"PDF处理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# 获取待处理文件列表
@app.get("/get_pending_files")
def get_pending_files():
    try:
        pending_files = coordinator.get_pending_files()
        return {"status": "success", "files": pending_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 获取文件处理状态
@app.get("/get_file_status/{file_path:path}")
def get_file_status(file_path: str):
    try:
        from src.utils.cache_manager import CacheManager
        cache_manager = CacheManager()
        status = cache_manager.get_process_status(file_path)
        return {"status": "success", "file_status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 获取所有文件处理状态
@app.get("/get_all_file_status")
def get_all_file_status():
    try:
        from src.utils.cache_manager import CacheManager
        cache_manager = CacheManager()
        all_status = cache_manager.process_status
        return {"status": "success", "file_statuses": all_status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 清除文件处理状态
@app.delete("/clear_file_status/{file_path:path}")
def clear_file_status(file_path: str):
    try:
        from src.utils.cache_manager import CacheManager
        cache_manager = CacheManager()
        cache_manager.clear_process_status(file_path)
        return {"status": "success", "message": "文件处理状态已清除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 处理选定的PDF文档
class SelectedFilesRequest(BaseModel):
    files: List[Dict]

@app.post("/process_selected_files")
async def process_selected_files(request: SelectedFilesRequest):
    try:
        # 立即设置处理状态，防止 SSE 重复启动
        global processing_status
        processing_status["is_processing"] = True
        processing_status["cancel_requested"] = False
        processing_status["progress"] = 0
        processing_status["message"] = "准备开始处理..."
        processing_status["result"] = None
        asyncio.create_task(process_pdfs_async(request.files))
        return {"status": "success", "message": "开始处理选定文件"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 生成诊断测试
class TestRequest(BaseModel):
    subject: str
    grade: str
    question_type: str = "mixed"  # 支持: mixed/choice/fill/judge
    question_count: int = 10

    @field_validator('subject')
    @classmethod
    def validate_subject(cls, v):
        if v not in ['语文', '数学']:
            raise ValueError('学科必须是"语文"或"数学"')
        return v

    @field_validator('grade')
    @classmethod
    def validate_grade(cls, v):
        if v not in ['一年级', '二年级']:
            raise ValueError('年级必须是"一年级"或"二年级"')
        return v

    @field_validator('question_type')
    @classmethod
    def validate_question_type(cls, v):
        if v not in ['mixed', 'choice', 'fill', 'judge']:
            raise ValueError('题型必须是 mixed/choice/fill/judge')
        return v

@app.post("/generate_test")
def generate_test(request: TestRequest):
    try:
        logger.info(f"生成诊断测试: 学科={request.subject}, 年级={request.grade}, 题型={request.question_type}")
        result = coordinator.generate_diagnostic_test(
            request.subject,
            request.grade,
            question_type=request.question_type,
            question_count=request.question_count
        )
        return result
    except Exception as e:
        logger.error(f"生成测试失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# 评估测试
class EvaluationRequest(BaseModel):
    test_questions: list
    student_answers: list
    
    @field_validator('test_questions', 'student_answers')
    @classmethod
    def validate_not_empty(cls, v, info):
        if not v:
            raise ValueError(f'{info.name}不能为空')
        return v

@app.post("/evaluate_test")
def evaluate_test(request: EvaluationRequest):
    try:
        logger.info(f"评估测试: {len(request.test_questions)}道题目")
        result = coordinator.evaluate_test(request.test_questions, request.student_answers)
        return result
    except Exception as e:
        logger.error(f"评估测试失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# 获取薄弱点
class WeakPointsRequest(BaseModel):
    test_results: dict

@app.post("/get_weak_points")
def get_weak_points(request: WeakPointsRequest):
    try:
        result = coordinator.get_weak_points(request.test_results)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 基于薄弱点生成练习
class WeakPointPracticeRequest(BaseModel):
    subject: str
    grade: str
    weak_knowledge_points: list
    question_type: str = "mixed"
    question_count: int = 5

    @field_validator('subject')
    @classmethod
    def validate_subject(cls, v):
        if v not in ['语文', '数学']:
            raise ValueError('学科必须是"语文"或"数学"')
        return v

    @field_validator('grade')
    @classmethod
    def validate_grade(cls, v):
        if v not in ['一年级', '二年级']:
            raise ValueError('年级必须是"一年级"或"二年级"')
        return v

    @field_validator('question_type')
    @classmethod
    def validate_question_type(cls, v):
        if v not in ['mixed', 'choice', 'fill', 'judge']:
            raise ValueError('题型必须是 mixed/choice/fill/judge')
        return v

@app.post("/generate_weak_point_practice")
def generate_weak_point_practice(request: WeakPointPracticeRequest):
    try:
        logger.info(f"生成薄弱点练习: {request.subject} {request.grade}，薄弱点={request.weak_knowledge_points}")
        result = coordinator.generate_weak_point_practice(
            request.subject,
            request.grade,
            request.weak_knowledge_points,
            request.question_type,
            request.question_count
        )
        return result
    except Exception as e:
        logger.error(f"薄弱点练习生成失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# 获取知识地图
@app.get("/get_knowledge_map/{subject}")
def get_knowledge_map(subject: str):
    try:
        logger.info(f"获取知识地图: {subject}")
        
        if subject not in ['语文', '数学']:
            raise HTTPException(status_code=400, detail="学科必须是'语文'或'数学'")
        
        from src.services.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.load_graph(f"{subject}_knowledge_map.json")
        
        # 构建返回数据
        nodes = []
        edges = []
        
        for node in kg.graph.nodes:
            node_data = kg.graph.nodes[node]
            nodes.append({
                "id": node,
                "label": node_data.get("name", ""),
                "subject": node_data.get("subject", ""),
                "grade": node_data.get("grade", ""),
                "content": node_data.get("content", "")
            })
        
        for edge in kg.graph.edges:
            edges.append({
                "from": edge[0],
                "to": edge[1],
                "label": kg.graph.edges[edge].get("relation", "关联")
            })
        
        logger.info(f"知识地图获取成功: {len(nodes)}个节点, {len(edges)}条边")
        return {"status": "success", "nodes": nodes, "edges": edges}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识地图失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# 获取学习历史
class HistoryRequest(BaseModel):
    subject: Optional[str] = None
    grade: Optional[str] = None
    limit: int = 10

@app.post("/get_learning_history")
def get_learning_history(request: HistoryRequest):
    try:
        from src.services.learning_history import LearningHistoryManager
        manager = LearningHistoryManager()
        history = manager.get_history(request.subject, request.grade, request.limit)
        return {"status": "success", "history": history}
    except Exception as e:
        logger.error(f"获取学习历史失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# 获取薄弱点趋势
class WeakTrendRequest(BaseModel):
    subject: Optional[str] = None
    grade: Optional[str] = None
    limit: int = 10

@app.post("/get_weak_point_trends")
def get_weak_point_trends(request: WeakTrendRequest):
    try:
        from src.services.learning_history import LearningHistoryManager
        manager = LearningHistoryManager()
        trends = manager.get_weak_point_trends(request.subject, request.grade, request.limit)
        return {"status": "success", "trends": trends}
    except Exception as e:
        logger.error(f"获取薄弱点趋势失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# 主入口
# 缓存管理 API
class ClearCacheRequest(BaseModel):
    cache_type: str = "all"  # all / image / process / status

@app.post("/clear_cache")
def clear_cache(request: ClearCacheRequest):
    """清理缓存"""
    try:
        from src.utils.cache_manager import CacheManager
        cm = CacheManager()
        if request.cache_type == "all":
            cm.clear_all_cache()
            cm.clear_all_status()
        elif request.cache_type == "image":
            cm.clear_image_cache_only()
        elif request.cache_type == "process":
            cm.clear_process_cache_only()
        elif request.cache_type == "status":
            cm.clear_all_status()
        else:
            raise ValueError("cache_type 必须是 all/image/process/status")
        return {"status": "success", "message": f"{request.cache_type} 缓存已清理"}
    except Exception as e:
        logger.error(f"清理缓存失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache_stats")
def cache_stats():
    """获取缓存统计"""
    try:
        from src.utils.cache_manager import CacheManager
        cm = CacheManager()
        return {"status": "success", "stats": cm.get_cache_stats()}
    except Exception as e:
        logger.error(f"获取缓存统计失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)