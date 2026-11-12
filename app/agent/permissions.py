import re
import json
import time
import uuid
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple, Union, Optional, Dict, Any, Set
from app.config import config_manager

# Patterns of catastrophic / dangerous commands to block
DANGEROUS_COMMAND_PATTERNS = [
    r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*)\s+(/|/\*|~|~/\*)(\s+|$)",
    r"\bmkfs(\.[a-z0-9]+)?\b",
    r"\bdd\s+if=/dev/(zero|urandom)\s+of=/dev/[a-z0-9]+",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
    r"\b(shutdown|reboot|poweroff|init\s+0)\b",
    r"\bchmod\s+(-R\s+)?000\s+(/|/\*|~)",
    r">\s*/dev/(sda|sdb|nvme|hda)"
]

# Tools that only inspect state and never need an approval prompt.
READ_ONLY_TOOLS = {
    "list_files", "tree", "read_file", "stat_file", "file_hash",
    "search_files", "analyze_image",
    "get_background_process_output", "list_background_processes",
    "read_binary_file",
}

VALID_PERMISSION_MODES = {"allow_all", "always_ask"}


def _short(value: Any, limit: int = 4000) -> str:
    """Return a safe, display-sized string for permission prompts."""
    text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False, default=str)
    if len(text) > limit:
        return text[:limit] + "\n... (truncated)"
    return text


def _as_args(arguments: Any) -> Dict[str, Any]:
    """Coerce tool arguments into a dictionary for permission checks."""
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            return {"raw": arguments}
    if arguments is None:
        return {}
    return {"value": arguments}


class PermissionManager:
    """Safeguards filesystem access and terminal execution for the autonomous agent."""

    _active_workspace_override: Optional[Path] = None

    @classmethod
    def set_active_workspace(cls, path_val: Optional[Union[str, Path]]) -> None:
        """Set the active working directory for the agent (e.g., active project root)."""
        if path_val:
            p = Path(path_val).resolve()
            p.mkdir(parents=True, exist_ok=True)
            cls._active_workspace_override = p
        else:
            cls._active_workspace_override = None

    @classmethod
    def get_workspace_dir(cls) -> Path:
        if cls._active_workspace_override and cls._active_workspace_override.exists():
            return cls._active_workspace_override
        configured = config_manager.get("agent_workspace")
        if configured:
            p = Path(configured).resolve()
            p.mkdir(parents=True, exist_ok=True)
            return p
        default_ws = Path(__file__).resolve().parent.parent.parent
        return default_ws

    @classmethod
    def resolve_safe_path(cls, path_str: Union[str, Path], allow_outside: bool = False) -> Path:
        """
        Resolves a path safely against the configured workspace directory.
        Raises PermissionError if path traversal escapes the workspace unless explicitly allowed.
        """
        workspace = cls.get_workspace_dir()
        target = Path(path_str)

        if not target.is_absolute():
            resolved = (workspace / target).resolve()
        else:
            resolved = target.resolve()

        if not allow_outside:
            try:
                resolved.relative_to(workspace)
            except ValueError:
                # Also allow data uploads directory for accessing user attachments
                uploads_dir = (workspace / "data" / "uploads").resolve()
                try:
                    resolved.relative_to(uploads_dir)
                except ValueError:
                    raise PermissionError(
                        f"Access denied: Path '{path_str}' resolves outside workspace boundary '{workspace}'"
                    )

        return resolved

    @classmethod
    def get_mode(cls) -> str:
        """Return the active Agent permission mode: 'allow_all' or 'always_ask'."""
        mode = str(config_manager.get("agent_permission_mode", "allow_all") or "allow_all").strip().lower()
        return mode if mode in VALID_PERMISSION_MODES else "allow_all"

    @classmethod
    def requires_approval(cls, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> bool:
        """
        Decide whether the agent must pause for user approval before running a tool.

        In Allow All mode every tool runs immediately. In Always Ask mode commands and
        state-changing file operations require approval; read-only inspection does not.
        """
        if cls.get_mode() != "always_ask":
            return False

        args = _as_args(arguments)

        if tool_name in READ_ONLY_TOOLS:
            return False

        if tool_name == "manage_docx":
            action = str(args.get("action", "read")).strip().lower()
            return action != "read"

        # Any tool not explicitly marked read-only is treated as state-changing.
        return True

    @classmethod
    def describe_action(cls, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build a human-readable description of a tool action for the approval modal."""
        args = _as_args(arguments)

        def present(key: str, fallback: str = "") -> str:
            value = args.get(key, fallback)
            return _short(value if value is not None else fallback)

        if tool_name == "run_terminal":
            command = present("command")
            cwd = args.get("cwd") or "workspace root"
            return {
                "kind": "terminal",
                "title": "Run terminal command",
                "detail": f"Working directory: {cwd}",
                "preview_label": "Command",
                "preview": command,
                "risk": "high",
            }

        if tool_name == "write_file":
            path = present("path")
            return {
                "kind": "file_write",
                "title": f"Write file: {path}",
                "detail": "Creates a new file or overwrites existing content.",
                "preview_label": "New content",
                "preview": present("content"),
                "risk": "medium",
            }

        if tool_name == "edit_file":
            path = present("path")
            target = present("target_text")
            replacement = present("replacement_text")
            preview = f"--- current text\n{target}\n\n+++ replacement text\n{replacement}"
            return {
                "kind": "file_edit",
                "title": f"Edit file: {path}",
                "detail": "Applies a targeted find-and-replace to this file.",
                "preview_label": "Proposed change",
                "preview": _short(preview),
                "risk": "medium",
            }

        if tool_name == "delete_file":
            path = present("path")
            return {
                "kind": "file_delete",
                "title": f"Delete: {path}",
                "detail": "This permanently removes the file or folder from disk.",
                "preview_label": "",
                "preview": "",
                "risk": "high",
            }

        if tool_name in ("move_file", "copy_file"):
            source = present("source")
            destination = present("destination")
            verb = "Move" if tool_name == "move_file" else "Copy"
            return {
                "kind": "file_move" if tool_name == "move_file" else "file_copy",
                "title": f"{verb} file or folder",
                "detail": f"{source}  →  {destination}",
                "preview_label": "",
                "preview": "",
                "risk": "medium",
            }

        if tool_name == "manage_docx":
            action = str(args.get("action", "read")).strip().lower()
            path = present("file_path")
            preview = ""
            preview_label = ""
            if action in ("create", "add_paragraph", "modify_paragraph"):
                preview_label = "Text"
                preview = present("text")
            elif action == "replace_text":
                preview_label = "Proposed change"
                preview = f"--- current text\n{present('target_text')}\n\n+++ replacement text\n{present('replacement_text')}"
            elif action in ("add_table", "modify_table"):
                preview_label = "Table data"
                preview = present("table_data")
            return {
                "kind": "docx",
                "title": f"{action.replace('_', ' ').title()} Word document",
                "detail": path,
                "preview_label": preview_label,
                "preview": _short(preview) if preview else "",
                "risk": "medium",
            }

        if tool_name == "run_script":
            return {
                "kind": "terminal",
                "title": f"Run {args.get('language', 'python')} script",
                "detail": f"Language: {args.get('language', 'python')}",
                "preview_label": "Code",
                "preview": _short(args.get("code", "")),
                "risk": "high",
            }

        if tool_name in ("start_background_process",):
            command = present("command")
            cwd = args.get("cwd") or "workspace root"
            label = args.get("label", "")
            return {
                "kind": "terminal",
                "title": f"Start background process{': ' + label if label else ''}",
                "detail": f"Working directory: {cwd}",
                "preview_label": "Command",
                "preview": command,
                "risk": "high",
            }

        if tool_name == "kill_background_process":
            return {
                "kind": "terminal",
                "title": "Kill background process",
                "detail": f"Process ID: {args.get('process_id', '')}",
                "preview_label": "",
                "preview": "",
                "risk": "medium",
            }

        if tool_name == "append_file":
            path = present("path")
            return {
                "kind": "file_write",
                "title": f"Append to file: {path}",
                "detail": "Appends text to the end of this file.",
                "preview_label": "Content to append",
                "preview": present("content"),
                "risk": "medium",
            }

        if tool_name == "insert_lines":
            path = present("path")
            after_line = args.get("after_line", "?")
            return {
                "kind": "file_edit",
                "title": f"Insert lines into: {path}",
                "detail": f"Inserts text after line {after_line}.",
                "preview_label": "Content to insert",
                "preview": present("content"),
                "risk": "medium",
            }

        if tool_name == "apply_patch":
            path = present("path")
            return {
                "kind": "file_edit",
                "title": f"Apply patch to: {path}",
                "detail": "Applies a unified diff patch to this file.",
                "preview_label": "Patch",
                "preview": present("patch"),
                "risk": "medium",
            }

        if tool_name == "create_directory":
            return {
                "kind": "file_write",
                "title": f"Create directory: {present('path')}",
                "detail": "Creates the directory and all parent directories.",
                "preview_label": "",
                "preview": "",
                "risk": "low",
            }

        if tool_name == "create_symlink":
            return {
                "kind": "file_write",
                "title": f"Create symlink: {present('link_path')} → {present('target')}",
                "detail": "",
                "preview_label": "",
                "preview": "",
                "risk": "low",
            }

        if tool_name == "write_binary_file":
            path = present("path")
            return {
                "kind": "file_write",
                "title": f"Write binary file: {path}",
                "detail": "Writes base64-decoded binary content to disk.",
                "preview_label": "",
                "preview": "",
                "risk": "medium",
            }

        return {
            "kind": "tool",
            "title": f"Run {tool_name}",
            "detail": "The agent wants to use this tool.",
            "preview_label": "Arguments",
            "preview": _short(args) if args else "",
            "risk": "medium",
        }

    @classmethod
    def is_safe_command(cls, command: str) -> Tuple[bool, str]:
        """
        Inspects terminal command for catastrophic or dangerous patterns.
        """
        cleaned = command.strip()
        if not cleaned:
            return False, "Command cannot be empty"

        for pat in DANGEROUS_COMMAND_PATTERNS:
            if re.search(pat, cleaned, re.IGNORECASE):
                return False, f"Blocked dangerous command pattern matching safety policy: {pat}"

        return True, "Command permitted"

    @classmethod
    def get_timeout(cls, requested_timeout: int = None) -> int:
        if requested_timeout and requested_timeout > 0:
            return min(requested_timeout, 300)  # capped at 5 minutes
        return int(config_manager.get("agent_timeout_seconds", 300))


@dataclass
class PendingPermission:
    request_id: str
    task_id: str
    tool_name: str
    arguments: Dict[str, Any]
    details: Dict[str, Any]
    event: threading.Event = field(default_factory=threading.Event)
    decision: Optional[str] = None
    resolution: Optional[str] = None
    created_at: float = field(default_factory=time.time)


class PermissionBroker:
    """
    Coordinates approval prompts between the synchronous agent loop and the
    asynchronous HTTP endpoint that receives the user's decision.
    """

    def __init__(self):
        self._pending: Dict[str, PendingPermission] = {}
        self._task_allowed_tools: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()

    def create_request(
        self,
        task_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        details: Dict[str, Any],
    ) -> Optional[PendingPermission]:
        with self._lock:
            # Prune abandoned requests so a disconnected client cannot leak memory.
            now = time.time()
            for stale_id, stale_request in list(self._pending.items()):
                if now - stale_request.created_at > 3600:
                    self._pending.pop(stale_id, None)

            if tool_name in self._task_allowed_tools.get(task_id, set()):
                return None
            request = PendingPermission(
                request_id=f"perm_{uuid.uuid4().hex[:12]}",
                task_id=task_id,
                tool_name=tool_name,
                arguments=arguments,
                details=details,
            )
            self._pending[request.request_id] = request
            return request

    def wait_for_decision(
        self,
        request_id: str,
        timeout: float = 300.0,
        cancel_check=None,
    ) -> Tuple[str, str]:
        """
        Block until the user responds, the task is cancelled, or the request times out.

        Returns (decision, resolution) where decision is "allow" or "deny" and
        resolution is the concrete outcome ("allow", "always_allow", "deny",
        "cancelled", "timeout", or "missing").
        """
        with self._lock:
            request = self._pending.get(request_id)

        if not request:
            return "deny", "missing"

        deadline = time.time() + max(1.0, float(timeout))
        while time.time() < deadline:
            if request.event.wait(0.2):
                with self._lock:
                    self._pending.pop(request_id, None)
                return request.decision or "deny", request.resolution or "resolved"

            if cancel_check and cancel_check():
                with self._lock:
                    self._pending.pop(request_id, None)
                return "deny", "cancelled"

        with self._lock:
            self._pending.pop(request_id, None)
        return "deny", "timeout"

    def resolve(self, request_id: str, decision: str) -> bool:
        decision = (decision or "").strip().lower()
        if decision not in ("allow", "deny", "always_allow"):
            return False

        with self._lock:
            request = self._pending.get(request_id)
            if not request:
                return False

            if decision == "always_allow":
                self._task_allowed_tools.setdefault(request.task_id, set()).add(request.tool_name)

            request.decision = "allow" if decision in ("allow", "always_allow") else "deny"
            request.resolution = decision
            request.event.set()
            return True

    def cancel_task(self, task_id: str) -> None:
        """Deny any pending requests for a task and forget its per-task allowlist."""
        with self._lock:
            self._task_allowed_tools.pop(task_id, None)
            requests = [r for r in self._pending.values() if r.task_id == task_id]
            for request in requests:
                request.decision = "deny"
                request.resolution = "cancelled"
                request.event.set()
            # Requests are removed by wait_for_decision() or the TTL pruner in
            # create_request(), so a waiter that starts late still sees "cancelled".

    def allow_all_pending(self) -> int:
        """Approve every pending request (used when the user switches to Allow All)."""
        with self._lock:
            requests = list(self._pending.values())
            for request in requests:
                request.decision = "allow"
                request.resolution = "allow_all"
                request.event.set()
            return len(requests)

    def cleanup_task(self, task_id: str) -> None:
        self.cancel_task(task_id)

    def is_allowed_for_task(self, task_id: str, tool_name: str) -> bool:
        with self._lock:
            return tool_name in self._task_allowed_tools.get(task_id, set())

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)


permission_manager = PermissionManager()
permission_broker = PermissionBroker()
