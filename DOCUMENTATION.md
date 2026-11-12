# Ollama Desktop Chatbot: Technical Architecture & System Documentation

This document is the technical reference for the **Ollama Desktop Chatbot** architecture, execution pipelines, API surface, data schemas, configuration, agent harness, and deployment model.

---

## 1. System Overview & Design Philosophy

The application is a **local-first hybrid desktop application**:

- A lightweight **FastAPI** backend running on `127.0.0.1` (desktop mode) or inside a container.
- A responsive **vanilla JavaScript** frontend rendered through **PyWebView**, with automatic fallback to the default browser.
- An embedded **SQLite** database for projects, conversations, messages, and analytics.
- A **multi-provider LLM layer** unifying local Ollama with OpenAI, Anthropic, Google Gemini, Groq, and OpenRouter.
- An **autonomous agent harness** with tool calling, approval gates, background processes, document editing, and multimodal image analysis.
- A **project/workspace system** that scopes conversations and injects `AGENTS.md` instructions into agent context.

The current UI uses a **Frutiger Aero / Windows 7 Glass** visual language: sky-blue gradients, translucent glass panels, glossy controls, and vivid blue/green accents.

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                  Desktop Window (PyWebView or Browser)                     │
│  ┌──────────────────────┐  ┌───────────────────────────────────────────┐   │
│  │ Sidebar              │  │ Header                                    │   │
│  │ - Project selector   │  │ - Searchable model picker                 │   │
│  │ - Recent projects    │  │ - Token pill · Export · Review changes    │   │
│  │ - Chat title search  │  │ - Model library · Settings                │   │
│  │ - Session list       │  ├───────────────────────────────────────────┤   │
│  │ - Ollama status      │  │ Chat feed: messages, citations, tool cards│   │
│  └──────────────────────┘  │ Composer: attachments, toggles, send/stop │   │
│                            └───────────────────────────────────────────┘   │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │ HTTP / Server-Sent Events
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Local Server                             │
│                                                                            │
│  project_service     rag_service      file_service     analytics_service   │
│  - projects          - web search     - PDF/DOCX       - tokens/cost       │
│  - AGENTS.md         - prompt build   - XLSX/PPTX      - budget status     │
│  - file overview     - citations      - CSV/code                           │
│                                                                            │
│  vision_service                         agent harness                      │
│  - image preprocessing                  - orchestrator                     │
│  - OCR/vision routing                   - tool registry (26 tools)         │
│  - OpenCV geometry                      - permission broker                │
│                                         - background processes             │
│                                                                            │
│                         llm_service (unified engine)                       │
│              ┌──────────────────────────┴──────────────────────────┐       │
│              ▼                                                     ▼       │
│       Local Ollama API                                  Cloud provider APIs│
│    (http://localhost:11434)                   OpenAI · Anthropic · Gemini  │
│                                                Groq · OpenRouter           │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     ▼
                    SQLite (`data/chatbot.db`)
        projects · conversations · messages · analytics
```

---

## 2. Technology Stack & Decision Rationale

| Layer | Technology | Why This Choice |
| :--- | :--- | :--- |
| **Backend** | **FastAPI + Uvicorn** | Async request handling, Pydantic validation, and native `StreamingResponse` support for SSE. |
| **Desktop shell** | **PyWebView** | Native OS window without Node.js/Electron overhead; falls back to the browser when display libraries are unavailable. |
| **Database** | **SQLite3 (stdlib)** | Zero-setup embedded persistence with ACID transactions, ideal for local project/history data. |
| **Frontend** | **Vanilla JS + CSS3** | No bundler or Node toolchain required; the app runs directly from a Python environment. |
| **Visual style** | **Frutiger Aero / Windows 7 Glass** | Translucent sky-blue panels, glossy gradients, soft shadows, and glass blur. |
| **Markdown & code** | **Marked.js + Highlight.js** | Streaming Markdown rendering, code highlighting, and copy-to-clipboard, with a minimal offline fallback. |
| **Document parsing** | `pypdf`, `python-docx`, `openpyxl`, `python-pptx` | Text extraction from PDF, DOCX, XLSX, PPTX, CSV, and source files. |
| **Vision** | **Pillow + OpenCV headless** | EXIF/orientation, crop, resize, grayscale/contrast, contour detection, and shape geometry. |
| **Web search** | `ddgs` / `duckduckgo_search` | Keyless live search snippets and URLs for internet RAG. |
| **Agent tools** | Python stdlib + native libraries | `subprocess`, filesystem APIs, `python-docx`, hashing, base64, and process management. |
| **Deployment** | **Docker + Docker Compose** | Multi-stage image, non-root runtime, host-gateway bridge, and CPU/GPU Ollama profiles. |

---

## 3. End-to-End Execution Pipelines

### A. Chat Message & Streaming Pipeline

```text
[User presses Enter / clicks Send]
  │
  ├─► app.js::sendMessage()
  │     ├─ Validates text and attachment tray.
  │     ├─ Renders the user bubble and assistant placeholder.
  │     └─ POST /api/chat with conversation, project, provider, model,
  │        append_chat, web-search, and agent-mode fields.
  │
  ├─► server.py::chat_endpoint(req)
  │     ├─ Loads or creates the conversation (scoped to project_id if supplied).
  │     ├─ Optionally performs web search through rag_service.
  │     ├─ Persists the user message and emits a `user_message` SSE event
  │     │  containing the saved message ID.
  │     ├─ Auto-titles a new conversation from the first ~6 words.
  │     ├─ Builds history (when append_chat is enabled).
  │     ├─ Augments the current prompt with attachments and search citations.
  │     └─ Branches into normal streaming or Agent Mode.
  │
  ├─► Normal mode: llm_service.stream_chat()
  │     ├─ Ollama: POST /api/chat with stream=True.
  │     ├─ OpenAI/Groq/OpenRouter/Gemini: OpenAI-compatible SSE.
  │     ├─ Anthropic: native /v1/messages streaming.
  │     └─ Emits `chunk` events, then a `done` event with metrics.
  │
  ├─► Agent mode: agent_orchestrator.run_agent_stream()
  │     └─ Emits agent/thinking/tool/permission events; see section 3C.
  │
  └─► Persistence & UI finalization
        ├─ Saves the assistant reply and attaches its message ID to `done`.
        ├─ Records analytics (tokens, model, estimated cost).
        ├─ Computes budget status.
        ├─ Appends speed/token/step/cost metadata to the bubble.
        └─ Refreshes the sidebar title and conversation list.
```

**Message IDs:** Newly rendered user and assistant bubbles are stamped with their database IDs from SSE events, so the delete-pair action works immediately without reloading the conversation.

### B. File Attachment & Ingestion Pipeline

```text
[User clicks '+']
  │
  ├─► Hidden multi-file input accepts PDF, DOCX, XLSX, PPTX, CSV, TXT,
  │   and common source-code extensions.
  ├─► app.js::handleFileUpload() sends one POST /api/upload per file.
  │
  ├─► server.py::upload_file()
  │     ├─ Saves the binary under data/uploads/ (random suffix on collision).
  │     └─ Calls file_service.get_file_metadata().
  │
  ├─► file_service.extract_text()
  │     ├─ DOCX → python-docx paragraphs
  │     ├─ PDF  → pypdf page extraction
  │     ├─ XLSX → openpyxl rows
  │     ├─ PPTX → python-pptx shapes
  │     ├─ CSV  → csv reader
  │     └─ Text/code → UTF-8 reader
  │
  └─► Returns filename, path, extension, size, character count, and content.
        └─► Frontend renders attachment chips with remove buttons.
```

Documents are embedded into the prompt as structured text blocks; there is no vector database or embedding index. Content is truncated at the service's character limit.

### C. Agent Mode Execution & Permission Pipeline

```text
[Agent Mode enabled + message sent]
  │
  ├─► llm_service.check_agent_readiness(provider, model)
  │     ├─ Ollama: verifies the model is installed and advertises `tools`.
  │     └─ Cloud: verifies the provider API key is configured.
  │
  ├─► agent_orchestrator.run_agent_stream()
  │     ├─ Builds environment context (OS, workspace, project, AGENTS.md,
  │     │  attachments, conversation history).
  │     ├─ Sends the objective and 26 tool schemas to the model.
  │     ├─ Receives tool calls and executes them sequentially.
  │     ├─ Each call passes through the permission broker when required.
  │     ├─ Feeds tool results back and repeats until a final answer or cap.
  │     └─ Tracks modified files and task metrics in memory.
  │
  ├─► Permission flow (Always Ask)
  │     ├─ Server emits `permission_request`.
  │     ├─ UI shows action, target, risk level, and preview.
  │     ├─ User chooses allow, always_allow, or deny.
  │     ├─ POST /api/agent/permission/{request_id}
  │     └─ Server emits `permission_resolved` and continues/blocks.
  │
  └─► Finalization
        ├─ Saves only the final assistant answer to the messages table.
        ├─ Records analytics.
        └─ Emits `done` with status, iterations, modified files, and message ID.
```

Agent task steps and tool results are **not persisted** to SQLite; the final answer and analytics are persisted. Cancellation stops the loop and clears pending approvals but does not undo file changes or kill detached background processes.

### D. Projects, Workspaces & `AGENTS.md` Pipeline

```text
[User opens/creates a project]
  │
  ├─► POST /api/projects { path, name?, instructions? }
  │     ├─ Resolves the absolute path; creates the folder if missing.
  │     ├─ Registers or updates the project row.
  │     ├─ Reads an existing AGENTS.md, or writes a starter template.
  │     ├─ Sets the project active in memory.
  │     └─ Touches last_opened_at.
  │
  ├─► Conversation lists are filtered by project_id.
  ├─► GET /api/projects/{id} returns project details plus a scanned overview.
  └─► Agent tasks for the project receive project name, workspace path,
        and instructions from the first available file:
        AGENTS.md → agents.md → .agentrules → CLAUDE.md
```

The project overview scans up to depth 3 and 60 entries, skipping common dependency, build, VCS, IDE, hidden, and cache directories.

### E. Vision & Multimodal Pipeline

```text
[Agent calls analyze_image(path, mode, query)]
  │
  ├─► image_tools.resolve image path or extract first embedded image:
  │     ├─ PDF  → pypdf embedded images
  │     ├─ DOCX → word/media/*
  │     └─ PPTX → ppt/media/*
  │
  ├─► vision_service.preprocess_image()
  │     ├─ EXIF auto-orientation, optional crop/rotate/resize
  │     ├─ grayscale, contrast, brightness
  │     └─ PNG/JPEG encoding for the provider
  │
  ├─► vision_service.resolve_vision_model()
  │     └─ configured override → current provider → local vision model
  │        → cloud fallback based on configured API keys
  │
  └─► Provider-specific multimodal request
        ├─ Ollama /api/chat with images[]
        ├─ OpenAI-compatible image_url data URLs
        └─ Anthropic base64 image blocks
```

Specialized modes include `ocr`, `chart_graph`, `diagram`/`flowchart`, `table`, `general`, and OpenCV `geometry`.

### F. Message-Pair Deletion Pipeline

Messages are ordered by `created_at` with `rowid` as a tie-breaker. Deleting either side of a normal turn removes both rows:

- **User message selected** → delete it and the immediately following assistant reply.
- **Assistant message selected** → delete it and the immediately preceding user message.
- **Orphaned assistant reply** → delete only the reply.

The endpoint returns `deleted_ids`; the UI removes every matching row and restores the welcome screen when the conversation becomes empty.

---

## 4. API Reference

### System & Projects

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET | `/api/system/specs` | CPU count, total RAM, OS, and hardware metadata used for model recommendations. |
| GET | `/api/projects` | List registered projects with conversation counts. |
| POST | `/api/projects` | Open or create a project from a directory path. |
| GET | `/api/projects/active` | Return the active project (auto-selects the most recent if none is set). |
| POST | `/api/projects/close` | Clear the active project and return to global workspace. |
| GET | `/api/projects/{project_id}` | Project record, overview tree, and `AGENTS.md` contents. |
| PATCH | `/api/projects/{project_id}` | Update name/path/instructions; instructions are written to `AGENTS.md`. |
| DELETE | `/api/projects/{project_id}` | Unregister a project; conversations are detached, files remain on disk. |
| POST | `/api/projects/{project_id}/open` | Activate an existing project. |

### Models

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET | `/api/models` | Installed Ollama models plus the cloud catalog and recommendation annotations. |
| GET | `/api/models/recommended` | Curated local models with installed/compatibility status. |
| POST | `/api/models/pull` | Stream Ollama model download progress as SSE. |
| DELETE | `/api/models/pull?model=...` | Cancel an in-progress model download. |
| DELETE | `/api/models?model=...` | Delete an installed local Ollama model. |

### Conversations & Messages

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET | `/api/conversations?project_id=...` | List conversations; omit for global-only or use `all`. |
| POST | `/api/conversations` | Create a conversation (optionally project-scoped). |
| GET | `/api/conversations/{conv_id}` | Full transcript with decoded attachments and citations. |
| PATCH | `/api/conversations/{conv_id}` | Rename a conversation. |
| DELETE | `/api/conversations/{conv_id}` | Delete the conversation and its messages. |
| DELETE | `/api/conversations/{conv_id}/messages/{msg_id}` | Delete a user/assistant message pair. |
| POST | `/api/conversations/{conv_id}/export?format=...` | Export as DOCX file (`docx`) or Markdown JSON. The current UI requests the DOCX variant with `GET`, so only Markdown export works from the header until the method is aligned. |

### Chat, Upload & Agent

| Method | Path | Purpose |
| :--- | :--- | :--- |
| POST | `/api/upload` | Upload and parse one document. |
| POST | `/api/chat` | Main SSE chat endpoint; normal or Agent Mode. |
| POST | `/api/agent/cancel/{task_id}` | Cancel an active agent task. |
| POST | `/api/agent/permission/{request_id}` | Resolve an approval with `allow`, `deny`, or `always_allow`. |

### Settings & Analytics

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET | `/api/settings` | Full configuration plus masked API keys. |
| POST | `/api/settings` | Merge and persist settings; switching to `allow_all` approves pending prompts. |
| GET | `/api/analytics` | Token/cost summary, per-model breakdown, and budget status. |
| GET | `/` | Serve the application UI. |
| GET | `/static/*` | Serve frontend assets. |

### SSE Event Contract

**Normal chat**

| Event | Key fields |
| :--- | :--- |
| `user_message` | `conversation_id`, `message_id` |
| `search_results` | `results` |
| `chunk` | `content` |
| `done` | token counts, `duration_sec`, `tokens_per_sec`, `estimated_cost`, `message_id`, `budget_status` |
| `error` | `error` |

**Agent Mode**

| Event | Key fields |
| :--- | :--- |
| `user_message` | `conversation_id`, `message_id` |
| `agent_start` | `task_id`, `objective`, `project_id`, `project_name`, `workspace`, `max_iterations`, `permission_mode` |
| `agent_step` | `iteration`, `status`, `message` |
| `agent_thought` | `iteration`, `content` |
| `tool_call` | `iteration`, `call_id`, `tool_name`, `arguments` |
| `permission_request` | `request_id`, `task_id`, `call_id`, `tool_name`, `details`, `timeout_seconds` |
| `permission_resolved` | `request_id`, `task_id`, `call_id`, `decision` |
| `tool_result` | `iteration`, `call_id`, `tool_name`, `arguments`, `result`, `duration_sec` |
| `chunk` | `content` (final answer fallback) |
| `error` | `error` |
| `done` | `task_id`, `status`, `final_answer`, `error`, `iterations`, `modified_files`, token metrics, `message_id`, `budget_status` |

**Model download**

| Event | Key fields |
| :--- | :--- |
| `progress` | `model`, `status`, `completed`, `total`, `percent` |
| `done` | `model`, `status` |
| `error` | `model`, `error` |
| `cancelled` | `model` |

---

## 5. Module Reference

### `app/server.py`

FastAPI gateway containing all REST and SSE endpoints listed above. It handles conversation creation, project scoping, web-search augmentation, chat persistence, agent orchestration, model library operations, settings masking, and analytics responses.

### `app/services/llm_service.py`

Unified provider engine:

- `get_ollama_models()` — installed local models and metadata.
- `get_device_specs()` — CPU/RAM/OS information.
- `get_recommended_models()` — curated model catalog with compatibility annotations.
- `pull_ollama_model()` / `delete_ollama_model()` — model library operations.
- `get_all_available_models()` — local plus cloud catalog.
- `stream_chat()` — streaming chat for all providers.
- `chat_with_tools()` — non-streaming tool-calling requests for agent mode.
- `check_agent_readiness()` — validates model installation, tool capability, or cloud key.
- `resolve_vision_model()` / `analyze_image_with_model()` — multimodal routing.

### `app/services/rag_service.py`

- `clean_search_query()` — strips conversational prefixes, corrects common typos, trims punctuation.
- `search_web()` — DuckDuckGo snippets with a legacy fallback.
- `build_augmented_context()` — combines documents, citations, and the user prompt.

### `app/services/file_service.py`

- `extract_text()` — format-specific extraction for PDF, DOCX, XLSX/XLS, PPTX, CSV, and text/code.
- `get_file_metadata()` — size, character count, extension, and truncated content.

### `app/services/analytics_service.py`

- `estimate_tokens()` — heuristic approximation (~4 characters/token).
- `calculate_cost()` — per-model input/output pricing; local Ollama is free.
- `get_budget_status()` — remaining tokens, percentage used, approaching flag (≥80%), and exceeded flag.

### `app/services/project_service.py`

- `open_or_create_project()`, `update_project()`, `delete_project()`.
- `get_project_agents_instructions()` — checks `AGENTS.md`, `agents.md`, `.agentrules`, then `CLAUDE.md`.
- `get_project_overview()` — bounded file-tree and language statistics.
- Active-project tracking and default `AGENTS.md` template creation.

### `app/services/vision_service.py`

- `preprocess_image()` — EXIF orientation, rotation, crop, resize, grayscale, contrast, brightness.
- `detect_shapes_and_geometry()` — OpenCV contours and polygon approximation.
- `extract_images_from_pdf()`, DOCX/PPTX embedded-image extraction.
- Specialized multimodal prompts and provider routing.

### `app/database.py`

- Project CRUD and conversation project assignment.
- Conversation/message CRUD, message-pair deletion, and JSON field decoding.
- Analytics recording and aggregation.
- DOCX export.

### `app/agent/`

- `orchestrator.py` — ReAct loop, readiness checks, permission integration, change tracking.
- `tool_registry.py` — tool schemas, argument validation, and dispatch.
- `permissions.py` — approval broker, destructive-command filtering, workspace resolution.
- `task_state.py` — in-memory task status, steps, tool calls, errors, and modified files.
- `tools/terminal.py`, `tools/filesystem.py`, `tools/docx_tools.py`, `tools/image_tools.py` — tool implementations.

---

## 6. Configuration Reference

Settings are stored in `data/config.json`. Missing keys are merged from defaults on load, and API-key/custom-endpoint maps are deep-merged.

| Setting | Default | Purpose |
| :--- | :--- | :--- |
| `ollama_url` | `http://localhost:11434` | Local Ollama base URL. |
| `selected_provider` | `ollama` | Default provider for new chats. |
| `selected_model` | `llama3.2:1b` | Default model for new chats. |
| `web_search_enabled` | `false` | Persisted UI preference. |
| `token_budget_limit` | `100000` | Informational analytics budget. |
| `remember_context` | `true` | Fallback when `append_chat` is omitted. |
| `export_docx` | `false` | Legacy preference. |
| `keep_alive` | `30m` | Ollama model keep-alive duration. |
| `api_keys` | empty strings | OpenAI, Anthropic, Gemini, Groq, OpenRouter keys. |
| `custom_endpoints` | provider defaults | Base URLs for OpenAI-compatible providers. |
| `agent_mode` | `false` | Persisted UI toggle state. |
| `agent_workspace` | repository root | Workspace when no project is active. |
| `agent_timeout_seconds` | `300` | Stored agent command timeout preference (capped at 5 minutes). |
| `agent_permission_mode` | `allow_all` | `allow_all` or `always_ask`. |
| `agent_permission_timeout_seconds` | `300` | Approval wait timeout. |
| `vision_provider` | `auto` | Vision override provider. |
| `vision_model` | empty | Vision override model. |

`web_search_results_count` is written by the settings UI and sent with chat requests (range 5–20). Model selection is persisted as `selected_provider` + `selected_model`.

---

## 7. Database Schema

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    instructions TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    project_id TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,               -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    attachments TEXT,                 -- JSON array
    search_results TEXT,              -- JSON array
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

Notable behavior:

- A safe startup migration adds `conversations.project_id` if an older database lacks it.
- `projects.path` is unique, so re-opening the same folder updates the existing project.
- Deleting a project sets associated `conversations.project_id` to `NULL` and leaves files on disk.
- Deleting a conversation removes its messages but not historical analytics rows.
- Attachments and search citations are stored as JSON text and decoded on load.
- `add_message()` updates the conversation's `updated_at` timestamp.
- Message ordering uses `created_at` with `rowid` as a tie-breaker for pair deletion.

---

## 8. Agent Harness Architecture

### A. Orchestrator (`app/agent/orchestrator.py`)

1. **Goal reception** — builds environment context, project instructions, attachments, and history.
2. **Readiness check** — verifies Ollama tool support or cloud API-key configuration.
3. **Model-driven ReAct loop** — reason, call tools, observe results, repeat.
4. **Sequential tool execution** — multiple tool calls per model response are supported.
5. **Permission integration** — state-changing calls may pause for approval.
6. **Finalization** — produces a final answer, modified-file list, iteration count, and metrics.
7. **Cancellation** — flags the task and cancels pending approvals at the next loop boundary.

The loop is **uncapped by default**. A caller may pass a positive `max_iterations` programmatically; `/api/chat` does not impose one.

### B. Tool Registry (`app/agent/tool_registry.py`)

The agent exposes **26 tools**:

| Category | Tools |
| :--- | :--- |
| **Terminal & processes** | `run_terminal`, `run_script`, `start_background_process`, `get_background_process_output`, `kill_background_process`, `list_background_processes` |
| **Filesystem inspection** | `list_files`, `tree`, `read_file`, `stat_file`, `search_files`, `file_hash`, `read_binary_file` |
| **Filesystem modification** | `write_file`, `append_file`, `edit_file`, `insert_lines`, `apply_patch`, `create_directory`, `create_symlink`, `move_file`, `copy_file`, `delete_file`, `write_binary_file` |
| **Documents & vision** | `manage_docx`, `analyze_image` |

Tool execution features include:

- JSON-string argument parsing and signature filtering.
- Required-parameter validation with structured errors.
- Shell command execution with cwd, timeout, stdin, env vars, and output capture.
- Script execution for Python, Bash, Node, Ruby, Perl, and PHP.
- Background process tracking with buffered output and process-group termination.
- Unified-diff patching, line insertion, file search with context, hashing, and base64 binary I/O.
- DOCX read/create/paragraph/replacement/table operations.
- Image analysis with OCR, chart, diagram, table, general, and geometry modes.

### C. Permission Broker (`app/agent/permissions.py`)

- **Modes:** `allow_all` and `always_ask`.
- **Read-only tools** run without prompting in Always Ask mode: listing, tree, read, stat, search, hash, binary read, image analysis, and background-output inspection.
- **State-changing tools** require approval: terminal/script/process tools, writes, edits, patches, moves, copies, deletes, symlinks, binary writes, and DOCX modifications.
- **Decisions:** `allow` (once), `always_allow` (same tool for the current task), and `deny`.
- **Lifecycle:** unanswered prompts time out after 300 seconds by default; cancellation denies pending prompts; per-task allowlists are discarded when the task ends.
- **Runtime switching:** selecting `allow_all` in Settings automatically approves pending prompts.

### D. Safety & Trust Model

- Catastrophic command patterns (root recursive deletion, disk formatting, fork bombs, destructive `dd`, shutdown patterns) are filtered.
- File and terminal tools are intended for **trusted local use**. The permission layer is an approval gate, not a complete filesystem sandbox; some tools can resolve absolute paths or `..` traversal.
- A dedicated project folder is recommended for agent work.
- Agent Mode inherits the host user's permissions for shell commands.
- Cancellation does not revert file modifications or terminate background processes that were intentionally detached.

---

## 9. UI Architecture

- **Theme:** Frutiger Aero / Windows 7 Glass; sky-blue gradients, translucent panels, glossy controls.
- **Sidebar:** project selector, recent projects, new chat, title search, conversation list, Ollama status.
- **Header:** searchable model picker, session token pill, export, review-changes badge, model library, settings.
- **Chat feed:** streaming Markdown, citations, attachment chips, token/speed metadata, copy buttons, message-pair delete controls.
- **Composer:** auto-growing textarea, attachment tray, Append Chat, Web Search, Agent Mode, Send/Stop.
- **Modals:** Settings & Providers, Local Model Library, Token Analytics, Open/Create Project, Review Agent Changes, Delete Message Pair, Permission Required.
- **Agent UI:** step indicator, reasoning blocks, expandable tool cards with arguments/results, permission status, error/cancellation blocks.
- **Keyboard:** `Enter` sends, `Shift+Enter` adds a newline; the model picker and model search support arrow keys, Enter, and Escape.
- **Session state:** changes tracking, token pill, toggles, and queued permission prompts are in-memory and reset on reload.

The interface is desktop-oriented and does not define responsive breakpoints or a dark/light theme switch.

---

## 10. Docker & Containerization

The image uses a two-stage build:

1. **Builder:** `python:3.11-slim` with build dependencies and Python packages installed into `/install`.
2. **Runtime:** `python:3.11-slim` plus shell, network, archive, build, Python, Node.js, and developer utilities the agent may invoke. The app runs as non-root `appuser` (UID 1000).

```text
┌──────────────────────────────────────────────────────────────┐
│ Host machine                                                 │
│  Ollama at http://127.0.0.1:11434 (optional)                 │
│  Agent workspace folder mounted into /workspace              │
└───────────────────────────▲──────────────────────────────────┘
                            │ host.docker.internal:host-gateway
┌───────────────────────────┴──────────────────────────────────┐
│ Container: ollama_chatbot                                    │
│  - FastAPI app                                               │
│  - /app/data volume: SQLite, config, uploads                 │
│  - /workspace volume: agent project files                    │
│  - Exposed port 8080                                         │
└──────────────────────────────────────────────────────────────┘
```

Compose profiles:

| Profile | Services | Use case |
| :--- | :--- | :--- |
| default | `chatbot` | Connect to Ollama on the host. |
| `with-ollama` | `chatbot` + `ollama` | Bundled CPU Ollama. |
| `gpu` | `chatbot` + `ollama-gpu` | Bundled Ollama with NVIDIA GPU passthrough. |

`.env.example` documents deployment variables such as `PORT`, `OLLAMA_URL`, `AGENT_WORKSPACE_HOST`, `AGENT_PERMISSION_MODE`, `AGENT_TIMEOUT_SECONDS`, and bundled-Ollama tuning. Application settings, including provider API keys, are managed through the in-app Settings dialog and persisted in the `data` volume.

For container or reverse-proxy deployments, ensure Uvicorn binds to an externally reachable interface; the desktop launcher defaults to `127.0.0.1` for local safety.

---

## 11. Testing

```bash
python -m unittest discover -s tests -v
```

Test modules:

- `tests/test_app.py` — database lifecycle, model discovery, API endpoints, analytics, RAG, append-chat behavior, and message-pair deletion.
- `tests/test_projects.py` — project registration, `AGENTS.md`, overview, and conversation scoping.
- `tests/test_agent.py` — agent readiness, tool registry, and tool behavior.
- `tests/test_acceptance.py` — terminal execution, code repair, Markdown/DOCX workflows, OCR/text extraction, and image analysis scenarios.

---

## 12. Security & Operational Notes

- The app is designed for **local/desktop use**. It has no authentication and allows CORS from any origin.
- API keys are stored in plaintext in `data/config.json`; protect that file and avoid exposing the server to untrusted networks.
- Agent Mode can execute shell commands and modify files with the host user's permissions. Use a dedicated workspace and review approvals carefully.
- Project removal only unregisters the project; it never deletes files from disk.
- Conversation deletion removes messages but leaves analytics history intact.
- Agent task steps, tool logs, and change tracking are not persisted across restarts.
- Long conversations are sent in full when Append Chat is enabled; there is no automatic summarization or context trimming.
