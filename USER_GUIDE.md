# Ollama Desktop Chatbot: User Guide & Manual

Welcome to the **Ollama Desktop Chatbot** user manual! This guide covers everything you need to know to install, configure, and use your desktop AI application.

---

## Table of Contents
1. [System Requirements & Prerequisites](#1-system-requirements--prerequisites)
2. [Installation Guide](#2-installation-guide)
3. [Starting the Application](#3-starting-the-application)
4. [User Interface Overview](#4-user-interface-overview)
5. [Attaching Files with the '+' Button](#5-attaching-files-with-the--button)
6. [Using Local Ollama Models](#6-using-local-ollama-models)
7. [Configuring Online LLMs (API Keys)](#7-configuring-online-llms-api-keys)
8. [Real-Time Web Search (Internet RAG)](#8-real-time-web-search-internet-rag)
9. [The 'Append Chat' Memory Toggle](#9-the-append-chat-memory-toggle)
10. [Token Analytics, Speed Metrics & Budget Limits](#10-token-analytics-speed-metrics--budget-limits)
11. [Exporting Chats (DOCX & Markdown)](#11-exporting-chats-docx--markdown)
12. [Docker Deployment](#12-docker-deployment)
13. [Troubleshooting & FAQs](#13-troubleshooting--faqs)

---

## 1. System Requirements & Prerequisites

- **Operating System**: Linux (Ubuntu, Debian, Fedora, Arch), macOS (10.15+), or Windows 10/11.
- **Python**: Version 3.10 or newer.
- **Ollama (Optional for Local Models)**:
  - Download and install from [ollama.com](https://ollama.com).
  - Ensure Ollama is running (`ollama serve`).

---

## 2. Installation Guide

The project includes automated installation scripts that configure a dedicated Python virtual environment and install all dependencies automatically.

### On Linux or macOS:
Open a terminal in the project directory and run:
```bash
./install.sh
```

### On Windows:
Double-click `install.bat` (or open Command Prompt / PowerShell in the folder and run):
```cmd
install.bat
```

### Manual Installation (Alternative):
If you prefer setting up manually:
```bash
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Starting the Application

### One-Click Launchers:
- **Linux / macOS**: `./run.sh`
- **Windows**: Double-click `run.bat`

### Launch via Python Terminal:
```bash
# With virtual environment activated:
python main.py
```
*The app automatically starts the local backend and launches a native desktop application window. If desktop display libraries are absent, it opens automatically in your default web browser.*

### Running in Headless / Server Mode:
If running on a remote server or Docker container without opening a browser window:
```bash
python main.py --headless
```
Access the application at `http://localhost:8080`.

---

## 4. User Interface Overview

The interface features an **Antigravity / Cursor-inspired dark blue and black theme** (`#070a12`, `#172554`, `#1e3a8a`, `#2563eb`):

```
┌─────────────────┬────────────────────────────────────────────────────────┐
│  Ollama Desktop │ [ Model Dropdown: llama3.2:1b v ]  [ 0 tok ] [Export]  │
├─────────────────┼────────────────────────────────────────────────────────┤
│ [+ New Chat]    │                                                        │
│ [Search chats..]│                     Chat Feed                          │
│                 │                                                        │
│ - Research      │  User: How does async file I/O work in Python?         │
│ - Data Analysis │  Assistant: [Detailed Markdown & Code Block]           │
│ - Code Review   │  1.2s (45.1 tok/s) • 32 in / 148 out                   │
│                 │                                                        │
│                 ├────────────────────────────────────────────────────────┤
│                 │ [document.pdf (142 KB) x]                              │
│                 │ [ Type your message...                               ] │
│ [o] Ollama Live │ [ + ] [ Append Chat ] [ Web Search ]            [Send] │
└─────────────────┴────────────────────────────────────────────────────────┘
```

1. **Left Sidebar**:
   - **`+ New Chat`**: Starts a fresh conversation.
   - **Search Input**: Filters chat sessions by title in real-time.
   - **Session List**: Click any chat to view its complete history, rename it, or click the delete button to remove it.
   - **Ollama Status Dot**: Displays green when your local Ollama server is detected, or red if offline.
2. **Top Navigation Bar**:
   - **Model Selector**: Switch between local Ollama models and cloud providers on the fly.
   - **Token Usage Pill**: Displays current session token count. Click it to open the full Analytics Drawer.
   - **Export Button**: Download the conversation as a formatted Microsoft Word document (`.docx`) or Markdown (`.md`).
   - **Settings Button**: Configure API keys, token limits, and custom endpoints.
3. **Bottom Interaction Bar**:
   - **Attachment Tray**: Shows attached files with file size badges and remove buttons.
   - **`+` (Plus) Button**: Open file picker to attach documents and code.
   - **`Append Chat` Toggle**: Control multi-turn memory.
   - **`Web Search` Toggle**: Enable live internet searching.
   - **Send Button**: Submit query (or stop streaming with Stop).

---

## 5. Attaching Files with the '+' Button

Gone are the inconvenient CLI prompts! Simply click the **`+`** icon next to the chat prompt.

### Supported File Formats:
- **PDF Documents** (`.pdf`)
- **Word Documents** (`.docx`)
- **Excel Spreadsheets** (`.xlsx`, `.xls`)
- **CSV Data Files** (`.csv`)
- **PowerPoint Presentations** (`.pptx`)
- **Source Code & Text Files** (`.py`, `.cpp`, `.h`, `.c`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.txt`, `.md`)

### How to Attach:
1. Click the **`+`** icon.
2. Select one or multiple files.
3. Preview chips will appear above the input box showing the filename and size.
4. If you attach a file by accident, click the remove icon on the chip to remove it.
5. Type your question (e.g., *"Summarize the quarterly financials in this spreadsheet"* or *"Find bugs in this Python file"*) and press **Enter**.

---

## 6. Using Local Ollama Models

Local models run **100% offline, privately, and completely free of charge ($0.00)**.

### Model Discovery:
When the application starts, it queries your local Ollama instance and populates the model dropdown with all installed models (e.g. `llama3.2:1b`, `qwen2.5:1.5b`, `deepseek-r1`, etc.).

### Downloading New Models:
You can pull new models into Ollama in two ways:
1. **Via the provided helper script**:
   ```bash
   python Model_Download.py
   ```
   Select numbers from the menu to download curated models like `llama3.2:3b`, `qwen2.5-coder:7b`, or `deepseek-r1:1.5b`.
2. **Via Ollama CLI**:
   ```bash
   ollama pull qwen2.5:3b
   ollama pull llama3.2:3b
   ```
*Once downloaded, restart the app or switch chats, and the new models will appear in the dropdown!*

---

## 7. Configuring Online LLMs (API Keys)

You can seamlessly switch between local Ollama and leading cloud AI models:

1. Click the **Settings** icon in the top right.
2. Enter your API key(s) for the providers you want to use:
   - **OpenAI**: `sk-...` (Access GPT-4o, GPT-4o Mini)
   - **Anthropic**: `sk-ant-...` (Access Claude 3.5 Sonnet, Claude 3.5 Haiku)
   - **Google Gemini**: `AIzaSy...` (Access Gemini 2.0 Flash, Gemini 1.5 Pro)
   - **Groq**: `gsk_...` (Access ultra-fast Llama 3.3 70B, Mixtral)
   - **OpenRouter**: `sk-or-...` (Access DeepSeek V3, open-source models)
3. Click **Save Changes**.
4. Now select your desired online model from the top model dropdown.

> [!NOTE]
> All API keys are stored **locally on your machine** in `data/config.json`. They are never sent to third-party servers.

---

## 8. Real-Time Web Search (Internet RAG)

Need up-to-date news, documentation, or facts beyond a model's training cutoff?

1. Click the **`Web Search`** button in the bottom input toolbar so it lights up blue (`Active`).
2. Type your question (e.g., *"What are the latest AI announcements this week?"*).
3. The chatbot will:
   - Clean your search query to remove conversational fluff.
   - Retrieve the latest web snippets and URLs via DuckDuckGo.
   - Display clickable source citations in the assistant response.
   - Synthesize the answer using live facts.
4. **To go 100% offline**: Click **`Web Search`** again so it becomes inactive. Queries will strictly use local knowledge and your attached files.

---

## 9. The 'Append Chat' Memory Toggle

This restores the classic *"Remember previous decisions / files"* option from the original script directly into the modern GUI:

- **When ON (Active / Blue)**:
  - The model retains full conversational memory. It remembers earlier messages, previous answers, and previously attached files in the chat session.
  - *Best for*: Iterative coding, brainstorming, ongoing investigations.
- **When OFF (Inactive / Gray)**:
  - Each message is treated as a clean, single-turn query without carrying over prior message history.
  - *Best for*: Asking quick, unrelated questions without cluttering the model's context window or wasting tokens.

---

## 10. Token Analytics, Speed Metrics & Budget Limits

Click the **Token Pill** in the top header (`0 tokens`) to view the Analytics Dashboard:

1. **Local Engine Metrics**:
   - **Generation Speed (`tok/s`)**: Live hardware generation speed (tokens per second) from your GPU or CPU.
   - **Duration**: Total seconds taken to compute the response.
   - **Prompt & Completion Tokens**: Exact input and output token counts.
2. **Financial Cost**:
   - Local Ollama usage is always calculated at **$0.00**.
   - Cloud models calculate real-time estimated costs based on standard pricing tiers.
3. **Budget Limit Tracker**:
   - Set a maximum token budget (e.g. `100,000` tokens) in Settings.
   - The visual progress bar tracks your usage, turning **amber at 75%** and **red at 90%** to prevent unexpected cloud API costs.

---

## 11. Exporting Chats (DOCX & Markdown)

You can preserve and share your conversations at any time:

1. Click the **Export** button in the top header.
2. A prompt will ask whether you want a **Word Document** or **Markdown**:
   - **Word Document (`.docx`)**: Generates a formatted document saved to the `OutWrite Documents/` folder with headers, model details, timestamps, and attached file records (preserving the original script's capability).
   - **Markdown (`.md`)**: Downloads a clean, portable `.md` file directly to your browser/computer.

---

## 12. Docker Deployment

The application is completely containerized.

### Option A: Standard Deployment (Connects to Host Ollama)
```bash
docker compose up -d
```
Access the application at `http://localhost:8080`. The container communicates with Ollama running natively on your computer through the Docker host gateway.

### Option B: All-in-One Deployment (Bundled Containerized Ollama)
If you don't have Ollama installed on your host system:
```bash
docker compose --profile with-ollama up -d
```
This spins up both the Chatbot interface and a dedicated Ollama service container with persistent volume storage for models.

---

## 13. Troubleshooting & FAQs

### Q: Why does the Ollama status dot say "Ollama Offline"?
**A**: Ensure the Ollama server is running. Open a terminal and run `ollama serve`. You can also verify connectivity by visiting `http://localhost:11434` in your browser.

### Q: Why did a small 1B model refuse to answer a question about future dates?
**A**: Small models like `llama3.2:1b` have strict built-in cutoff filters. To get more descriptive answers without refusals, make sure **`Web Search`** is toggled ON (so the model receives live verified snippets), or switch to **`qwen2.5:1.5b`** in the model dropdown.

### Q: Where are my conversations and uploaded files stored?
**A**: Everything is stored locally in the `data/` folder:
- `data/chatbot.db`: SQLite database storing all chat sessions and analytics.
- `data/uploads/`: Attached documents.
- `data/config.json`: Local settings and API keys.
- `OutWrite Documents/`: Exported Word documents.

### Q: Can I run this without an internet connection?
**A**: **Yes!** The application is 100% offline-ready. As long as you choose a local Ollama model and leave **Web Search** toggled OFF, no data ever leaves your computer.
