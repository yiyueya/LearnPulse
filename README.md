# LearnPulse — AI 智能学习助手

> 专为小学1-2年级学生打造的语文和数学个性化学习辅导系统

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 功能特性

### 📚 核心功能

- **PDF 知识提取** — 上传语文/数学教材 PDF，自动提取文本和图片内容
- **知识图谱构建** — 将教材内容转化为可视化的知识网络图
- **智能出题** — 根据知识点生成诊断测试题（选择题、填空题、判断题）
- **答案评估** — AI 自动批改学生答案，给出详细反馈
- **薄弱点分析** — 精准定位学生薄弱知识点
- **针对性练习** — 基于薄弱点生成个性化练习题
- **学习路径推荐** — 根据知识图谱推荐最优学习顺序

### 🎯 支持学科与年级

| 学科 | 年级 | 题型 |
|------|------|------|
| 语文 | 一年级、二年级 | 拼音、汉字、词语、句子、阅读 |
| 数学 | 一年级、二年级 | 加减法、乘法、图形、计量单位、应用题 |

### 💡 技术亮点

- **多 Agent 协作** — ContentExtractor → KnowledgeGraph → QuestionGenerator → AnswerEvaluator → AnalysisAgent 流水线
- **实时进度流** — SSE 实时推送处理进度，支持取消操作
- **智能缓存** — AI 响应缓存 + 处理状态持久化，避免重复调用
- **图片批量处理** — 智能合并图片，适配 MiniMax 5MB 接口限制
- **D3.js 可视化** — 知识图谱交互式可视化展示

## 系统要求

- Python 3.9+
- MiniMax API Key（用于 AI 能力）
- 建议 4GB+ 内存

## 快速开始

### 1. 克隆项目

```bash
cd /home/lin/.openclaw/projects/LearnPulse
```

### 2. 配置 API Key

```bash
# 编辑 .env 文件，填入你的 MiniMax API Key
echo "MINIMAX_API_KEY=your_api_key_here" > .env
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 启动服务

```bash
python app.py
# 或使用启动脚本
bash start.sh
```

服务启动后访问：**http://127.0.0.1:8000**

## 使用流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  上传 PDF   │ ──▶ │  构建知识图谱 │ ──▶ │  生成诊断测试 │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                   ┌─────────────┐     ┌─────────────┐
                   │薄弱点练习生成│ ◀── │  答案评估    │
                   └─────────────┘     └─────────────┘
```

1. **上传教材 PDF** — 将语文或数学教材 PDF 上传到 `data/语文/` 或 `data/数学/` 目录
2. **处理教材** — 点击处理，系统自动提取知识点并构建知识图谱
3. **生成测试** — 选择学科、年级、题型，生成诊断测试
4. **提交答案** — 学生作答后提交，系统自动批改
5. **查看薄弱点** — 根据测试结果查看薄弱知识点
6. **针对性练习** — 基于薄弱点生成个性化练习题

## API 接口

### 文档处理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/upload_pdf` | POST | 上传 PDF 文件 |
| `/process_pdfs_stream` | GET | 处理 PDF（SSE 实时进度） |
| `/cancel_process` | POST | 取消正在进行的处理 |
| `/get_pending_files` | GET | 获取待处理文件列表 |
| `/get_uploaded_files` | GET | 获取已上传文件及状态 |

### 测试生成

| 接口 | 方法 | 说明 |
|------|------|------|
| `/generate_test` | POST | 生成诊断测试题 |
| `/generate_test_pdf` | POST | 生成测试卷 PDF 下载 |
| `/evaluate_test` | POST | 评估学生答案 |
| `/get_weak_points` | POST | 获取薄弱知识点 |
| `/generate_weak_point_practice` | POST | 生成薄弱点练习 |

### 知识图谱

| 接口 | 方法 | 说明 |
|------|------|------|
| `/get_knowledge_map/{subject}` | GET | 获取知识地图 |
| `/rebuild_knowledge_map/{subject}` | POST | 重建知识地图 |
| `/get_learning_path/{node_id}` | GET | 获取学习路径 |
| `/get_next_learning/{node_id}` | GET | 获取后续学习节点 |

### 其他

| 接口 | 方法 | 说明 |
|------|------|------|
| `/get_learning_history` | POST | 获取学习历史 |
| `/get_weak_point_trends` | POST | 获取薄弱点趋势 |
| `/clear_cache` | POST | 清理缓存 |
| `/cache_stats` | GET | 获取缓存统计 |

## 项目结构

```
LearnPulse/
├── app.py                      # FastAPI 主应用入口
├── config/
│   └── config.py               # 配置文件
├── src/
│   ├── agents/                 # Agent 模块
│   │   ├── agent_coordinator.py    # Agent 协调器
│   │   ├── content_extractor_agent.py  # PDF 内容提取
│   │   ├── knowledge_graph_agent.py     # 知识图谱构建
│   │   ├── question_generator_agent.py  # 题目生成
│   │   ├── answer_evaluator_agent.py    # 答案评估
│   │   └── analysis_agent.py            # 薄弱点分析
│   ├── services/               # 服务模块
│   │   ├── ai_service.py           # AI 接口调用
│   │   ├── knowledge_graph.py       # 知识图谱存储
│   │   └── learning_history.py      # 学习历史管理
│   └── utils/                  # 工具模块
│       ├── cache_manager.py        # 缓存管理
│       ├── logger.py               # 日志
│       └── pdf_generator.py        # PDF 生成
├── static/
│   └── index.html              # 前端页面
├── data/
│   ├── 语文/                   # 语文教材 PDF
│   ├── 数学/                   # 数学教材 PDF
│   ├── json/                  # 提取的 JSON 数据
│   └── cache/                  # AI 响应缓存
├── tests/                      # 单元测试
├── CLAUDE.md                   # Claude Code 开发指南
├── start.sh                   # 启动脚本
└── requirements.txt           # Python 依赖
```

## 开发指南

### 运行测试

```bash
# 所有测试
pytest

# 指定测试文件
pytest tests/test_cache.py -v

# 指定测试函数
pytest tests/test_cache.py::test_cache_stats -v
```

### 调试模式

```bash
# 查看日志
tail -f app.log

# 或直接运行（带实时日志）
python app.py
```

## 技术栈

- **后端**: FastAPI + Uvicorn
- **AI 服务**: MiniMax API（文字理解 + 图片理解）
- **知识图谱**: NetworkX
- **PDF 处理**: pdfplumber + Pillow
- **前端**: 原生 HTML/CSS/JS + D3.js + vis.js
- **缓存**: JSON 文件持久化

## 注意事项

1. **API Key** — 必须配置有效的 MiniMax API Key，否则 AI 功能不可用
2. **PDF 命名** — 文件名建议包含学科和年级，如 `数学一年级第一单元.pdf`
3. **内存限制** — WSL 环境下注意内存使用，图片批量处理有 5MB 限制
4. **缓存清理** — 调试时可使用 `/clear_cache` 接口清理缓存

## License

MIT
