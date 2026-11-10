# 🤖 Ollama Desktop Chatbot

A modern, minimal, and powerful desktop AI application inspired by **Antigravity** and **Cursor**. Built with a sleek dark blue and black aesthetic, persistent chat history, file attachments via an intuitive `+` button, seamless switching between local Ollama models and online LLMs (OpenAI, Anthropic, Gemini, Groq, OpenRouter), live Web Search RAG, token analytics, and full Docker support.

---

## ✨ Features

- **🎨 Modern Dark Blue & Black GUI**: Beautiful UI with deep navy (`#080b12`, `#172554`) accents, glowing borders, smooth streaming Markdown, and syntax-highlighted code blocks with 1-click copy.
- **📎 Streamlined Attachments (`+` Icon)**: Add documents (`.pdf`, `.docx`, `.xlsx`, `.csv`, `.pptx`, `.txt`, `.py`, `.cpp`, `.js`, etc.) using the `+` button next to the prompt, complete with chip previews and remove buttons.
- **💬 Full Chat History & Memory Control**:
  - Antigravity-style collapsible left sidebar with chat sessions, search filter, auto-titling, rename, delete, and DOCX/Markdown export.
  - **🔁 Append Chat Toggle**: Just like the original `"Remember previous decisions"` prompt, you can toggle **Append Chat** ON or OFF at any time. When ON, the model maintains full multi-turn conversation memory; when OFF, queries are treated independently without carrying over previous messages or files.
- **⚡ Local & Online LLMs**:
  - **Local Ollama**: Auto-detects all installed models (`llama3.2`, `qwen2.5`, `deepseek-r1`, etc.).
  - **Online Providers**: Connect via API keys to OpenAI (GPT-4o, GPT-4o Mini), Anthropic (Claude 3.5 Sonnet, Claude 3.5 Haiku), Google Gemini (Gemini 2.0 Flash, Gemini 1.5 Pro), Groq, and OpenRouter.
- **🌐 Internet & Document RAG**:
  - **Live Web Search**: Toggle the web search button to retrieve DuckDuckGo search snippets and citations in real time.
  - **Offline RAG**: Turn web search off to keep queries 100% private and offline using only attached documents and local models.
- **📊 User Analytics & Budget Tracking**:
  - Live token counters (prompt/input and completion/output tokens).
  - Generation speed (`tok/s`) and response duration.
  - Token budget & spending limit tracker with warning progress bar when approaching limit.
  - Estimated dollar cost for online models (and \$0.00 for local Ollama).
- **🚀 One-Click Install & Run**: Automated cross-platform scripts (`install.sh`, `install.bat`, `run.sh`, `run.bat`).
- **🐳 Full Docker Support**: Pre-configured `Dockerfile` and `docker-compose.yml` with optional bundled Ollama.

---

## 🛠️ Quick Start

### 1. Installation

#### Linux / macOS:
```bash
./install.sh
```

#### Windows:
Double-click `install.bat` (or run in CMD):
```bat
install.bat
```

*The installer sets up a Python virtual environment, installs dependencies, and verifies your local Ollama connection.*

---

### 2. Launch the Application

#### Linux / macOS:
```bash
./run.sh
```

#### Windows:
Double-click `run.bat`:
```bat
run.bat
```

#### Or directly via Python:
```bash
python main.py
```

*By default, the application opens a native desktop window (or your default browser). To run as a headless server, pass `--headless`:*
```bash
python main.py --headless
```

---

## 🐳 Docker Deployment

### Run with Docker Compose:

```bash
docker compose up -d
```
Access the application at `http://localhost:8080`.

### With Bundled Ollama (All-in-One Container Stack):
```bash
docker compose --profile with-ollama up -d
```

### Build and Run with Docker CLI:
```bash
docker build -t ollama-desktop-chatbot .
docker run -p 8080:8080 -v $(pwd)/data:/app/data ollama-desktop-chatbot
```

---

## ⚙️ Configuration & Settings

Click the **Settings (⚙️)** icon in the top right to configure:
- **Local Ollama URL**: Default `http://localhost:11434`.
- **API Keys**: Enter keys for OpenAI, Anthropic, Gemini, Groq, or OpenRouter. Keys are stored locally and securely in `data/config.json`.
- **Token Budget Limit**: Set your preferred token limit to track usage and avoid unexpected online API costs.

---

## 📁 Project Structure

```text
OllamaChatbot/
├── app/
│   ├── config.py             # Settings and API key manager
│   ├── database.py           # SQLite chat history & analytics persistence
│   ├── server.py             # FastAPI backend with SSE streaming
│   ├── services/
│   │   ├── llm_service.py    # Local Ollama + Online LLM streaming
│   │   ├── rag_service.py    # Web search RAG & document context injector
│   │   ├── file_service.py   # Multi-format document parser (PDF, DOCX, XLSX, etc.)
│   │   └── analytics_service.py # Token limits, speed, and cost calculator
│   └── static/
│       ├── index.html        # Antigravity/Cursor inspired desktop UI
│       ├── css/app.css       # Dark blue & black theme
│       └── js/app.js         # Reactive streaming & attachment manager
├── data/                     # Local persistent database, uploads & config
├── OutWrite Documents/       # Exported DOCX transcripts
├── tests/
│   └── test_app.py           # Automated unit and integration tests
├── main.py                   # Desktop launcher (pywebview / browser app)
├── install.sh / install.bat  # Automated installers
├── run.sh / run.bat          # Streamlined launchers
├── Dockerfile                # Docker container definition
├── docker-compose.yml        # Multi-container compose configuration
├── requirements.txt          # Pinned dependency requirements
└── README.md
```

---

## 📄 License
MIT License.
