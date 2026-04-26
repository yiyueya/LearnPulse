# AI智能学习助手 - API文档

## 基础信息
- **服务地址**: http://localhost:8000
- **API前缀**: 无
- **数据格式**: JSON
- **认证方式**: 无（本地服务）

## API端点

### 1. 健康检查
**URL**: `GET /health`

**描述**: 检查服务状态和配置信息

**响应示例**:
```json
{
  "status": "healthy",
  "api_key_status": "configured",
  "version": "1.0.0"
}
```

**字段说明**:
- `status`: 服务状态（healthy/unhealthy）
- `api_key_status`: API密钥状态（configured/missing）
- `version`: API版本号

---

### 2. SSE实时进度推送
**URL**: `GET /process_pdfs_stream`

**描述**: 通过Server-Sent Events实时推送PDF处理进度

**响应格式**:
```
data: {"is_processing": true, "progress": 25, "message": "正在处理..."}

data: {"is_processing": true, "progress": 50, "message": "处理中..."}

data: {"is_processing": false, "progress": 100, "message": "处理完成！", "result": {...}}
```

**事件字段**:
- `is_processing`: 是否正在处理
- `progress`: 处理进度（0-100）
- `message`: 当前处理状态消息
- `result`: 处理结果（完成后返回）

---

### 3. 处理PDF文档
**URL**: `POST /process_pdfs`

**描述**: 处理data目录下的所有PDF文档，提取知识点并构建知识地图

**请求参数**: 无

**请求示例**:
```bash
curl -X POST http://localhost:8000/process_pdfs
```

**成功响应**:
```json
{
  "extraction_results": {
    "数学": {
      "文件名.pdf": {
        "status": "success",
        "data": {
          "knowledge_points": [...],
          "chapters": [...]
        },
        "file": "data/json/数学_一年级_文件名.json",
        "extracted_data": {
          "text_length": 12345,
          "image_count": 5,
          "images_understood": 5
        }
      }
    }
  },
  "knowledge_map_results": {
    "数学": {
      "status": "success",
      "message": "数学学科知识地图构建完成"
    }
  }
}
```

**错误响应**:
```json
{
  "status": "error",
  "error_type": "INTERNAL_ERROR",
  "message": "服务器内部错误: 具体错误信息"
}
```

---

### 4. 生成诊断测试
**URL**: `POST /generate_test`

**描述**: 基于知识地图生成诊断测试题目

**请求参数**:
```json
{
  "subject": "数学",
  "grade": "一年级"
}
```

**参数说明**:
- `subject`: 学科（必填），可选值：`数学`、`语文`
- `grade`: 年级（必填），可选值：`一年级`、`二年级`

**请求示例**:
```bash
curl -X POST http://localhost:8000/generate_test \
  -H "Content-Type: application/json" \
  -d '{"subject": "数学", "grade": "一年级"}'
```

**成功响应**:
```json
{
  "status": "success",
  "questions": [
    {
      "id": 1,
      "type": "选择题",
      "question": "1+1=?",
      "options": ["1", "2", "3", "4"],
      "answer": "2",
      "knowledge_point": "加法",
      "difficulty": "基础"
    }
  ],
  "total_questions": 10,
  "estimated_time": "8分钟"
}
```

**错误响应**:
```json
{
  "detail": "学科必须是\"语文\"或\"数学\""
}
```

---

### 5. 评估测试
**URL**: `POST /evaluate_test`

**描述**: 评估学生的测试答案，并生成薄弱点分析

**请求参数**:
```json
{
  "test_questions": [
    {
      "id": 1,
      "type": "选择题",
      "question": "1+1=?",
      "options": ["1", "2", "3", "4"],
      "answer": "2",
      "knowledge_point": "加法"
    }
  ],
  "student_answers": ["2"]
}
```

**参数说明**:
- `test_questions`: 题目列表（必填，不能为空）
- `student_answers`: 学生答案列表（必填，不能为空）

**请求示例**:
```bash
curl -X POST http://localhost:8000/evaluate_test \
  -H "Content-Type: application/json" \
  -d '{
    "test_questions": [{"id": 1, "question": "1+1=?", "answer": "2", "type": "选择题"}],
    "student_answers": ["2"]
  }'
```

**成功响应**:
```json
{
  "status": "success",
  "results": [
    {
      "question_id": 1,
      "question": "1+1=?",
      "correct_answer": "2",
      "student_answer": "2",
      "is_correct": true,
      "feedback": "回答正确！",
      "knowledge_point": "加法"
    }
  ],
  "score": 1,
  "total": 1,
  "accuracy": 100.0,
  "analysis": {
    "total_questions": 1,
    "correct_count": 1,
    "wrong_count": 0,
    "accuracy": 100.0,
    "weak_knowledge": [],
    "knowledge_distribution": {
      "加法": {"total": 1, "correct": 1}
    },
    "suggestions": [
      "继续保持，当前知识点掌握良好"
    ]
  }
}
```

**错误响应**:
```json
{
  "detail": "test_questions不能为空"
}
```

---

### 6. 获取薄弱点
**URL**: `POST /get_weak_points`

**描述**: 分析测试结果，获取薄弱知识点并生成学习建议

**请求参数**:
```json
{
  "test_results": {
    "results": [...],
    "score": 8,
    "total": 10,
    "accuracy": 80.0,
    "analysis": {...}
  }
}
```

**成功响应**:
```json
{
  "status": "success",
  "report": {
    "total_questions": 10,
    "correct_count": 8,
    "wrong_count": 2,
    "accuracy": 80.0,
    "weak_knowledge": [
      {
        "knowledge": "减法",
        "count": 2,
        "accuracy": 50.0,
        "suggestion": "建议加强减法运算练习"
      }
    ],
    "knowledge_summary": {
      "已掌握": ["加法", "认识图形"],
      "待加强": ["减法", "应用题"]
    },
    "suggestions": [
      "加强减法的练习，建议每天练习相关题目",
      "应用题需要加强理解能力的培养"
    ]
  }
}
```

---

### 7. 获取知识地图
**URL**: `GET /get_knowledge_map/{subject}`

**描述**: 获取指定学科的知识地图结构

**路径参数**:
- `subject`: 学科名称（必填），可选值：`数学`、`语文`

**请求示例**:
```bash
curl -X GET http://localhost:8000/get_knowledge_map/数学
```

**成功响应**:
```json
{
  "status": "success",
  "nodes": [
    {
      "id": "kp_1",
      "label": "加法",
      "subject": "数学",
      "grade": "一年级",
      "content": "掌握10以内数的加法运算..."
    }
  ],
  "edges": [
    {
      "from": "kp_1",
      "to": "kp_2",
      "relation": "前置知识"
    }
  ],
  "statistics": {
    "total_nodes": 50,
    "total_edges": 45
  }
}
```

**错误响应**:
```json
{
  "detail": "学科必须是'语文'或'数学'"
}
```

---

### 8. 获取待处理文件列表
**URL**: `GET /get_pending_files`

**描述**: 获取需要处理的PDF文件列表

**成功响应**:
```json
{
  "status": "success",
  "files": [
    {
      "path": "data/数学/教材.pdf",
      "subject": "数学",
      "grade": "一年级",
      "modified_time": "2026-04-20T10:00:00",
      "needs_processing": true
    }
  ]
}
```

---

### 9. 获取文件处理状态
**URL**: `GET /get_file_status/{file_path}`

**描述**: 获取指定文件的处理状态

**路径参数**:
- `file_path`: 文件路径（URL编码）

**成功响应**:
```json
{
  "status": "success",
  "file_status": {
    "path": "data/数学/教材.pdf",
    "status": "completed",
    "current_step": 4,
    "total_steps": 4,
    "last_processed": "2026-04-23T15:30:00"
  }
}
```

---

## 错误代码说明

### HTTP状态码
- `200`: 请求成功
- `400`: 请求参数错误
- `500`: 服务器内部错误

### 错误类型（error_type）
- `API_KEY_MISSING`: API密钥未配置
- `PROCESSING_ERROR`: 处理过程中的错误
- `INTERNAL_ERROR`: 服务器内部错误
- `VALIDATION_ERROR`: 数据验证错误

### 常见错误信息
```json
{
  "detail": "学科必须是\"语文\"或\"数学\""
}
```
原因：subject字段传递了不支持的值

```json
{
  "status": "error",
  "error_type": "API_KEY_MISSING",
  "message": "API密钥未配置，请检查环境变量设置"
}
```
原因：MINIMAX_API_KEY环境变量未设置

```json
{
  "status": "error",
  "error_type": "PROCESSING_ERROR",
  "message": "PDF文本提取失败"
}
```
原因：PDF文件无法正常解析

## 使用流程

### 完整使用流程

1. **检查服务状态**
   ```bash
   GET /health
   ```
   确认api_key_status为"configured"

2. **处理PDF文档（可选，如果知识地图已构建可跳过）**
   ```bash
   # 方式1：同步处理
   POST /process_pdfs

   # 方式2：实时进度推送（推荐）
   GET /process_pdfs_stream
   ```

3. **生成诊断测试**
   ```bash
   POST /generate_test
   body: {"subject": "数学", "grade": "一年级"}
   ```

4. **学生答题**

5. **评估测试**
   ```bash
   POST /evaluate_test
   body: {"test_questions": [...], "student_answers": [...]}
   ```

6. **获取薄弱点分析**
   ```bash
   POST /get_weak_points
   body: {"test_results": {...}}
   ```

7. **查看知识地图**
   ```bash
   GET /get_knowledge_map/数学
   ```

## 注意事项

### 环境配置
- 确保 `.env` 文件中配置了 `MINIMAX_API_KEY`
- API密钥可从阿里云百炼平台获取

### PDF文件要求
- 支持格式：`.pdf`
- 建议放置在 `data/数学/` 或 `data/语文/` 目录
- 文件名需包含年级信息（如"一年级"、"二年级"）

### 性能优化
- PDF处理可能需要较长时间（每个文件约2-5分钟）
- 建议使用SSE端点 `/process_pdfs_stream` 实时监控进度
- 已处理的文件会自动使用缓存，加快处理速度

### 错误处理
- 所有API都包含完善的错误处理和日志记录
- 建议实现重试机制应对临时性网络错误
- 详细错误信息可在日志文件中查看（`logs/app_*.log`）

### 日志文件
- 位置：`logs/app_YYYY-MM-DD.log`
- 记录内容：API调用、处理进度、错误信息
- 可用于调试和监控

## 响应状态说明

### processing_status状态
```json
{
  "is_processing": true,
  "progress": 50,
  "message": "正在处理第3个文件...",
  "result": null
}
```

字段说明：
- `is_processing`: 是否正在处理
- `progress`: 处理进度百分比（0-100）
- `message`: 当前状态描述
- `result`: 处理结果（仅在is_processing=false时有效）
