import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class TaskState:
    """Maintains in-memory execution state, tool history, and metrics for an active agent task."""

    def __init__(self, objective: str, conversation_id: str, task_id: Optional[str] = None):
        self.task_id = task_id or str(uuid.uuid4())
        self.objective = objective
        self.conversation_id = conversation_id
        self.status = "running"  # "running" | "completed" | "failed" | "cancelled"
        self.steps: List[Dict[str, Any]] = []
        self.modified_files: List[str] = []
        self.errors_encountered: List[str] = []
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        self.status = "cancelled"
        self.updated_at = datetime.now(timezone.utc).isoformat()

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def add_step(self, iteration: int, thought: str = "") -> Dict[str, Any]:
        step = {
            "iteration": iteration,
            "thought": thought,
            "tool_calls": [],
            "tool_results": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.steps.append(step)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return step

    def record_tool_call(self, iteration: int, tool_name: str, arguments: Dict[str, Any], call_id: str):
        if not self.steps:
            self.add_step(iteration)
        current = self.steps[-1]
        current["tool_calls"].append({
            "call_id": call_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def record_tool_result(self, call_id: str, tool_name: str, result: Dict[str, Any]):
        if not self.steps:
            self.add_step(1)
        current = self.steps[-1]
        current["tool_results"].append({
            "call_id": call_id,
            "tool_name": tool_name,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        if not result.get("success", True):
            self.errors_encountered.append(f"Tool '{tool_name}' error: {result.get('error', 'Unknown error')}")
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def record_modified_file(self, file_path: str):
        if file_path not in self.modified_files:
            self.modified_files.append(file_path)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "objective": self.objective,
            "conversation_id": self.conversation_id,
            "status": self.status,
            "steps_count": len(self.steps),
            "steps": self.steps,
            "modified_files": self.modified_files,
            "errors": self.errors_encountered,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
