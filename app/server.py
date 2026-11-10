import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import config_manager
from app.database import db
from app.services.file_service import file_service
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service
from app.services.analytics_service import analytics_service

app = FastAPI(title="Ollama Desktop Chatbot", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Models for request validation
class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    attachments: Optional[List[Dict[str, Any]]] = None
    use_web_search: bool = False
    append_chat: Optional[bool] = True
    provider: Optional[str] = None
    model: Optional[str] = None

class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Chat"
    provider: Optional[str] = None
    model: Optional[str] = None

class UpdateTitleRequest(BaseModel):
    title: str

class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any]


@app.get("/api/models")
async def get_models():
    """Returns local Ollama models and available online LLM providers."""
    return llm_service.get_all_available_models()


@app.get("/api/conversations")
async def list_conversations():
    """List all saved conversations."""
    return db.list_conversations()


@app.post("/api/conversations")
async def create_conversation(req: CreateConversationRequest):
    """Create a new conversation session."""
    provider = req.provider or config_manager.get("selected_provider", "ollama")
    model = req.model or config_manager.get("selected_model", "llama3.2:1b")
    conv = db.create_conversation(title=req.title or "New Chat", provider=provider, model=model)
    return conv


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    """Get full conversation with messages."""
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@app.patch("/api/conversations/{conv_id}")
async def update_conversation(conv_id: str, req: UpdateTitleRequest):
    """Update conversation title."""
    success = db.update_conversation_title(conv_id, req.title)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "ok", "title": req.title}


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Delete a conversation."""
    success = db.delete_conversation(conv_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "ok"}


@app.post("/api/conversations/{conv_id}/export")
async def export_conversation(conv_id: str, format: str = "docx"):
    """Export conversation to DOCX or Markdown file."""
    if format == "docx":
        filepath = db.export_docx(conv_id)
        if not filepath or not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="Failed to export DOCX")
        return FileResponse(filepath, filename=os.path.basename(filepath), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    else:
        conv = db.get_conversation(conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        md_lines = [f"# {conv['title']}\n\nModel: {conv['model']} ({conv['provider']})\n\n---\n"]
        for m in conv.get("messages", []):
            role_display = "User" if m["role"] == "user" else "Assistant"
            md_lines.append(f"### {role_display}\n\n{m['content']}\n\n---\n")
        return {"markdown": "\n".join(md_lines), "filename": f"{conv['title']}.md"}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload document for attachment (PDF, DOCX, TXT, CSV, XLSX, PPTX, code)."""
    try:
        dest_path = UPLOAD_DIR / file.filename
        # Handle filename collisions
        if dest_path.exists():
            stem = dest_path.stem
            suffix = dest_path.suffix
            dest_path = UPLOAD_DIR / f"{stem}_{os.urandom(4).hex()}{suffix}"

        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        metadata = file_service.get_file_metadata(dest_path)
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Streaming chat endpoint using Server-Sent Events (SSE)."""
    conv = db.get_conversation(req.conversation_id)
    if not conv:
        # Create one if doesn't exist
        conv = db.create_conversation(title="Chat", provider=req.provider or "ollama", model=req.model or "llama3.2:1b")
        req.conversation_id = conv["id"]

    provider = req.provider or conv["provider"]
    model = req.model or conv["model"]

    # 1. Web search if requested
    search_results = []
    if req.use_web_search:
        search_results = rag_service.search_web(req.message)

    # 2. Record user message in DB
    db.add_message(
        conversation_id=req.conversation_id,
        role="user",
        content=req.message,
        attachments=req.attachments,
        search_results=search_results
    )

    # Auto-rename title if it is the first user message
    if conv["title"] == "New Chat" or conv["title"] == "Chat":
        cleaned_title = " ".join(req.message.split()[:6])
        if cleaned_title:
            db.update_conversation_title(req.conversation_id, cleaned_title)

    # 3. Construct history messages for context
    history_messages = []
    system_instruction = (
        "You are an expert, helpful AI assistant. "
        "When real-time Web Search Results or documents are provided in the context, synthesize "
        "the facts and details directly to answer the user's question clearly and objectively. "
        "Do not refuse or claim you lack real-time data, as verified current information is provided in the context."
    )
    history_messages.append({"role": "system", "content": system_instruction})

    should_append = req.append_chat if req.append_chat is not None else config_manager.get("remember_context", True)
    if should_append:
        for m in conv.get("messages", []):
            if m["role"] != "system":
                history_messages.append({"role": m["role"], "content": m["content"]})

    # Build augmented prompt with attachments & web search results
    augmented_prompt = rag_service.build_augmented_context(
        user_message=req.message,
        attachments=req.attachments,
        search_results=search_results
    )
    history_messages.append({"role": "user", "content": augmented_prompt})

    def event_generator():
        accumulated_response = ""
        last_metrics = None

        # First emit search results if any
        if search_results:
            yield f"data: {json.dumps({'type': 'search_results', 'results': search_results})}\n\n"

        for event in llm_service.stream_chat(history_messages, provider=provider, model=model):
            event_type = event.get("type")
            if event_type == "chunk":
                accumulated_response += event.get("content", "")
                yield f"data: {json.dumps(event)}\n\n"
            elif event_type == "done":
                last_metrics = event
                # Save assistant message to DB
                db.add_message(
                    conversation_id=req.conversation_id,
                    role="assistant",
                    content=accumulated_response,
                    prompt_tokens=event.get("prompt_tokens", 0),
                    completion_tokens=event.get("completion_tokens", 0),
                    duration_sec=event.get("duration_sec", 0.0)
                )
                # Record in analytics table
                db.record_analytics(
                    conversation_id=req.conversation_id,
                    provider=provider,
                    model=model,
                    prompt_tokens=event.get("prompt_tokens", 0),
                    completion_tokens=event.get("completion_tokens", 0),
                    estimated_cost=event.get("estimated_cost", 0.0)
                )

                # Fetch updated budget status
                summary = db.get_analytics_summary()
                grand_total = summary["overall"].get("grand_total_tokens", 0)
                budget_limit = config_manager.get("token_budget_limit", 100000)
                budget_status = analytics_service.get_budget_status(grand_total, budget_limit)
                event["budget_status"] = budget_status

                yield f"data: {json.dumps(event)}\n\n"
            elif event_type == "error":
                yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/settings")
async def get_settings():
    """Retrieve application settings."""
    cfg = config_manager.get_all()
    # Mask API keys for safety in display (only show last 4 chars)
    safe_keys = {}
    for k, v in cfg.get("api_keys", {}).items():
        if v and len(v) > 6:
            safe_keys[k] = f"{v[:3]}...{v[-4:]}"
        elif v:
            safe_keys[k] = "***"
        else:
            safe_keys[k] = ""
    res = dict(cfg)
    res["masked_api_keys"] = safe_keys
    return res


@app.post("/api/settings")
async def update_settings(req: SettingsUpdateRequest):
    """Save updated application settings."""
    updated = config_manager.update(req.settings)
    return {"status": "ok", "settings": updated}


@app.get("/api/analytics")
async def get_analytics():
    """Retrieve token usage analytics and budget status."""
    summary = db.get_analytics_summary()
    grand_total = summary["overall"].get("grand_total_tokens", 0)
    budget_limit = config_manager.get("token_budget_limit", 100000)
    budget_status = analytics_service.get_budget_status(grand_total, budget_limit)
    return {
        "summary": summary,
        "budget_status": budget_status
    }


# Static files and root UI
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Ollama Desktop Chatbot - UI Initializing</h1>"
