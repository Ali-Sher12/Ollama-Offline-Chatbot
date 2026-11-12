# Ollama Desktop Chatbot: User Guide & Manual

Welcome to the **Ollama Desktop Chatbot** user manual! This guide covers installation, projects, models, agent mode, vision, analytics, Docker, and troubleshooting.

---

## Table of Contents

1. [System Requirements & Prerequisites](#1-system-requirements--prerequisites)
2. [Installation Guide](#2-installation-guide)
3. [Starting the Application](#3-starting-the-application)
4. [User Interface Overview](#4-user-interface-overview)
5. [Projects & Workspaces](#5-projects--workspaces)
6. [Attaching Files with the '+' Button](#6-attaching-files-with-the--button)
7. [Using Local Ollama Models](#7-using-local-ollama-models)
8. [Configuring Online LLMs & Settings](#8-configuring-online-llms--settings)
9. [Real-Time Web Search (Internet RAG)](#9-real-time-web-search-internet-rag)
10. [The 'Append Chat' Memory Toggle](#10-the-append-chat-memory-toggle)
11. [Agent Mode & Permissions](#11-agent-mode--permissions)
12. [Vision & Image Analysis](#12-vision--image-analysis)
13. [Reviewing Agent Changes](#13-reviewing-agent-changes)
14. [Managing Chats & Messages](#14-managing-chats--messages)
15. [Token Analytics, Speed Metrics & Budget Limits](#15-token-analytics-speed-metrics--budget-limits)
16. [Exporting Chats (DOCX & Markdown)](#16-exporting-chats-docx--markdown)
17. [Docker Deployment](#17-docker-deployment)
18. [Troubleshooting & FAQs](#18-troubleshooting--faqs)

---

## 1. System Requirements & Prerequisites

- **Operating System**: Linux (Ubuntu, Debian, Fedora, Arch), macOS (10.15+), or Windows 10/11.
- **Python**: Version 3.10 or newer.
- **Ollama (optional for local models)**:
  - Install from [ollama.com](https://ollama.com).
  - Start it with `ollama serve` if it is not already running.
- **Agent Mode**:
  - A tool-capable model is required.
  - A dedicated project folder is recommended for file and terminal work.
- **Docker (optional)**: Docker Engine with Docker Compose for container deployment.

---

## 2. Installation Guide

The project includes automated installers that create a virtual environment and install dependencies.

### Linux or macOS
```bash
./install.sh
```

### Windows
Double-click `install.bat`, or run:
```cmd
install.bat
```

### Manual Installation
```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Starting the Application

### One-Click Launchers
- **Linux / macOS**: `./run.sh`
- **Windows**: Double-click `run.bat`

### Launch via Python
```bash
python main.py
```

The app starts the local backend, chooses the first available port starting at `8080`, and opens a native desktop window through PyWebView. If the desktop window cannot be created, it opens in your default browser instead.

### Headless / Server Mode
```bash
python main.py --headless
```

The terminal prints the exact URL to open. In Docker, the app is served on port `8080` by default.

---

## 4. User Interface Overview

The interface uses a **Frutiger Aero / Windows 7 Glass** theme with sky-blue gradients, translucent glass panels, glossy buttons, and soft shadows.

```text
┌──────────────────────┬──────────────────────────────────────────────────────┐
│ Ollama Desktop       │ [ Model: qwen2.5:1.5b v ] [ 0 tok ] [Export] [Changes]│
│ [ Project: My App v ]│ [ Model Library ] [ Settings ]                       │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ [+ New Chat]         │                                                      │
│ [Search chats...]    │                     Chat Feed                        │
│                      │                                                      │
│ - Research notes     │  User: How does async file I/O work in Python?       │
│ - Fix parser bug     │  Assistant: [Markdown, code block, citations]        │
│ - Data analysis      │  1.2s (45.1 tok/s) • 32 in / 148 out                 │
│                      │                                                      │
│                      ├──────────────────────────────────────────────────────┤
│                      │ [document.pdf (142 KB) x]                            │
│                      │ [ Type your message...                           ]   │
│ [o] Ollama (3 models)│ [ + ] [ Append Chat ] [ Web Search ] [ Agent Mode ]  │
└──────────────────────┴──────────────────────────────────────────────────────┘
```

### Sidebar
- **Project selector**: Switch between **Global Workspace** and registered projects, open/create projects, and view recent projects.
- **`+ New Chat`**: Start a fresh conversation in the active workspace.
- **Chat search**: Filters conversation titles as you type.
- **Session list**: Click a chat to load it; hover and click the trash icon to delete it.
- **Ollama status**: Green when local Ollama is reachable, red when offline.

### Top Header
- **Searchable model picker**: Filter local and cloud models by name, provider, or tag.
- **Token pill**: Session token total; click it for the analytics dashboard.
- **Export**: Save the conversation as DOCX or Markdown.
- **Review Changes**: Appears after agent tasks modify files; shows the number of tracked files.
- **Model Library**: Download, search, cancel, or delete local Ollama models.
- **Settings**: Configure API keys, vision model, keep-alive, agent options, budget, and web-search count.

### Composer
- **Attachment tray**: Shows selected files and remove buttons.
- **`+`**: Attach documents and source files.
- **Append Chat**: Toggle multi-turn memory.
- **Web Search**: Toggle live internet search.
- **Agent Mode**: Toggle autonomous tool execution.
- **Send / Stop**: Submit the prompt or stop the current response.

### Message Actions
- Hover a message row to reveal the **Delete this message pair** button.
- Assistant messages may show citation cards, token/speed metadata, step counts, and cost estimates.
- Code blocks include a **Copy** button.

---

## 5. Projects & Workspaces

Projects keep related conversations, files, and agent instructions together.

### Global Workspace vs. Projects
- **Global Workspace** contains chats that are not tied to a project.
- **Projects** contain their own chat history and give Agent Mode a dedicated folder to work in.

### Open or Create a Project
1. Click the project selector at the top of the sidebar.
2. Choose **Open / Create Project...**.
3. Enter:
   - **Project Folder Path**: An existing directory or a new folder to create.
   - **Project Name (Optional)**: Defaults to the folder name.
   - **Project Instructions (`AGENTS.md`)**: Optional build, test, style, or behavior guidance for the agent.
4. Click **Open Project**.

If no `AGENTS.md` is supplied, the app creates a starter template containing:

- **Overview**
- **Build, Test & Run Commands**
- **Code Style & Guidelines**

You can edit this file later from **Project Overview & AGENTS.md**. The agent also recognizes `agents.md`, `.agentrules`, and `CLAUDE.md` in that priority fallback order.

### Project Overview
The edit view shows:

- **Total Files** and **Total Directories**
- A bounded project file tree
- The editable `AGENTS.md` instructions

The scan skips common dependency, build, cache, IDE, version-control, and hidden directories.

### Switching Projects
- Use **Recent Projects** in the selector to switch quickly.
- The active project is highlighted.
- Project conversations are loaded automatically.
- Choose **Global (No Project)** to return to the global workspace.

### Removing a Project
Click the **×** next to a recent project. This unregisters the project from the app and detaches its conversations, but **does not delete any files from disk**.

### Agent Integration
When a project is active, Agent Mode uses that folder as its workspace and receives the project name plus `AGENTS.md` instructions automatically.

---

## 6. Attaching Files with the '+' Button

Click the **`+`** icon next to the prompt to attach documents or code.

### Supported Formats
- PDF (`.pdf`)
- Word (`.docx`)
- Excel (`.xlsx`, `.xls`)
- CSV (`.csv`)
- PowerPoint (`.pptx`)
- Text and source code (`.py`, `.cpp`, `.h`, `.c`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.txt`, `.md`)

### How to Attach
1. Click **`+`**.
2. Select one or more files.
3. Review the chips above the input; click **×** on a chip to remove it.
4. Ask your question and press **Enter**.

Attached content is parsed and injected into the prompt. This is useful for summaries, spreadsheet analysis, code review, and document Q&A.

> To analyze an image, use Agent Mode with the image placed in the active project folder, or provide its path in your request. See [Vision & Image Analysis](#12-vision--image-analysis).

---

## 7. Using Local Ollama Models

Local models run offline, privately, and at no API cost.

### Discovering Models
On startup, the app queries Ollama and populates the searchable model picker with installed models such as `llama3.2:1b`, `qwen2.5:1.5b`, and `deepseek-r1:1.5b`.

Use the model picker search to filter by name, provider, or tag. Arrow keys move through results; **Enter** selects; **Escape** closes the picker.

### Opening the Model Library
Click the **Model Library** button in the header.

You can:

- Search installed and recommended models.
- Download a curated recommendation or type any Ollama model name.
- Watch live download progress and the completed/total size.
- **Cancel** an in-progress download.
- **Delete** an installed model to free disk space.

Recommendations include approximate size, minimum RAM, and badges such as **Installed** or **Needs more RAM**. The RAM badge is advisory; you can still choose to download.

### Keeping a Model Loaded
Open **Settings → Keep Local Model Loaded** and choose:

- `5 minutes`
- `10 minutes`
- `30 minutes` (default)
- `45 minutes`
- `60 minutes`
- `No limit (keep in memory)`

This controls how long Ollama keeps the model in RAM after a response.

---

## 8. Configuring Online LLMs & Settings

You can switch between local Ollama and cloud models at any time.

### Add API Keys
1. Click **Settings** in the header.
2. Enter keys for the providers you use:
   - **OpenAI**: `sk-...` — GPT-4o, GPT-4o Mini, GPT-3.5 Turbo
   - **Anthropic**: `sk-ant-...` — Claude 3.5 Sonnet, Claude 3.5 Haiku
   - **Google Gemini**: `AIzaSy...` — Gemini 2.0 Flash, Gemini 1.5 Flash/Pro
   - **Groq**: `gsk_...` — fast Llama and Mixtral models
   - **OpenRouter**: `sk-or-...` — hosted open-source models
3. Click **Save Changes**.
4. Select the model from the searchable picker.

> API keys are stored locally in `data/config.json`. They are only sent to the provider you select.

### Settings Reference

| Setting | Default | What it does |
| :--- | :--- | :--- |
| **Local Ollama URL** | `http://localhost:11434` | Address of the local Ollama server. |
| **OpenAI / Anthropic / Gemini / Groq / OpenRouter API Key** | Empty | Enables the corresponding cloud provider. |
| **Vision Provider / Model (Optional)** | Empty / Auto | Forces a vision-capable model for image analysis. Leave blank for automatic routing. |
| **Keep Local Model Loaded** | `30 minutes` | Ollama keep-alive duration. |
| **Agent Workspace Directory** | Project root | Workspace used when no project is active. |
| **Agent Permissions** | `Allow All` | `Allow All` or `Always Ask` approval mode. |
| **Token Budget Limit** | `100,000` | Budget target used by analytics. |
| **Web Search Results Count** | `10` | Number of search results per query (`5–20`). |

Settings are saved when you click **Save Changes**. Web Search and Append Chat toggles are session controls in the composer.

---

## 9. Real-Time Web Search (Internet RAG)

1. Click **Web Search** in the composer so it becomes active.
2. Ask a question that needs current information.
3. The app will:
   - Clean the query for search.
   - Retrieve DuckDuckGo snippets and URLs.
   - Display a **Web Search Citations** card with numbered links.
   - Include the snippets in the model context.
4. Set **Web Search Results Count** in Settings to control how many results are retrieved (`5–20`).
5. Toggle **Web Search** off for fully offline answers using local knowledge and attachments.

---

## 10. The 'Append Chat' Memory Toggle

**Append Chat ON**
- The model receives previous messages in the conversation.
- Best for iterative coding, debugging, and ongoing research.

**Append Chat OFF**
- Each prompt is treated as a single-turn request without prior messages.
- Best for unrelated questions or saving context tokens.

This toggle is a per-session composer control and is sent with each chat request.

---

## 11. Agent Mode & Permissions

Agent Mode lets the model autonomously plan and execute multi-step work using tools.

### Enable Agent Mode
Click **Agent Mode** in the composer so it is active, then send your request.

### Model Requirements
The selected model must support tool calling. For local models, the app verifies the model is installed and advertises tool capability. For cloud providers, the provider API key must be configured. If not, the app reports the exact reason before starting.

Good tool-capable choices include `qwen2.5:1.5b`, `qwen2.5:3b`, `mistral`, and stronger coding models.

### What the Agent Can Do
The agent has **26 tools**, grouped into:

- **Terminal & processes**: run shell commands, run scripts in several languages, start/inspect/kill background processes.
- **Filesystem inspection**: list files, render directory trees, read files and line ranges, stat files, search contents, hash files, read binary files.
- **Filesystem modification**: write, append, edit, insert lines, apply patches, create directories/symlinks, move, copy, delete, and write binary files.
- **Documents & vision**: create/modify Word documents and analyze images.

### Permission Modes
Open **Settings → Agent Permissions**.

- **Allow All** — Runs tools without pausing. Catastrophic command patterns are still blocked.
- **Always Ask** — Pauses before terminal commands and state-changing file operations. Read-only inspection runs automatically.

### Approval Dialog
When approval is required, the dialog shows the action, target, risk level, and a command or content preview.

Choose:

- **Allow Once** — Approve only this action.
- **Always Allow (this task)** — Skip future prompts for that tool during the current task.
- **Deny** — Block the action; the agent can adapt or explain the failure.

If you stop the agent, pending approvals are cancelled. Unanswered prompts time out after five minutes by default.

### Tips for Good Agent Tasks
- Be specific about the goal and acceptance criteria.
- Use a dedicated project folder.
- Ask the agent to inspect before editing and verify after changes.
- Keep destructive operations behind **Always Ask**.
- Review the changed-file list when the task finishes.

### Stop the Agent
While generating, the Send button changes to **Stop**. Clicking it aborts the stream, cancels the agent task, and clears pending approvals.

> **Safety:** Agent Mode can execute shell commands and modify files with your user permissions. Use trusted workspaces and review approvals carefully.

---

## 12. Vision & Image Analysis

The agent includes multimodal image analysis through the `analyze_image` tool.

### Supported Analysis Modes
- **OCR**: Read text, labels, handwriting, and document layouts.
- **Charts and graphs**: Identify chart types, axes, legends, trends, and estimated values.
- **Diagrams and flowcharts**: Describe components, connections, and decision paths.
- **Tables**: Extract headers/rows and produce Markdown-table output.
- **General scenes**: Objects, relationships, and visual details.
- **Geometry**: OpenCV contour/shape detection for circles, rectangles, triangles, and polygons.

### Analyze an Image
1. Place the image in the active project folder (or provide a path the agent can access).
2. Enable **Agent Mode**.
3. Ask, for example:
   - *"Use OCR to extract all text from invoice.png."*
   - *"Describe the trend in sales_chart.jpg."*
   - *"Analyze the flowchart in diagram.png."*

The agent can also extract and inspect the first embedded image from a PDF, DOCX, or PPTX file.

### Choosing a Vision Model
By default, the app looks for a suitable local vision model, then uses the current provider or a configured cloud fallback. To force a specific model, set **Vision Provider / Model** in Settings, for example `llama3.2-vision` or `gemini-2.0-flash`.

---

## 13. Reviewing Agent Changes

After agent tasks change files, the **Review Changes** button appears in the header with a count badge.

1. Click **Review Changes**.
2. Review the list of files marked:
   - `created`
   - `modified`
   - `deleted`
3. Click a file to see its path, action, tool, and recording time.
4. Click **Clear Tracking** to reset the session list.

Tracking records successful agent tools whose names contain `file`, `edit`, or `write` (for example `write_file`, `edit_file`, `append_file`, and `delete_file`). Because of that name-based filter, some read-only file inspections can appear in the list, while tools such as `manage_docx` are not tracked. The panel records change metadata for the current session; it is not a full unified-diff viewer and resets when the page reloads.

---

## 14. Managing Chats & Messages

### New Chat
Click **`+ New Chat`** to start a conversation in the active workspace. The app titles it automatically from the first user message.

### Find a Chat
Use the **Search chats...** field. Filtering is case-insensitive and matches conversation titles.

### Delete a Chat
Hover a conversation and click the trash icon. Confirm deletion. This removes the conversation and its messages; analytics history is not removed.

### Delete a Message Pair
Hover a message row and click the **Delete this message pair** button.

- Deleting a **user message** also deletes the assistant reply that immediately follows it.
- Deleting an **assistant reply** also deletes the user message that immediately precedes it.
- Click **Delete pair** to confirm. This cannot be undone.
- Deletion is disabled while a response is streaming.

### Markdown & Code
Assistant responses render Markdown. Code blocks are syntax-highlighted and include a **Copy** button.

---

## 15. Token Analytics, Speed Metrics & Budget Limits

Click the **Token Pill** in the header to open **Token Analytics & Budget Tracker**.

### Metrics
- **Total Tokens Used**: Persisted usage across conversations.
- **Estimated Cost**: Cloud cost estimate; local Ollama is `$0.00`.
- **Prompt (Input)**: Input tokens.
- **Completion (Output)**: Output tokens.
- **Generation Speed**: Tokens per second in each assistant response.
- **Duration**: Response time in seconds.

The header token pill is a separate **session** counter; the analytics modal reports persisted totals.

### Budget Meter
- Set **Token Budget Limit** in Settings (for example, `100,000`).
- The progress bar turns amber from **75%** and red from **90%**.
- Remaining tokens are shown below the bar. If no budget is set, the backend reports unlimited remaining tokens, although the usage line may fall back to showing a `100,000` display value.

The budget is informational and does not block requests.

---

## 16. Exporting Chats (DOCX & Markdown)

1. Open the conversation you want to export.
2. Click **Export** in the header.
3. Choose:
   - **OK** → export as a Word document (`.docx`), saved to `OutWrite Documents/`.
   - **Cancel** → download Markdown (`.md`) directly.

Markdown export works from the header button. The DOCX export backend exists and writes a `.docx` into `OutWrite Documents/`, but the current header button opens the DOCX URL with a `GET` request while the server route expects `POST`, so Word export may return an error. Use Markdown export if DOCX does not download.

---

## 17. Docker Deployment

The app ships with a multi-stage Dockerfile and Compose profiles.

### Prepare the Environment
```bash
cp .env.example .env
```

### Option A: Connect to Ollama on the Host
```bash
docker compose up -d
```
The container reaches host Ollama through `host.docker.internal:host-gateway`. Open `http://localhost:8080`.

### Option B: Bundle Ollama (CPU)
```bash
docker compose --profile with-ollama up -d
```

### Option C: Bundle Ollama with NVIDIA GPU
```bash
docker compose --profile gpu up -d
```
Requires the NVIDIA Container Toolkit on the host.

### Persistent Data
- `chatbot_data` stores the database, settings, and uploads under `/app/data`.
- `ollama_models` stores bundled Ollama model weights.
- `AGENT_WORKSPACE_HOST` (default `./workspace`) is mounted into the agent workspace.

Provider API keys are best entered through **Settings** after launch so they persist in the `data` volume.

### Docker CLI
```bash
docker build -t ollama-desktop-chatbot .
docker run -p 8080:8080 -v "$(pwd)/data:/app/data" ollama-desktop-chatbot
```

---

## 18. Troubleshooting & FAQs

### Q: Why does the Ollama status say "Ollama Offline"?
**A**: Make sure Ollama is running with `ollama serve` and reachable at the URL in **Settings** (default `http://localhost:11434`). In Docker, verify that the container can reach the host or bundled Ollama service.

### Q: Why does a small model refuse to answer about recent events?
**A**: Small models have training cutoffs and may refuse future-date questions. Enable **Web Search**, or switch to a stronger model such as `qwen2.5:1.5b` or larger.

### Q: Why does Agent Mode fail before doing anything?
**A**: Check that:
- The selected model is installed and supports tool calling.
- Ollama is reachable.
- A cloud provider key is configured when using an online model.
- The project/workspace path exists and is writable.

### Q: The agent stopped with an error or cancellation.
**A**: The app now shows the actual failure or cancellation reason. If a permission prompt timed out, send the request again or switch to **Allow All** if you trust the workspace.

### Q: Where are project instructions stored?
**A**: In the project root as `AGENTS.md`. The agent also recognizes `agents.md`, `.agentrules`, and `CLAUDE.md` as fallbacks.

### Q: Does removing a project delete my files?
**A**: No. Removing a project only unregisters it and detaches its conversations. Files remain on disk.

### Q: Where are conversations, uploads, and settings stored?
**A**: In the local `data/` folder:
- `data/chatbot.db` — projects, conversations, messages, analytics
- `data/uploads/` — attached files
- `data/config.json` — settings and API keys
- `OutWrite Documents/` — exported Word documents

### Q: Can I use the app fully offline?
**A**: Yes. Select a local Ollama model, leave **Web Search** off, and use attached documents or local project files. Agent Mode tools also run locally.

### Q: Why is my new model not in the picker?
**A**: Open the **Model Library** and refresh, or switch chats to trigger a model refresh. Confirm the download finished and Ollama is reachable.

### Q: A model download is stuck.
**A**: Open the Model Library and click **Cancel**, then retry. Check that Ollama has enough disk space and network access.

### Q: Why can't I delete a message while the AI is responding?
**A**: Message-pair deletion is disabled during streaming so the in-progress reply cannot be orphaned. Wait for the response to finish or click **Stop**, then delete the pair.

### Q: Where is the vision model configured?
**A**: In **Settings → Vision Provider / Model**. Leave it blank to let the app choose a local vision model or a configured cloud fallback.

### Q: How do I run the tests?
```bash
python -m unittest discover -s tests -v
```
