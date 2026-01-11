# Architecture Documentation

This document provides a comprehensive overview of the Course Materials RAG system architecture, including the codebase structure, document processing pipeline, and query flow.

## Table of Contents

- [Codebase Overview](#codebase-overview)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Key Components](#key-components)
- [Document Processing Pipeline](#document-processing-pipeline)
- [Query Flow](#query-flow)

---

## Codebase Overview

This is a **Course Materials RAG (Retrieval-Augmented Generation) System** - a full-stack web application that lets users ask questions about course materials and receive AI-powered, source-cited answers.

The project follows a **client-server architecture** with:
- **Backend**: Python FastAPI server handling RAG logic, vector storage, and AI generation
- **Frontend**: HTML/CSS/JavaScript single-page application for user interactions
- **Vector Database**: ChromaDB for semantic search and content storage

---

## Project Structure

```
rag/
├── backend/                    # Python FastAPI backend
│   ├── app.py                 # FastAPI endpoints
│   ├── rag_system.py          # Main RAG orchestrator
│   ├── vector_store.py        # ChromaDB semantic search
│   ├── ai_generator.py        # Claude API integration
│   ├── document_processor.py  # Document parsing & chunking
│   ├── search_tools.py        # Tool definitions for Claude
│   ├── session_manager.py     # Conversation history
│   ├── models.py              # Pydantic data models
│   ├── config.py              # Configuration
│   └── chroma_db/             # Vector database storage
├── frontend/                   # Web UI
│   ├── index.html             # Main interface
│   ├── script.js              # Client-side logic
│   └── style.css              # Dark theme styling
├── docs/                       # Course materials (source documents)
│   ├── course1_script.txt
│   ├── course2_script.txt
│   ├── course3_script.txt
│   └── course4_script.txt
├── pyproject.toml             # Dependencies
├── .env.example               # Example environment variables
├── .env                       # API keys (not tracked)
├── main.py                    # Root entry point
└── run.sh                     # Startup script
```

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | FastAPI, Uvicorn, Python 3.13+ |
| AI | Anthropic Claude (claude-sonnet-4-20250514) |
| Vector DB | ChromaDB with SentenceTransformers (`all-MiniLM-L6-v2`) |
| Frontend | Vanilla HTML/CSS/JS, Marked.js for markdown |

### Configuration Settings

| Setting | Value | Description |
|---------|-------|-------------|
| Embedding Model | `all-MiniLM-L6-v2` | Lightweight model for text embeddings |
| Claude Model | `claude-sonnet-4-20250514` | AI generation model |
| Chunk Size | 800 characters | Maximum size per text chunk |
| Chunk Overlap | 100 characters | Overlap between consecutive chunks |
| Max Search Results | 5 | Maximum results returned per search |
| Conversation History | 2 messages | Messages retained for context |

---

## Key Components

### Backend Components

#### `app.py` (Entry Point)
- Initializes FastAPI application
- Defines API endpoints:
  - `POST /api/query` - Process user queries and return AI responses with sources
  - `GET /api/courses` - Get course statistics and catalog
- Serves frontend static files
- Auto-loads documents from `../docs` on startup

#### `rag_system.py` (Orchestrator)
- Central coordinator for the entire RAG pipeline
- Key methods:
  - `add_course_document()` - Add single course to knowledge base
  - `add_course_folder()` - Batch load courses with duplicate prevention
  - `query()` - Main query processing with tool-based search
  - `get_course_analytics()` - Return course catalog statistics

#### `vector_store.py` (Semantic Search Engine)
- Uses ChromaDB with SentenceTransformers embeddings
- Two collections:
  - `course_catalog` - Course metadata for semantic name matching
  - `course_content` - Course lesson chunks for content search
- Supports course filtering and lesson filtering

#### `ai_generator.py` (Claude Integration)
- Wraps Anthropic's Claude API
- Features:
  - Tool-aware prompt engineering with system instructions
  - One-search-per-query limitation to focus responses
  - Conversation history support for context
  - Tool execution handling with agentic loop

#### `document_processor.py` (Document Parsing)
- Processes `.pdf`, `.docx`, and `.txt` files
- Parses structured course format with metadata and lessons
- Smart sentence-based chunking with overlap

#### `search_tools.py` (Tool Framework)
- Abstract `Tool` base class for extensibility
- `CourseSearchTool` - Registered as Claude tool for agentic calling
- `ToolManager` - Coordinates tool registration and execution

#### `session_manager.py` (Conversation Context)
- Manages conversation sessions with unique IDs
- Stores message history per session
- Formats history for Claude context

### Frontend Components

#### `index.html`
- Dark-themed interface with collapsible sidebars
- Left sidebar for course statistics and suggested questions
- Main chat area for message thread and input

#### `script.js`
- Session management with persistent session ID
- Message handling with markdown rendering
- Source display in collapsible details

#### `style.css`
- Dark theme with CSS variables
- Responsive design with mobile breakpoints
- Custom scrollbars and animations

---

## Document Processing Pipeline

The `DocumentProcessor` class handles document ingestion with a structured format and intelligent chunking.

### Expected Document Format

```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 0: Introduction
Lesson Link: [url]
[lesson content...]

Lesson 1: Getting Started
Lesson Link: [url]
[lesson content...]
```

### Processing Steps

#### 1. File Reading
- Reads files with UTF-8 encoding
- Falls back to ignoring errors if UTF-8 decoding fails

#### 2. Metadata Extraction
- Parses first 3-4 lines for course metadata:
  - Course title (regex: `^Course Title:\s*(.+)$`)
  - Course link
  - Instructor name
- Creates a `Course` object with this metadata

#### 3. Lesson Parsing
- Scans for lesson markers: `Lesson N: Title`
- Extracts optional lesson links (`Lesson Link: [url]`)
- Collects all content between lesson markers
- Creates `Lesson` objects for each lesson found

#### 4. Text Chunking
- **Normalizes whitespace** - Collapses multiple spaces/newlines
- **Sentence-aware splitting** - Uses regex that handles abbreviations:
  ```python
  r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+(?=[A-Z])'
  ```
- **Builds chunks up to 800 characters** (configurable)
- **Adds 100-character overlap** between chunks to preserve context

#### 5. Chunk Creation
- First chunk of each lesson gets context prefix: `"Lesson N content: ..."`
- Each chunk becomes a `CourseChunk` object with:
  - `content` - The text
  - `course_title` - Parent course
  - `lesson_number` - Which lesson
  - `chunk_index` - Sequential ID

### Chunking Algorithm Visualization

```
Original text (2500 chars)
    |
    v
Split into sentences
    |
    v
[Sent1] [Sent2] [Sent3] [Sent4] [Sent5] [Sent6] [Sent7] ...
    |
    v
Build chunks (<=800 chars each, with 100 char overlap)
    |
    v
Chunk 1: [Sent1 Sent2 Sent3]
Chunk 2: [Sent3 Sent4 Sent5]  <- overlaps with previous
Chunk 3: [Sent5 Sent6 Sent7]  <- overlaps with previous
```

### Fallback Behavior

If no lesson markers are found, the entire document content is chunked as a single unit without lesson structure.

---

## Query Flow

This section traces the complete flow of a user query from the frontend to the backend and back.

### Step 1: Frontend Sends Query

**Location:** `frontend/script.js:45-72`

```javascript
async function sendMessage() {
    const query = chatInput.value.trim();

    const response = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query: query,
            session_id: currentSessionId  // null on first request
        })
    });

    const data = await response.json();
    // data = { answer, sources, session_id }
}
```

### Step 2: FastAPI Receives Request

**Location:** `backend/app.py:56-74`

```python
@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    # Create session if not provided
    session_id = request.session_id or rag_system.session_manager.create_session()

    # Process query using RAG system
    answer, sources = rag_system.query(request.query, session_id)

    return QueryResponse(answer=answer, sources=sources, session_id=session_id)
```

### Step 3: RAG System Orchestrates

**Location:** `backend/rag_system.py:102-140`

```python
def query(self, query: str, session_id: Optional[str] = None):
    prompt = f"Answer this question about course materials: {query}"

    # Get conversation history
    history = self.session_manager.get_conversation_history(session_id)

    # Generate response with tools available
    response = self.ai_generator.generate_response(
        query=prompt,
        conversation_history=history,
        tools=self.tool_manager.get_tool_definitions(),
        tool_manager=self.tool_manager
    )

    # Get sources from search tool
    sources = self.tool_manager.get_last_sources()
    self.tool_manager.reset_sources()

    # Save to history
    self.session_manager.add_exchange(session_id, query, response)

    return response, sources
```

### Step 4: Claude Decides Whether to Search

**Location:** `backend/ai_generator.py:43-87`

```python
def generate_response(self, query, conversation_history, tools, tool_manager):
    # Build system prompt with conversation context
    system_content = f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{history}"

    # Call Claude API with tools
    response = self.client.messages.create(
        model="claude-sonnet-4-20250514",
        temperature=0,
        max_tokens=800,
        messages=[{"role": "user", "content": query}],
        system=system_content,
        tools=tools,
        tool_choice={"type": "auto"}  # Claude decides
    )

    # If Claude wants to use a tool
    if response.stop_reason == "tool_use":
        return self._handle_tool_execution(response, api_params, tool_manager)

    # Otherwise return direct answer
    return response.content[0].text
```

### Step 5: Tool Execution (if needed)

**Location:** `backend/ai_generator.py:89-135`

```python
def _handle_tool_execution(self, initial_response, base_params, tool_manager):
    messages = [{"role": "user", "content": query}]
    messages.append({"role": "assistant", "content": initial_response.content})

    # Execute each tool call
    tool_results = []
    for block in initial_response.content:
        if block.type == "tool_use":
            result = tool_manager.execute_tool(block.name, **block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result
            })

    messages.append({"role": "user", "content": tool_results})

    # Get final response from Claude with search results
    final_response = self.client.messages.create(messages=messages, ...)
    return final_response.content[0].text
```

### Step 6: Search Tool Queries Vector Store

**Location:** `backend/search_tools.py:52-86`

```python
def execute(self, query: str, course_name=None, lesson_number=None):
    # Search ChromaDB via vector store
    results = self.store.search(
        query=query,
        course_name=course_name,
        lesson_number=lesson_number
    )

    # Track sources for UI display
    self.last_sources = ["Course A - Lesson 1", "Course B - Lesson 3", ...]

    # Return formatted results to Claude
    return "[Course A - Lesson 1]\nContent here...\n\n[Course B - Lesson 3]\n..."
```

### Step 7: Response Returns to Frontend

**Location:** `frontend/script.js:76-85`

```javascript
const data = await response.json();
// { answer: "...", sources: ["Course A - Lesson 1", ...], session_id: "abc123" }

currentSessionId = data.session_id;
addMessage(data.answer, 'assistant', data.sources);
// Renders markdown, shows collapsible sources
```

### Visual Flow Diagram

```
+-----------------------------------------------------------------------------+
|  FRONTEND (script.js)                                                       |
|  +---------------+                                                          |
|  | User types    |---> POST /api/query { query, session_id }                |
|  | question      |                                                          |
|  +---------------+                         |                                |
+--------------------------------------------|---------------------------------+
                                             v
+-----------------------------------------------------------------------------+
|  BACKEND                                                                    |
|                                                                             |
|  +---------------+    +---------------+    +---------------+                |
|  |   app.py      |--->| rag_system    |--->| ai_generator  |                |
|  |  (FastAPI)    |    |  .query()     |    |               |                |
|  +---------------+    +---------------+    +-------+-------+                |
|                                                    |                        |
|                                                    v                        |
|                                     +------------------------+              |
|                                     |  Claude API Call       |              |
|                                     |  (with tools)          |              |
|                                     +-----------+------------+              |
|                                                 |                           |
|                              +------------------+------------------+        |
|                              v                                     v        |
|                    +-------------------+              +-------------------+  |
|                    | Direct Answer     |              | Tool Use Request  |  |
|                    | (no search)       |              | search_course...  |  |
|                    +---------+---------+              +---------+---------+  |
|                              |                                  |           |
|                              |                                  v           |
|                              |                     +----------------------+  |
|                              |                     | CourseSearchTool     |  |
|                              |                     | .execute()           |  |
|                              |                     +-----------+----------+  |
|                              |                                 |            |
|                              |                                 v            |
|                              |                     +----------------------+  |
|                              |                     | VectorStore.search() |  |
|                              |                     | (ChromaDB)           |  |
|                              |                     +-----------+----------+  |
|                              |                                 |            |
|                              |                                 v            |
|                              |                     +----------------------+  |
|                              |                     | Results -> Claude    |  |
|                              |                     | -> Final Response    |  |
|                              |                     +-----------+----------+  |
|                              |                                 |            |
|                              +-----------------+---------------+            |
|                                                |                            |
|                                                v                            |
|                              { answer, sources, session_id }                |
+-----------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------+
|  FRONTEND                                                                   |
|  +---------------------------------------------+                            |
|  | Render markdown answer                      |                            |
|  | Display collapsible sources                 |                            |
|  | Update session ID                           |                            |
|  +---------------------------------------------+                            |
+-----------------------------------------------------------------------------+
```

---

## Key Features

1. **Semantic Search** - Uses embeddings to find relevant course content beyond keyword matching
2. **Tool-Based Generation** - Claude autonomously decides when to search using registered tools
3. **Session Management** - Maintains conversation context across queries
4. **Source Attribution** - Returns which course/lesson each response came from
5. **Intelligent Chunking** - Sentence-based with overlap prevents context loss
6. **Deduplication** - Prevents re-processing of already-indexed courses
7. **Responsive UI** - Works on desktop and mobile
8. **Markdown Support** - Rich formatting in AI responses
