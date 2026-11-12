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
from app.services.project_service import project_service
from app.agent.orchestrator import agent_orchestrator
from app.agent.tool_registry import tool_registry
from app.agent.permissions import permission_broker

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
    web_search_results_count: Optional[int] = 10
    append_chat: Optional[bool] = True
    provider: Optional[str] = None
    model: Optional[str] = None
    agent_mode: Optional[bool] = False
    project_id: Optional[str] = None

class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Chat"
    provider: Optional[str] = None
    model: Optional[str] = None
    project_id: Optional[str] = None

class CreateProjectRequest(BaseModel):
    path: str
    name: Optional[str] = None
    instructions: Optional[str] = None

class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    instructions: Optional[str] = None

class UpdateTitleRequest(BaseModel):
    title: str

class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any]

class PullModelRequest(BaseModel):
    model: str


class PermissionDecisionRequest(BaseModel):
    decision: str


@app.get("/api/system/specs")
async def get_system_specs():
    """Retrieve host hardware specifications and recommendation thresholds."""
    return llm_service.get_device_specs()


@app.get("/api/projects")
async def list_projects():
    """List all registered projects, most recently accessed first."""
    return project_service.list_projects()


@app.post("/api/projects")
async def create_or_open_project(req: CreateProjectRequest):
    """Create or open a project by directory path."""
    return project_service.open_or_create_project(
        path_str=req.path,
        name=req.name,
        instructions=req.instructions,
        set_active=True
    )


@app.get("/api/projects/active")
async def get_active_project():
    """Get the currently active project if any."""
    active = project_service.get_active_project()
    return active or {"active": None}


@app.post("/api/projects/close")
async def close_project():
    """Close the active project."""
    project_service.close_active_project()
    return {"status": "ok", "active": None}


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details, overview and instructions."""
    proj = project_service.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    overview = project_service.get_project_overview(proj["path"])
    instructions = project_service.get_project_agents_instructions(proj["path"])
    return {
        **proj,
        "overview": overview,
        "instructions_content": instructions
    }


@app.patch("/api/projects/{project_id}")
async def update_project(project_id: str, req: UpdateProjectRequest):
    """Update project metadata or instructions."""
    proj = project_service.update_project(
        project_id=project_id,
        name=req.name,
        path=req.path,
        instructions=req.instructions
    )
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Unregister a project (does not delete directory on disk)."""
    success = project_service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "ok"}


@app.post("/api/projects/{project_id}/open")
async def open_project(project_id: str):
    """Set project as active."""
    proj = project_service.set_active_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@app.get("/api/models")
async def get_models():
    """Returns local Ollama models and available online LLM providers."""
    return llm_service.get_all_available_models()


@app.get("/api/models/recommended")
async def get_recommended_models():
    """Curated local models users can download directly from the app."""
    return llm_service.get_recommended_models()


# Active download cancellation registry: model_name -> threading.Event
import threading
_pull_cancel_flags: Dict[str, threading.Event] = {}
_pull_lock = threading.Lock()


@app.post("/api/models/pull")
async def pull_model(req: PullModelRequest):
    """Download (pull) a local Ollama model and stream progress as SSE."""
    cancel_event = threading.Event()
    with _pull_lock:
        _pull_cancel_flags[req.model] = cancel_event

    def pull_event_generator():
        try:
            for event in llm_service.pull_ollama_model(req.model, cancel_event=cancel_event):
                if cancel_event.is_set():
                    yield f"data: {json.dumps({'type': 'cancelled', 'model': req.model})}\n\n"
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            with _pull_lock:
                _pull_cancel_flags.pop(req.model, None)

    return StreamingResponse(pull_event_generator(), media_type="text/event-stream")


@app.delete("/api/models/pull")
async def cancel_pull_model(model: str):
    """Cancel an in-progress model download."""
    with _pull_lock:
        flag = _pull_cancel_flags.get(model)
    if flag:
        flag.set()
        return {"status": "cancelling", "model": model}
    return {"status": "not_downloading", "model": model}


@app.delete("/api/models")
async def delete_model(model: str):
    """Delete an installed local Ollama model."""
    result = llm_service.delete_ollama_model(model)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to delete model"))
    return result


@app.get("/api/conversations")
async def list_conversations(project_id: Optional[str] = None):
    """List all saved conversations, optionally filtered by project_id."""
    return db.list_conversations(project_id=project_id)


@app.post("/api/conversations")
async def create_conversation(req: CreateConversationRequest):
    """Create a new conversation session."""
    provider = req.provider or config_manager.get("selected_provider", "ollama")
    model = req.model or config_manager.get("selected_model", "llama3.2:1b")
    conv = db.create_conversation(
        title=req.title or "New Chat",
        provider=provider,
        model=model,
        project_id=req.project_id
    )
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


@app.delete("/api/conversations/{conv_id}/messages/{msg_id}")
async def delete_message_pair(conv_id: str, msg_id: str):
    """
    Delete a user message and its paired assistant reply.
    Pass the ID of either the user message or the assistant message.
    """
    result = db.delete_message_pair(conv_id, msg_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Message not found"))
    return result


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
        conv = db.create_conversation(
            title="Chat",
            provider=req.provider or "ollama",
            model=req.model or "llama3.2:1b",
            project_id=req.project_id
        )
        req.conversation_id = conv["id"]

    project_id = req.project_id or conv.get("project_id")
    provider = req.provider or conv["provider"]
    model = req.model or conv["model"]

    # 1. Web search if requested
    search_results = []
    if req.use_web_search:
        n_results = max(1, min(20, req.web_search_results_count or 10))
        search_results = rag_service.search_web(req.message, max_results=n_results)

    # 2. Record user message in DB
    user_message = db.add_message(
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

    # 4. Check if Agent Mode is active
    if req.agent_mode:
        def agent_event_generator():
            accumulated_response = ""
            agent_errors: List[str] = []
            # Tell the UI which DB row anchors the user side of this turn so it
            # can offer delete-message-pair straight away (without a reload).
            yield f"data: {json.dumps({'type': 'user_message', 'conversation_id': req.conversation_id, 'message_id': user_message['id']})}\n\n"
            try:
                for event in agent_orchestrator.run_agent_stream(
                    objective=req.message,
                    conversation_id=req.conversation_id,
                    provider=provider,
                    model=model,
                    attachments=req.attachments,
                    history=conv.get("messages", []) if should_append else None,
                    project_id=project_id
                ):
                    event_type = event.get("type")
                    if event_type == "chunk":
                        accumulated_response += event.get("content", "")
                    elif event_type == "error":
                        agent_errors.append(event.get("error") or "Unknown agent error")
                    elif event_type == "done":
                        status = event.get("status", "unknown")
                        error_text = event.get("error") or (
                            agent_errors[-1] if agent_errors else ""
                        )

                        if status == "completed":
                            final_ans = event.get("final_answer") or accumulated_response or "Task completed."
                        elif status == "cancelled":
                            final_ans = "Agent task was cancelled."
                        elif status == "max_iterations_reached":
                            final_ans = event.get("final_answer") or accumulated_response or (
                                "Agent reached the configured step limit before finishing."
                            )
                        else:
                            final_ans = "Agent task failed before completion."
                            if error_text:
                                final_ans += f"\n\n{error_text}"
                            if accumulated_response:
                                final_ans += f"\n\nPartial output:\n{accumulated_response}"

                        # Send the resolved message/status to the UI as well as the DB.
                        event["status"] = status
                        event["error"] = error_text or None
                        event["final_answer"] = final_ans

                        # Save assistant message to DB
                        assistant_message = db.add_message(
                            conversation_id=req.conversation_id,
                            role="assistant",
                            content=final_ans,
                            prompt_tokens=event.get("prompt_tokens", 0),
                            completion_tokens=event.get("completion_tokens", 0),
                            duration_sec=event.get("duration_sec", 0.0)
                        )
                        event["message_id"] = assistant_message["id"]
                        # Record analytics
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
            except Exception as e:
                import traceback
                traceback.print_exc()
                err_event = {"type": "error", "error": f"Agent execution error: {str(e)}"}
                yield f"data: {json.dumps(err_event)}\n\n"

        return StreamingResponse(agent_event_generator(), media_type="text/event-stream")

    def event_generator():
        accumulated_response = ""
        last_metrics = None

        # Tell the UI which DB row anchors the user side of this turn so it can
        # offer delete-message-pair straight away (without a reload).
        yield f"data: {json.dumps({'type': 'user_message', 'conversation_id': req.conversation_id, 'message_id': user_message['id']})}\n\n"

        # First emit search results if any
        if search_results:
            yield f"data: {json.dumps({'type': 'search_results', 'results': search_results})}\n\n"

        try:
            for event in llm_service.stream_chat(
                history_messages,
                provider=provider,
                model=model,
                keep_alive=config_manager.get("keep_alive", "30m")
            ):
                event_type = event.get("type")
                if event_type == "chunk":
                    accumulated_response += event.get("content", "")
                    yield f"data: {json.dumps(event)}\n\n"
                elif event_type == "done":
                    last_metrics = event
                    # Save assistant message to DB
                    assistant_message = db.add_message(
                        conversation_id=req.conversation_id,
                        role="assistant",
                        content=accumulated_response,
                        prompt_tokens=event.get("prompt_tokens", 0),
                        completion_tokens=event.get("completion_tokens", 0),
                        duration_sec=event.get("duration_sec", 0.0)
                    )
                    event["message_id"] = assistant_message["id"]
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
        except Exception as e:
            err_event = {"type": "error", "error": f"Stream error: {str(e)}"}
            yield f"data: {json.dumps(err_event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/agent/cancel/{task_id}")
async def cancel_agent_task(task_id: str):
    """Cancel an active autonomous agent task."""
    cancelled = agent_orchestrator.cancel_task(task_id)
    return {"status": "ok", "cancelled": cancelled}


@app.post("/api/agent/permission/{request_id}")
async def resolve_agent_permission(request_id: str, req: PermissionDecisionRequest):
    """Resolve a pending Agent Mode permission request (allow, deny, always_allow)."""
    decision = (req.decision or "").strip().lower()
    if decision not in ("allow", "deny", "always_allow"):
        raise HTTPException(status_code=400, detail="Invalid permission decision")
    resolved = permission_broker.resolve(request_id, decision)
    if not resolved:
        raise HTTPException(status_code=404, detail="Permission request not found or already resolved")
    return {"status": "ok", "request_id": request_id, "decision": decision}


@app.get("/api/agent/tools")
async def list_agent_tools():
    """List all registered agent tools and schemas."""
    return {
        "count": len(tool_registry.list_tool_names()),
        "names": tool_registry.list_tool_names(),
        "tools": tool_registry.get_tool_definitions()
    }


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
    if str((req.settings or {}).get("agent_permission_mode", "")).lower() == "allow_all":
        permission_broker.allow_all_pending()
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
