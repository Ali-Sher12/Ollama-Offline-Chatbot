# Ollama Desktop Chatbot

A local-first desktop AI workspace with a **Frutiger Aero / Windows 7 Glass** interface. Chat with local Ollama models or cloud providers, organize work into projects, attach documents, search the web, and hand multi-step coding, file, document, and vision tasks to an autonomous tool-using agent.

---

## Highlights

- **Frutiger Aero Glass GUI**: Sky-blue gradients, translucent glass panels, glossy buttons, smooth streaming Markdown, and syntax-highlighted code blocks with one-click copy.
- **Projects & Workspaces**: Register any folder as a project, keep its chats separate, browse a generated project file tree, and edit `AGENTS.md` instructions that are automatically injected into agent context.
- **Modern Chat Management**: Title search, auto-titling, conversation delete, per-message-pair deletion, Markdown export, and DOCX export support (the current DOCX button has an HTTP-method mismatch; Markdown export works).
- **Searchable Model Picker**: Quickly filter installed Ollama models and configured cloud models by name, provider, or tag.
- **Local & Online LLMs**:
  - **Local Ollama**: Auto-detects installed models (`llama3.2`, `qwen2.5`, `deepseek-r1`, etc.).
  - **In-App Model Library**: Search curated recommendations, download any Ollama model with live progress and cancellation, and delete installed models without leaving the app.
  - **Online Providers**: OpenAI, Anthropic, Google Gemini, Groq, and OpenRouter.
- **Autonomous Agent Mode**: An uncapped ReAct-style loop with **26 tools** covering terminal commands, script execution, background processes, filesystem operations, patching, search, hashing, binary files, Word documents, and image analysis.
- **Agent Permission Modes**: Choose **Allow All** for uninterrupted execution or **Always Ask** to approve terminal commands and state-changing file operations. Approvals support **Allow Once**, **Always Allow (this task)**, and **Deny**.
- **Review Agent Changes**: A session panel tracks files the agent created, modified, or deleted, with action badges and tool details.
- **Vision & Multimodal Analysis**: OCR, chart/graph reading, diagram and table extraction, scene description, and OpenCV shape detection for images and images embedded in PDFs, DOCX, and PPTX files.
- **Internet & Document RAG**:
  - **Live Web Search**: Retrieve DuckDuckGo snippets and clickable citations in real time.
  - **Offline Document Context**: Supplied files are parsed and injected directly into the prompt, so local models can work fully offline.
- **Analytics & Budget Tracking**: Session token counter, prompt/completion token breakdown, generation speed, duration, estimated cloud cost, and a configurable token-budget meter.
- **Native Desktop & Headless Modes**: Launch a PyWebView desktop window, fall back to a browser, or run as a local headless server.
- **One-Click Install & Run**: Cross-platform scripts for Linux, macOS, and Windows.
- **Docker Deployment**: Host-Ollama, bundled CPU Ollama, and bundled NVIDIA GPU profiles.

---

## Quick Start

### 1. Install

**Linux / macOS**
```bash
./install.sh
```

**Windows**
```bat
install.bat
```

The installer creates a Python virtual environment, installs dependencies, and checks the local Ollama connection.

Manual alternative:
```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Launch

```bash
./run.sh          # Linux / macOS
run.bat           # Windows
python main.py    # Any platform
```

The app starts the local FastAPI server, chooses the first available port from `8080`, and opens a native desktop window. If PyWebView is unavailable, it falls back to your default browser.

Headless/server mode:
```bash
python main.py --headless
```

---

## Projects & Workspaces

Open the workspace selector at the top of the sidebar:

- **Global Workspace** keeps chats that are not tied to a project.
- **Open / Create Project...** registers an existing folder or creates a new one.
- **Project Overview & AGENTS.md** edits project details, shows a file-tree snapshot, and opens the project instruction file.
- **Recent Projects** lets you switch quickly or unregister a project without deleting files from disk.

When a project is active, new conversations belong to it and Agent Mode uses that folder as its workspace. Project instructions are read from `AGENTS.md` (with fallbacks to `agents.md`, `.agentrules`, and `CLAUDE.md`) and passed to the agent automatically.

---

## Configuration & Settings

Open **Settings** in the top-right header to configure:

- **Local Ollama URL** and optional cloud API keys.
- **Vision Provider / Model** override (auto-detection by default).
- **Keep Local Model Loaded** duration (`5m`, `10m`, `30m`, `45m`, `60m`, or no limit).
- **Agent Workspace Directory** used when no project is active.
- **Agent Permissions** (`Allow All` or `Always Ask`).
- **Token Budget Limit** for analytics.
- **Web Search Results Count** (`5–20`).

Settings are stored locally in `data/config.json`. API keys are never sent anywhere except the provider you select.

---

## Tests

```bash
python -m unittest discover -s tests -v
```

The test suite covers database lifecycle, project management, API endpoints, agent readiness/tool behavior, acceptance scenarios, analytics, RAG, and message-pair deletion.

---

## Docker Deployment

Copy the environment template first:
```bash
cp .env.example .env
```

### Connect to Ollama on the host
```bash
docker compose up -d
```
The container reaches host Ollama through `host.docker.internal:host-gateway`. Access the app at `http://localhost:8080`.

### Bundle Ollama in the stack (CPU)
```bash
docker compose --profile with-ollama up -d
```

### Bundle Ollama with NVIDIA GPU passthrough
```bash
docker compose --profile gpu up -d
```
Requires the NVIDIA Container Toolkit on the host.

### Docker CLI
```bash
docker build -t ollama-desktop-chatbot .
docker run -p 8080:8080 -v "$(pwd)/data:/app/data" ollama-desktop-chatbot
```

Persistent volumes keep the SQLite database and settings, Ollama model weights, and the mounted agent workspace across restarts. Configure provider API keys in the app after launch so they persist in the `data` volume.

---

## Project Structure

```text
OllamaChatbot/
├── app/
│   ├── config.py                 # Settings and API key manager
│   ├── database.py               # SQLite projects, chats, messages, analytics
│   ├── server.py                 # FastAPI REST + SSE gateway
│   ├── agent/
│   │   ├── orchestrator.py       # ReAct-style agent loop
│   │   ├── permissions.py        # Approval broker, safety checks, workspace rules
│   │   ├── task_state.py         # In-memory task tracking
│   │   ├── tool_registry.py      # 26 tool schemas and dispatch
│   │   └── tools/
│   │       ├── terminal.py       # Shell, scripts, background processes
│   │       ├── filesystem.py     # File, patch, search, hash, binary tools
│   │       ├── docx_tools.py     # Word document operations
│   │       └── image_tools.py    # Vision and embedded-image analysis
│   ├── services/
│   │   ├── llm_service.py        # Ollama + cloud streaming and tool calling
│   │   ├── rag_service.py        # Web search and prompt augmentation
│   │   ├── file_service.py       # PDF, DOCX, XLSX, PPTX, CSV, text parsing
│   │   ├── analytics_service.py  # Tokens, speed, cost, budget
│   │   ├── project_service.py    # Projects, AGENTS.md, project overview
│   │   └── vision_service.py     # Image preprocessing, OCR routing, OpenCV
│   └── static/
│       ├── index.html            # Desktop UI
│       ├── css/app.css           # Frutiger Aero glass theme
│       └── js/app.js             # Streaming, projects, modals, agent UI
├── data/                         # Database, uploads, config
├── workspace/                    # Default Docker agent workspace
├── OutWrite Documents/           # Exported DOCX transcripts
├── tests/                        # Unit, integration, agent, acceptance tests
├── main.py                       # Desktop launcher
├── install.sh / install.bat      # Installers
├── run.sh / run.bat              # Launchers
├── .env.example                  # Docker Compose environment template
├── Dockerfile                    # Multi-stage container build
├── docker-compose.yml            # Host, bundled-CPU, and GPU profiles
├── requirements.txt
├── README.md
├── USER_GUIDE.md                 # End-user manual
└── DOCUMENTATION.md              # Technical architecture reference
```

---

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** — installation, projects, models, agent mode, vision, analytics, Docker, troubleshooting.
- **[DOCUMENTATION.md](DOCUMENTATION.md)** — architecture, execution pipelines, API reference, database schema, configuration, agent tools, and security notes.

---

## License

MIT License.
