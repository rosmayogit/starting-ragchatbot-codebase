# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Run Commands

**Always use `uv` to manage all dependencies - never use `pip` directly.**

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add <package>

# Remove a dependency
uv remove <package>

# Run the application (from project root)
./run.sh

# Or manually
cd backend && uv run uvicorn app:app --reload --port 8000

# Run any Python script
uv run python <script.py>
```

Access points:
- Web UI: http://localhost:8000
- API docs: http://localhost:8000/docs

## Environment Setup

Requires `.env` file in project root with:
```
ANTHROPIC_API_KEY=your_key_here
```

## Architecture

This is a Course Materials RAG (Retrieval-Augmented Generation) system with a client-server architecture.

### Request Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (script.js)                                                       │
│  User query ──► POST /api/query {query, session_id}                         │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  BACKEND                                                                    │
│                                                                             │
│  ┌─────────┐    ┌─────────────┐    ┌──────────────┐                         │
│  │ app.py  │───►│ rag_system  │───►│ ai_generator │                         │
│  │(FastAPI)│    │  .query()   │    │              │                         │
│  └─────────┘    └─────────────┘    └──────┬───────┘                         │
│                                           │                                 │
│                                           ▼                                 │
│                            ┌─────────────────────────┐                      │
│                            │     Claude API Call     │                      │
│                            │     (with tools)        │                      │
│                            └───────────┬─────────────┘                      │
│                                        │                                    │
│                       ┌────────────────┴────────────────┐                   │
│                       ▼                                 ▼                   │
│            ┌──────────────────┐              ┌──────────────────┐           │
│            │  Direct Answer   │              │  Tool Use        │           │
│            │  (no search)     │              │  (search needed) │           │
│            └────────┬─────────┘              └────────┬─────────┘           │
│                     │                                 │                     │
│                     │                                 ▼                     │
│                     │                    ┌───────────────────────┐          │
│                     │                    │  CourseSearchTool     │          │
│                     │                    │  (search_tools.py)    │          │
│                     │                    └───────────┬───────────┘          │
│                     │                                │                      │
│                     │                                ▼                      │
│                     │                    ┌───────────────────────┐          │
│                     │                    │  VectorStore.search() │          │
│                     │                    │  (ChromaDB)           │          │
│                     │                    └───────────┬───────────┘          │
│                     │                                │                      │
│                     │                                ▼                      │
│                     │                    ┌───────────────────────┐          │
│                     │                    │  Results ──► Claude   │          │
│                     │                    │  ──► Final Response   │          │
│                     │                    └───────────┬───────────┘          │
│                     │                                │                      │
│                     └────────────────┬───────────────┘                      │
│                                      │                                      │
│                                      ▼                                      │
│                       { answer, sources, session_id }                       │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND                                                                   │
│  Render markdown answer + collapsible sources                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| RAGSystem | `rag_system.py` | Central orchestrator |
| VectorStore | `vector_store.py` | ChromaDB wrapper with two collections: `course_catalog` (metadata) and `course_content` (chunks) |
| AIGenerator | `ai_generator.py` | Claude API wrapper with tool execution loop |
| DocumentProcessor | `document_processor.py` | Parses course docs, chunks text with sentence-aware splitting |
| ToolManager | `search_tools.py` | Registers tools, executes them, tracks sources |

### Document Format

Course documents in `docs/` must follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 0: Introduction
Lesson Link: [url]
[content...]

Lesson 1: Getting Started
...
```

### Configuration

All tunable parameters are in `backend/config.py`:
- Chunk size: 800 chars, overlap: 100 chars
- Max search results: 5
- Conversation history: 2 messages
- Embedding model: `all-MiniLM-L6-v2`
- Claude model: `claude-sonnet-4-20250514`
