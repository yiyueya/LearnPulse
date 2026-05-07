# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

LearnPulse is an AI-powered learning assistant for elementary school students (grades 1-2) in Chinese language (语文) and mathematics (数学). The system extracts knowledge from PDFs, builds knowledge graphs, generates diagnostic tests, evaluates answers, and identifies weak points.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Run all tests
pytest

# Run a specific test file
pytest tests/test_cache.py

# Run a specific test function
pytest tests/test_cache.py::test_cache_stats -v
```

## Architecture

### Core Flow

1. **PDF Upload & Processing** → ContentExtractor parses PDFs, extracts text and images
2. **Knowledge Graph Build** → KnowledgeGraphAgent converts extracted content into NetworkX knowledge graphs
3. **Test Generation** → QuestionGeneratorAgent generates questions from knowledge graph nodes
4. **Test Evaluation** → AnswerEvaluatorAgent evaluates student answers
5. **Weak Point Analysis** → AnalysisAgent identifies weak knowledge points from test results

### Agent System

The `AgentCoordinator` (`src/agents/agent_coordinator.py`) orchestrates all agents:
- `ContentExtractorAgent` - Extracts content from PDF documents
- `KnowledgeGraphAgent` - Builds knowledge maps from extracted content
- `QuestionGeneratorAgent` - Generates test questions via AI
- `AnswerEvaluatorAgent` - Evaluates student answers
- `AnalysisAgent` - Analyzes performance and identifies weak points

### Services

- **AIService** (`src/services/ai_service.py`) - Handles all MiniMax API calls for text and image understanding. Includes caching (file-based + memory), quota tracking, and batch image processing with smart grouping under 5MB limits.
- **KnowledgeGraph** (`src/services/knowledge_graph.py`) - NetworkX-based knowledge graph storage
- **LearningHistory** (`src/services/learning_history.py`) - Tracks student performance over time

### Data Structure

```
data/
  pdfs/           # Uploaded PDF files
  json/           # Extracted knowledge JSON files
  knowledge_map/  # Built knowledge graph JSON files
  cache/          # AI response cache (JSON files)
```

### API Endpoints

- `POST /process_pdfs` - Process PDFs and build knowledge maps
- `POST /generate_test` - Generate diagnostic test questions
- `POST /evaluate_test` - Evaluate student answers
- `GET /get_knowledge_map/{subject}` - Retrieve knowledge graph
- `POST /clear_cache` - Clear AI response cache

### Key Configuration

`config/config.py` contains all settings:
- `MINIMAX_API_KEY` - Required for AI features (set in `.env`)
- `IMAGE_SMART_FILTER` - Enable/disable intelligent image filtering
- `MAX_MERGED_SIZE_MB` - 5MB limit for batch image processing
- `MAX_IMAGE_BATCH_WORKERS` - 2 (WSL memory constrained environment)

### Frontend

Single-page application in `static/index.html` with:
- D3.js knowledge map visualization
- Server-Sent Events (SSE) for real-time progress
- PDF upload and file selection UI