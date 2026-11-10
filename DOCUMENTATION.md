# 📘 Ollama Desktop Chatbot: Technical Architecture & System Documentation

This document provides a comprehensive technical reference for the **Ollama Desktop Chatbot** architecture, execution pipelines, function call paths, data schemas, and the rationale behind each component in the technology stack.

---

## 1. System Overview & Design Philosophy

The application is structured as a **hybrid desktop application**:
- A lightweight, high-performance **FastAPI asynchronous backend** running locally on `127.0.0.1:8080` (or dynamically allocated port).
- A reactive, Antigravity/Cursor-inspired **desktop frontend** rendered natively via `pywebview` (with seamless fallback to dedicated browser application mode).
- An embedded **SQLite relational engine** guaranteeing zero external database dependencies and instant transactional persistence.
- A **multi-provider LLM orchestrator** unifying local Ollama instances with cloud APIs (OpenAI, Anthropic, Gemini, Groq, OpenRouter) through a single streaming protocol.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Desktop Window (PyWebView)                      │
│   ┌───────────────────────┐ ┌───────────────────────────────────────┐  │
│   │   Sidebar (History)   │ │  Main View: Header, Messages, Input   │  │
│   │   - Active Sessions   │ │  - Model Dropdown  - Export Action    │  │
│   │   - Search / Delete   │ │  - [+] Attachments - Web Search Toggle│  │
│   └───────────────────────┘ └───────────────────────────────────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / Server-Sent Events (SSE)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Local Server                           │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────────┐ │
│  │   rag_service   │  │   file_service   │  │   analytics_service    │ │
│  │  - Query Clean  │  │  - PDF/DOCX/XLSX │  │  - Hardware Tok/s      │ │
│  │  - DDGS Search  │  │  - PPTX/CSV/Code │  │  - Cost & Budget Limit │ │
│  └────────┬────────┘  └────────┬─────────┘  └───────────┬────────────┘ │
│           │                    │                        │              │
│           └────────────────────┼────────────────────────┘              │
│                                ▼                                       │
│                       llm_service (Engine)                             │
│                  ┌─────────────┴─────────────┐                         │
│                  ▼                           ▼                         │
│         Local Ollama API            Online Cloud APIs                  │
│       (http://127.0.0.1:11434)   (OpenAI, Claude, Gemini, Groq)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
                     Embedded SQLite (`data/chatbot.db`)
```

---

## 2. Technology Stack & Decision Rationale

| Layer | Technology | Why This Specific Choice Was Made |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI + Uvicorn** | FastAPI provides native asynchronous request processing, automatic JSON validation via Pydantic v2, and first-class support for `StreamingResponse` (Server-Sent Events). It is significantly faster and more modern than Flask, and much lighter than Django. |
| **Desktop Shell** | **PyWebView** | Allows creating a native operating-system window with custom dimensions, title, and dark window decorations without requiring Node.js, Electron (which adds ~150MB+ of binary overhead), or complex C++ bindings. If desktop GUI dependencies are absent (e.g., Docker/headless Linux), it cleanly falls back to `webbrowser.open()`. |
| **Database** | **SQLite3 (Python Standard Library)** | Embedded relational database with zero setup, zero network overhead, ACID transactions, and zero risk of corruption. Ideal for local desktop history, message indexing, and analytics logging. |
| **Frontend Framework** | **Modern Vanilla JS + CSS3** | Avoids heavy Node/npm toolchains, bundlers, and compilation steps. The entire app starts immediately from a clean Python installation. Styling adopts CSS variables for pixel-perfect dark blue and black fidelity (`#070a12`, `#172554`, `#1e3a8a`, `#2563eb`). |
| **Markdown & Code** | **Marked.js & Highlight.js** | Industry-standard parsing for tables, blockquotes, lists, and syntax-highlighted code blocks with built-in copy-to-clipboard functionality. Includes built-in offline regex fallback if external CDN assets are unreachable. |
| **Document Processing** | `pypdf`, `python-docx`, `openpyxl`, `python-pptx` | Native Python libraries capable of deep textual extraction across PDFs, Word documents, Excel workbooks, PowerPoint decks, CSV files, and source code files. |
| **Web Search RAG** | `ddgs` (DuckDuckGo Search) | Free, instantaneous web search requiring **no API keys, no subscription, and no user registration**. Yields live snippets and URLs directly into the context window. |
| **Deployment** | **Docker + Docker Compose** | Multi-platform containerization using `python:3.11-slim`, volume mounts for persistent data, and host-gateway bridges to communicate with host-native Ollama engines or bundled containerized Ollama. |

---

## 3. End-to-End Execution Pipelines & Function Paths

### A. Chat Message & Streaming Generation Pipeline

When a user submits a prompt, the system executes the following chronological call path:

```
[User presses Enter / clicks Send]
  │
  ├─► `app.js::sendMessage()`
  │     ├─ Validates input string and `attachedFiles` tray.
  │     ├─ Appends User Message bubble in DOM.
  │     ├─ Appends Assistant Placeholder bubble with animated cursor.
  │     └─ Dispatches `fetch('/api/chat', { method: 'POST', body: JSON })`.
  │
  ├─► `server.py::chat_endpoint(req: ChatRequest)`
  │     ├─ 1. Retrieves active conversation via `db.get_conversation(conv_id)`.
  │     ├─ 2. Web Search Step (if `req.use_web_search == True`):
  │     │      ├─ Calls `rag_service.clean_search_query(req.message)`
  │     │      │    └─ Strips conversational phrases ("Tell me...", "What is..."), fixes typos.
  │     │      └─ Calls `rag_service.search_web(cleaned_query)`
  │     │           └─ Queries `ddgs.text()`, formats title, URL, and snippet body.
  │     ├─ 3. Records user message in DB:
  │     │      └─ `db.add_message(conv_id, 'user', content, attachments, search_results)`
  │     ├─ 4. Auto-Titling:
  │     │      └─ If title == "New Chat", calls `db.update_conversation_title(conv_id, first_words)`.
  │     ├─ 5. Memory / Context Construction:
  │     │      ├─ Injects authoritative System Instruction (prevents model refusals).
  │     │      ├─ If `req.append_chat == True`: appends prior turns from `conv["messages"]`.
  │     │      └─ Calls `rag_service.build_augmented_context(message, attachments, search_results)`
  │     │           └─ Injects document blocks, web citations, and user prompt.
  │     │
  │     └─ 6. Initiates `StreamingResponse(event_generator(), media_type="text/event-stream")`:
  │            ├─ Emits `{"type": "search_results", "results": [...]}` if web search was performed.
  │            └─ Calls `llm_service.stream_chat(history_messages, provider, model)`
  │
  ├─► `llm_service.py::stream_chat()`
  │     ├─ **Branch: Ollama (Local)**:
  │     │    ├─ Posts payload to `http://localhost:11434/api/chat` with `stream=True`.
  │     │    ├─ Yields `{"type": "chunk", "content": chunk_text}`.
  │     │    └─ On `done=True`, extracts `prompt_eval_count`, `eval_count`, `eval_duration`.
  │     ├─ **Branch: Online (OpenAI / Groq / OpenRouter / Gemini)**:
  │     │    ├─ Sends request with Bearer API key to provider endpoint.
  │     │    ├─ Iterates over SSE `data: {"choices": [{"delta": {"content": "..."}}]}` lines.
  │     │    └─ Computes estimated completion tokens via `analytics_service.estimate_tokens()`.
  │     └─ Computes final metrics:
  │          ├─ `duration_sec = time.time() - start_time`
  │          ├─ `tokens_per_sec = round(completion_tokens / duration_sec, 1)`
  │          ├─ `cost = analytics_service.calculate_cost(provider, model, prompt_tok, comp_tok)`
  │          └─ Yields `{"type": "done", "prompt_tokens": ..., "completion_tokens": ..., "tokens_per_sec": ..., "estimated_cost": ...}`
  │
  ├─► `server.py` Finalization:
  │     ├─ Saves assistant response: `db.add_message(conv_id, 'assistant', full_text, ...)`
  │     ├─ Logs analytics: `db.record_analytics(conv_id, provider, model, prompt_tok, comp_tok, cost)`
  │     └─ Computes budget status: `analytics_service.get_budget_status(grand_total, limit)`
  │
  └─► `app.js` SSE Stream Reader:
        ├─ Receives SSE chunks, updates inner HTML via `renderMarkdown(accumulatedText)`.
        ├─ Highlights syntax on code blocks via `highlightCodeBlocks()`.
        ├─ On `type: "done"`, updates token pill, attaches speed badge (`⚡ 1.2s (45.1 tok/s)`), and refreshes history title.
```

---

### B. File Attachment & Ingestion Pipeline

```
[User clicks '+' button]
  │
  ├─► `app.js::btnPlusAttach.click()` -> triggers hidden `<input type="file" multiple>`
  ├─► User selects 1 or more files (.pdf, .docx, .xlsx, .pptx, .csv, .txt, .py, etc.)
  │
  ├─► `app.js::handleFileUpload()`
  │     └─ Creates `FormData` and sends `POST /api/upload`
  │
  ├─► `server.py::upload_file(file: UploadFile)`
  │     ├─ Saves binary to `data/uploads/{filename}` (with collision hashing).
  │     └─ Invokes `file_service.get_file_metadata(dest_path)`
  │
  ├─► `file_service.py::extract_text(file_path)`
  │     ├─ `.docx` -> `docx.Document(file).paragraphs`
  │     ├─ `.pdf`  -> `pypdf.PdfReader(file).pages[i].extract_text()`
  │     ├─ `.xlsx` -> `openpyxl.load_workbook(file).active.iter_rows()`
  │     ├─ `.pptx` -> `pptx.Presentation(file).slides[i].shapes`
  │     ├─ `.csv`  -> `csv.reader(file)`
  │     └─ Code/text (`.py`, `.cpp`, `.js`, `.json`, `.txt`) -> UTF-8 stream reader
  │
  └─► Returns JSON metadata:
        `{ filename, filepath, extension, size_str, char_count, content }`
        └─► Frontend displays attachment chip preview with icon, size, and [✕] remove button.
```

---

## 4. Module & Function Reference

### `app/server.py`
The REST and SSE API gateway:
- `get_models()`: Discovers installed Ollama models and lists supported cloud providers.
- `list_conversations()`: Fetches all saved chat sessions ordered by last updated.
- `create_conversation(req)`: Initializes a new conversation session.
- `get_conversation(conv_id)`: Loads complete transcript, message history, and attached metadata.
- `update_conversation(conv_id, req)`: Renames conversation title.
- `delete_conversation(conv_id)`: Cascades deletion of conversation and associated messages.
- `export_conversation(conv_id, format)`: Compiles conversation into formatted Word document (`.docx`) or Markdown (`.md`).
- `upload_file(file)`: Ingests user files and parses textual representations.
- `chat_endpoint(req)`: Orchestrates context augmentation, web search, SSE streaming, and persistent storage.
- `get_settings()` / `update_settings(req)`: Reads and updates persistent configuration and masked API keys.
- `get_analytics()`: Computes total tokens, costs, model distribution, and budget progress.

### `app/services/llm_service.py`
The unified AI streaming engine:
- `get_ollama_models()`: Queries `GET http://localhost:11434/api/tags` and extracts installed model IDs, sizes, and metadata.
- `get_all_available_models()`: Combines local Ollama status with configured cloud providers.
- `stream_chat(messages, provider, model, keep_alive)`: Yields SSE tokens and hardware performance metrics across local Ollama and cloud APIs.

### `app/services/rag_service.py`
The search and context synthesis engine:
- `clean_search_query(query)`: Removes conversational phrasing (`"Tell me about"`, `"What is"`), corrects typos (e.g., `"lastest"` $\rightarrow$ `"latest"`), and trims punctuation to optimize search hit rates.
- `search_web(query, max_results)`: Uses `ddgs.text()` to pull current web search results, URLs, and snippet bodies.
- `build_augmented_context(user_message, attachments, search_results)`: Structures system context, attached document contents, and web search citations into a Markdown prompt block.

### `app/services/file_service.py`
Multi-format document parsing:
- `extract_text(file_path)`: Detects extension and executes format-specific parsing (`docx`, `pdf`, `pptx`, `xlsx`, `csv`, plain text, and source code).
- `get_file_metadata(file_path, max_chars)`: Computes file size strings, character counts, and handles intelligent truncation boundaries.

### `app/services/analytics_service.py`
Hardware telemetry and budget control:
- `estimate_tokens(text)`: Heuristic token approximation (~4 characters per token).
- `calculate_cost(provider, model, prompt_tokens, completion_tokens)`: Computes dollar cost based on model pricing tiers (\$0.00 for local Ollama).
- `get_budget_status(total_tokens_used, budget_limit)`: Returns remaining tokens, percentage used, and trigger thresholds (warning at $\ge 75\%$, danger at $\ge 90\%$).

### `app/database.py`
The embedded SQLite persistence layer:
- `_init_db()`: Initializes schema tables (`conversations`, `messages`, `analytics`).
- `create_conversation()`, `list_conversations()`, `get_conversation()`: Conversation CRUD.
- `add_message()`: Stores individual turns with attachments, search results, token counts, and latency.
- `record_analytics()`: Logs transactional analytics data points.
- `get_analytics_summary()`: Aggregates grand total tokens, costs, and breakdown by model.
- `export_docx()`: Generates stylized Word document matching the original script's output style.

---

## 5. Database Schema Architecture

```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,               -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    attachments TEXT,                 -- JSON array of file metadata
    search_results TEXT,              -- JSON array of web citations
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    duration_sec REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE TABLE analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    estimated_cost REAL DEFAULT 0.0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. Docker & Containerization Architecture

The containerized setup (`Dockerfile` & `docker-compose.yml`) handles local host bridging:

```
┌────────────────────────────────────────────────────────┐
│                      Host Machine                      │
│  Native Ollama Server running on http://127.0.0.1:11434│
└───────────────────────────▲────────────────────────────┘
                            │ host.docker.internal:host-gateway
┌───────────────────────────┴────────────────────────────┐
│                  Docker Container (chatbot)            │
│  - Python 3.11-slim Base Image                         │
│  - FastAPI Server listening on 0.0.0.0:8080            │
│  - Volumes:                                            │
│      ./data -> /app/data                               │
│      ./OutWrite Documents -> /app/OutWrite Documents   │
└────────────────────────────────────────────────────────┘
```
1. **Host Bridge**: `extra_hosts: "host.docker.internal:host-gateway"` allows the container to communicate directly with an Ollama instance installed on the host operating system without re-downloading model weights.
2. **Bundled Profile**: An optional `ollama` service container is provided under the `--profile with-ollama` flag for environments where Ollama is not installed natively on the host.
