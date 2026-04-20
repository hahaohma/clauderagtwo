# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (uses uv)
uv sync

# Start the backend server
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

No test or lint commands exist — this is a starter codebase.

## Architecture

This is a full-stack RAG chatbot that answers questions about course materials. The backend is Python/FastAPI, the frontend is vanilla HTML/CSS/JS, and ChromaDB provides vector storage.

### Data Flow

```
/docs/*.txt|pdf|docx
    → DocumentProcessor   (parse + chunk text, extract lesson metadata)
    → VectorStore         (store in ChromaDB: course_catalog + course_content collections)

User query (POST /api/query)
    → RAGSystem.query()
    → AIGenerator         (Claude with search_course_content tool)
    → CourseSearchTool    (hits VectorStore for relevant chunks)
    → Claude assembles final answer
    → SessionManager      (persists conversation history per session)
```

### Key Files

| File | Role |
|------|------|
| `backend/rag_system.py` | Main orchestrator; entry point for `add_course_document()`, `add_course_folder()`, `query()` |
| `backend/ai_generator.py` | Wraps Claude API; drives the tool-calling loop |
| `backend/vector_store.py` | ChromaDB wrapper; manages `course_catalog` and `course_content` collections |
| `backend/document_processor.py` | Parses course docs; chunks text at 800 chars with 100-char overlap |
| `backend/search_tools.py` | `CourseSearchTool` + `ToolManager`; Claude calls `search_course_content` to retrieve chunks |
| `backend/session_manager.py` | In-memory session history (default 2-message context window) |
| `backend/app.py` | FastAPI app; `POST /api/query` and `GET /api/courses` |
| `backend/config.py` | All tunable parameters (loaded from `.env`) |

### ChromaDB: Two Collections

- **`course_catalog`** — Course-level metadata; used for smart course-name matching when Claude passes `course_name` to the search tool.
- **`course_content`** — Actual chunked text with lesson metadata; used for semantic content retrieval.

### Tool-Calling Design

Claude does not receive course content directly in its system prompt. Instead it uses the `search_course_content` tool:
- `query` (required) — semantic search string
- `course_name` (optional) — resolved via vector similarity against `course_catalog`
- `lesson_number` (optional) — filters to a specific lesson

The `AIGenerator` runs a multi-turn loop: execute tools until Claude stops calling them, then return the final text response.

## Configuration

Create `backend/.env`:
```
ANTHROPIC_API_KEY=your-key-here
```

Key defaults in `config.py`:
- Model: `claude-sonnet-4-20250514`
- Embedding model: `all-MiniLM-L6-v2` (SentenceTransformers)
- ChromaDB path: `./chroma_db/` (git-ignored)
- Chunk size: 800 chars / overlap: 100 chars
- Max search results: 5
- Max conversation history: 2 messages

## Course Document Format

Files in `/docs/` must follow this structure for `DocumentProcessor` to parse them correctly:

```
Course Title: [Title]
Course Link: [URL]
Course Instructor: [Name]

Lesson 1: [Title]
Lesson Link: [URL]
[Content...]

Lesson 2: [Title]
[Content...]
```

Documents in `/docs/` are loaded automatically on startup.
