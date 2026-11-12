import json
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Generator, Optional
from app.config import config_manager
from app.agent.task_state import TaskState
from app.agent.tool_registry import tool_registry
from app.agent.permissions import permission_manager, permission_broker
from app.services.llm_service import llm_service
from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """You are an expert, general-purpose autonomous AI agent with full control over the local machine.
You can execute any shell command, read and write any file, manage processes, and accomplish complex multi-step engineering tasks.

═══════════════════════════ AVAILABLE TOOLS ═══════════════════════════════

TERMINAL TOOLS:
  • run_terminal      — Execute ANY shell command (bash, python, node, git, docker, pip, npm, make, ffmpeg, curl, etc.)
                        Supports stdin piping, env var overrides, any working directory, up to 5-minute timeouts.
  • run_script        — Write and execute a code snippet in Python, Bash, Node.js, Ruby, Perl, or PHP.
  • start_background_process — Launch a long-running process (dev servers, watchers, build daemons).
  • get_background_process_output — Read stdout/status of a background process.
  • kill_background_process  — Terminate a background process.
  • list_background_processes — List all running background processes.

FILESYSTEM TOOLS:
  • list_files        — List directory contents with glob filtering and recursive option.
  • tree              — Show a visual directory tree (like `tree` command).
  • read_file         — Read any text file, with optional line ranges for large files.
  • stat_file         — Get file metadata: size, permissions, timestamps.
  • write_file        — Create or overwrite a file with specified content.
  • append_file       — Append text to end of a file (or create it).
  • edit_file         — Precise find-and-replace inside a file (literal match).
  • insert_lines      — Insert lines at a specific position in a file.
  • apply_patch       — Apply a unified diff patch to a file.
  • create_directory  — Create a directory and all parents.
  • create_symlink    — Create a symbolic link.
  • move_file         — Move or rename a file/directory.
  • copy_file         — Copy a file/directory.
  • delete_file       — Delete a file or directory (confirm=True required).
  • search_files      — Grep/ripgrep-like text search across files with context lines.
  • file_hash         — Compute MD5/SHA256 hash of a file.
  • read_binary_file  — Read binary file as base64.
  • write_binary_file — Write base64 data as a binary file.

DOCUMENT TOOLS:
  • manage_docx       — Read, create, and modify Word .docx documents.

VISION TOOLS:
  • analyze_image     — Use a vision LLM to describe, OCR, or analyze charts/diagrams in images.

══════════════════════════ OPERATIONAL RULES ══════════════════════════════

1. FULLY AUTONOMOUS: Accomplish goals directly with tools — never just describe what the user should do.

2. EXPLORE BEFORE ACTING: Before editing, run `tree` or `list_files` to understand structure, then `read_file`
   to see the exact current content. Never make edits blind.

3. SHELL IS YOUR SUPERPOWER: Use `run_terminal` for anything requiring the system:
   - Install packages: pip install ..., npm install, apt-get install ...
   - Run tests: pytest, jest, cargo test, go test ...
   - Build projects: make, cargo build, npm run build, mvn package ...
   - Git operations: git clone, git status, git commit ...
   - Docker: docker build, docker compose up ...
   - System inspection: ps aux, df -h, free -h, uname -a, which python3 ...
   - File operations (when simpler than multiple tool calls): find, grep, sed, awk, zip, tar ...

4. PRECISE FILE EDITING: Use `edit_file` for surgical changes (single function, single section).
   Use `write_file` for wholesale rewrites. Always `read_file` first.
   For line insertions at known positions, use `insert_lines`.

5. MULTI-STEP TASKS: Break complex goals into small verifiable steps. After each step, verify
   the result (read the file back, run a test, check exit code).

6. ERROR RECOVERY: If a command fails (non-zero exit code), read stderr, diagnose the root cause,
   fix it, and retry. Never give up after one failure.

7. LONG-RUNNING WORK: For servers/watchers/build daemons, use `start_background_process`.
   Then use `get_background_process_output` to monitor them.

8. BINARY & BINARY-ADJACENT FILES: Use `read_binary_file`/`write_binary_file` for non-text files.
   Use `run_terminal` with curl/wget/cp for downloading and moving files.

9. VERIFICATION BEFORE REPORTING: Never say a task is complete without verifying it:
   - Re-read modified files
   - Run the code / test suite
   - Check process output
   - Confirm files exist with stat_file or list_files

10. CLEAR FINAL REPORT: When done, summarize: what you did, what files were created/modified,
    what commands were run, and the verification results.

11. ACCURATE TIMING: Tool results include `duration_sec`, `duration_ms`, and `duration_display`.
    Use `duration_display` when reporting how long an operation took. Never report "0.0 seconds"
    for a completed operation; very fast operations are reported in milliseconds.

═══════════════════════════════════════════════════════════════════════════
"""


def _duration_fields(seconds: float) -> Dict[str, Any]:
    """Return human- and machine-readable elapsed time fields."""
    seconds = max(0.0, float(seconds or 0.0))
    milliseconds = max(1, int(round(seconds * 1000))) if seconds > 0 else 0
    return {
        "duration_sec": round(seconds, 4),
        "duration_ms": milliseconds,
        "duration_display": (
            f"{milliseconds} ms" if milliseconds < 1000 else f"{seconds:.2f} s"
        ),
    }


class AgentOrchestrator:
    """
    Manages autonomous agent execution loops, tool dispatch, error handling,
    and real-time event streaming for multi-step tasks.
    """

    def __init__(self):
        self.active_tasks: Dict[str, TaskState] = {}

    def cancel_task(self, task_id: str) -> bool:
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            permission_broker.cancel_task(task_id)
            return True
        return False

    def run_agent_stream(
        self,
        objective: str,
        conversation_id: str,
        provider: str,
        model: str,
        project_id: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        max_iterations: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Executes the agent loop and yields structured SSE events.
        Fully project-aware: sets workspace to project root and injects AGENTS.md instructions.
        """
        from app.database import db
        from app.services.project_service import project_service

        task = TaskState(objective=objective, conversation_id=conversation_id)
        self.active_tasks[task.task_id] = task
        start_time = time.perf_counter()
        # Agent execution is uncapped by default. A positive max_iterations
        # may still be supplied programmatically for callers that want a cap.
        max_iter = int(max_iterations) if max_iterations else 0

        # Preflight before announcing that the agent started. This avoids the
        # confusing "Agent initialized..." message followed immediately by a
        # crash when the selected model/provider cannot support Agent Mode.
        ready, readiness_error = llm_service.check_agent_readiness(provider, model)
        if not ready:
            task.status = "failed"
            duration = round(time.perf_counter() - start_time, 3)
            logger.error("Agent preflight failed: %s", readiness_error)
            self.active_tasks.pop(task.task_id, None)
            permission_broker.cleanup_task(task.task_id)
            yield {"type": "error", "error": readiness_error}
            yield {
                "type": "done",
                "task_id": task.task_id,
                "status": "failed",
                "final_answer": "",
                "error": readiness_error,
                "iterations": 0,
                "modified_files": [],
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                **_duration_fields(duration),
                "tokens_per_sec": 0.0,
                "estimated_cost": 0.0,
            }
            return

        # Check if running in a project context
        proj = db.get_project(project_id) if project_id else None
        if proj:
            permission_manager.set_active_workspace(proj["path"])
            workspace = Path(proj["path"]).resolve()
            project_name = proj["name"]
            project_instructions = project_service.get_project_agents_instructions(workspace)
        else:
            workspace = permission_manager.get_workspace_dir()
            project_name = None
            project_instructions = ""

        yield {
            "type": "agent_start",
            "task_id": task.task_id,
            "objective": objective,
            "project_id": project_id,
            "project_name": project_name,
            "workspace": str(workspace),
            "max_iterations": max_iter,
            "permission_mode": permission_manager.get_mode()
        }

        # Construct initial context
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT}
        ]

        # Workspace and environment info
        env_lines = [
            f"Active Workspace Directory: {workspace}",
            f"Operating System: Linux"
        ]
        if project_name:
            env_lines.append(f"Active Project Name: {project_name}")

        if project_instructions:
            env_lines.append(f"\nPROJECT SPECIFIC INSTRUCTIONS (from AGENTS.md):\n{project_instructions}\n")

        if attachments:
            att_info = "\n".join(
                f"- Attached File: {a.get('filename')} (Path: {a.get('filepath')})"
                for a in attachments
            )
            env_lines.append(f"Attached User Files:\n{att_info}")

        env_info = "\n".join(env_lines)

        # Previous conversation history if relevant
        if history:
            for h in history:
                if h.get("role") in ("user", "assistant") and h.get("content"):
                    messages.append({"role": h["role"], "content": h["content"]})

        user_content = f"ENVIRONMENT:\n{env_info}\n\nUSER TASK OBJECTIVE:\n{objective}"
        messages.append({"role": "user", "content": user_content})

        tools_schema = tool_registry.get_tool_definitions()

        accumulated_final_answer = ""
        agent_error: Optional[str] = None
        total_prompt_tokens = 0
        total_completion_tokens = 0

        iteration = 0
        while True:
            # A max_iter of 0 means unlimited steps (the default).
            if max_iter > 0 and iteration >= max_iter:
                break

            if task.is_cancelled:
                yield {
                    "type": "agent_step",
                    "iteration": iteration,
                    "status": "cancelled",
                    "message": "Task cancelled by user."
                }
                break

            iteration += 1
            yield {
                "type": "agent_step",
                "iteration": iteration,
                "status": "thinking",
                "message": f"Step {iteration}: Reasoning and planning actions..."
            }

            try:
                llm_response = llm_service.chat_with_tools(
                    messages=messages,
                    tools=tools_schema,
                    provider=provider,
                    model=model,
                    keep_alive=config_manager.get("keep_alive", "30m")
                )
            except Exception as e:
                err_msg = f"LLM Tool Call Failure: {str(e)}"
                logger.error(err_msg)
                agent_error = err_msg
                yield {"type": "error", "error": err_msg}
                task.status = "failed"
                break

            content = llm_response.get("content", "") or ""
            tool_calls = llm_response.get("tool_calls", []) or []
            total_prompt_tokens += llm_response.get("prompt_tokens", 0)
            total_completion_tokens += llm_response.get("completion_tokens", 0)

            step = task.add_step(iteration=iteration, thought=content)

            # If the model produced thought/explanation text
            if content:
                yield {
                    "type": "agent_thought",
                    "iteration": iteration,
                    "content": content
                }

            # Check if there are tool calls to execute
            if tool_calls:
                # Add assistant message with tool calls to context
                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"]
                            }
                        }
                        for tc in tool_calls
                    ]
                })

                # Execute each tool call
                permission_stop = False
                for tc in tool_calls:
                    call_id = tc["id"]
                    t_name = tc["name"]
                    t_args = tc["arguments"]

                    # Some providers return tool arguments as a JSON string. Normalize
                    # once so permission prompts and result tracking can inspect them.
                    if isinstance(t_args, str):
                        try:
                            parsed_args = json.loads(t_args)
                            if isinstance(parsed_args, dict):
                                t_args = parsed_args
                        except Exception:
                            pass

                    task.record_tool_call(iteration=iteration, tool_name=t_name, arguments=t_args, call_id=call_id)

                    yield {
                        "type": "tool_call",
                        "iteration": iteration,
                        "call_id": call_id,
                        "tool_name": t_name,
                        "arguments": t_args
                    }

                    # Permission gate: pause before commands and file changes.
                    if permission_manager.requires_approval(t_name, t_args):
                        details = permission_manager.describe_action(t_name, t_args)
                        request = permission_broker.create_request(
                            task.task_id, t_name, t_args, details
                        )
                        if request:
                            timeout = float(config_manager.get(
                                "agent_permission_timeout_seconds", 300
                            ) or 300)
                            yield {
                                "type": "permission_request",
                                "request_id": request.request_id,
                                "task_id": task.task_id,
                                "call_id": call_id,
                                "tool_name": t_name,
                                "details": details,
                                "timeout_seconds": timeout,
                            }
                            decision, resolution = permission_broker.wait_for_decision(
                                request.request_id,
                                timeout=timeout,
                                cancel_check=lambda: task.is_cancelled,
                            )
                            yield {
                                "type": "permission_resolved",
                                "request_id": request.request_id,
                                "task_id": task.task_id,
                                "call_id": call_id,
                                "decision": resolution,
                            }

                            if decision != "allow":
                                if resolution == "timeout":
                                    denied_output = {
                                        "success": False,
                                        "error": (
                                            f"Permission request timed out after {int(timeout)} seconds. "
                                            "The action was not run."
                                        ),
                                        "permission_denied": True,
                                        "tool": t_name,
                                    }
                                elif resolution == "cancelled":
                                    denied_output = {
                                        "success": False,
                                        "error": "Permission request cancelled by the user.",
                                        "permission_denied": True,
                                        "tool": t_name,
                                    }
                                else:
                                    denied_output = {
                                        "success": False,
                                        "error": "Permission denied by the user.",
                                        "permission_denied": True,
                                        "tool": t_name,
                                    }

                                task.record_tool_result(call_id=call_id, tool_name=t_name, result=denied_output)
                                yield {
                                    "type": "tool_result",
                                    "iteration": iteration,
                                    "call_id": call_id,
                                    "tool_name": t_name,
                                    "arguments": t_args,
                                    "result": denied_output,
                                    **_duration_fields(0.0)
                                }
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": call_id,
                                    "name": t_name,
                                    "content": json.dumps(denied_output, indent=2, ensure_ascii=False)
                                })

                                if resolution == "timeout":
                                    agent_error = denied_output["error"]
                                    logger.error(agent_error)
                                    yield {"type": "error", "error": agent_error}
                                    task.status = "failed"
                                    permission_stop = True
                                    break
                                if resolution == "cancelled":
                                    permission_stop = True
                                    break
                                # A normal denial: let the model see the result and adapt.
                                continue

                    t_start = time.perf_counter()
                    tool_output = tool_registry.execute_tool(t_name, t_args)
                    t_dur_fields = _duration_fields(time.perf_counter() - t_start)
                    t_dur = t_dur_fields["duration_sec"]
                    tool_output.update(t_dur_fields)

                    task.record_tool_result(call_id=call_id, tool_name=t_name, result=tool_output)

                    # Track file modifications for all state-changing filesystem operations
                    if isinstance(t_args, dict):
                        MODIFYING_TOOLS = {
                            "write_file", "edit_file", "append_file", "insert_lines",
                            "apply_patch", "create_directory", "create_symlink",
                            "move_file", "copy_file", "delete_file", "manage_docx",
                            "write_binary_file",
                        }
                        if t_name in MODIFYING_TOOLS:
                            file_mod = (
                                t_args.get("path")
                                or t_args.get("link_path")
                                or t_args.get("destination")
                                or t_args.get("file_path")
                                or t_args.get("output_path")
                            )
                            if file_mod:
                                task.record_modified_file(str(file_mod))

                    yield {
                        "type": "tool_result",
                        "iteration": iteration,
                        "call_id": call_id,
                        "tool_name": t_name,
                        "arguments": t_args,
                        "result": tool_output,
                        "duration_sec": t_dur,
                        "duration_ms": t_dur_fields["duration_ms"],
                        "duration_display": t_dur_fields["duration_display"]
                    }

                    # Add tool result message to conversation context
                    output_str = json.dumps(tool_output, indent=2, ensure_ascii=False)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": t_name,
                        "content": output_str
                    })

                if permission_stop:
                    if task.status == "failed":
                        break
                    # Cancellation is handled at the top of the loop.
                    continue

                # Proceed to next iteration of loop to let model evaluate results
                continue

            else:
                # Model did not call any tools; this is the final answer/resolution.
                # Guard against empty responses and malformed tool-call text, which
                # would otherwise be reported as a successful "execution complete".
                stripped_content = content.strip()
                if not stripped_content:
                    agent_error = (
                        "The selected model returned an empty response instead of a final answer. "
                        "Agent Mode needs a model with reliable tool-calling support; try a larger "
                        "local model (for example qwen2.5:1.5b, qwen2.5:3b, or mistral) or a configured cloud model."
                    )
                    logger.error(agent_error)
                    yield {"type": "error", "error": agent_error}
                    task.status = "failed"
                    break

                if stripped_content.startswith('{"type"') and '"function"' in stripped_content:
                    agent_error = (
                        "The selected model returned raw tool-call JSON instead of making a valid tool call. "
                        "Choose a model with reliable tool-calling support (for example qwen2.5:1.5b, "
                        "qwen2.5:3b, or mistral) and try again."
                    )
                    logger.error(agent_error)
                    yield {"type": "error", "error": agent_error}
                    task.status = "failed"
                    break

                accumulated_final_answer = content
                task.status = "completed"
                # Emit content chunk for rendering
                yield {
                    "type": "chunk",
                    "content": accumulated_final_answer
                }
                break

        # Optional explicit step cap reached without completion
        if max_iter > 0 and iteration >= max_iter and task.status == "running":
            task.status = "max_iterations_reached"
            notice = f"\n\n*[Notice: Agent reached the configured limit of {max_iter} steps. Task paused.]*"
            accumulated_final_answer += notice
            yield {"type": "chunk", "content": notice}

        duration = round(time.perf_counter() - start_time, 3)
        task.total_prompt_tokens = total_prompt_tokens
        task.total_completion_tokens = total_completion_tokens

        estimated_cost = analytics_service.calculate_cost(
            provider, model, total_prompt_tokens, total_completion_tokens
        )

        # Drop any per-task permission allowlist and close stray prompts.
        permission_broker.cleanup_task(task.task_id)

        yield {
            "type": "done",
            "task_id": task.task_id,
            "status": task.status,
            "final_answer": accumulated_final_answer,
            "error": agent_error,
            "iterations": iteration,
            "modified_files": task.modified_files,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            **_duration_fields(duration),
            "tokens_per_sec": round(total_completion_tokens / max(0.01, duration), 1),
            "estimated_cost": estimated_cost
        }

        # Clean up active task reference
        if task.task_id in self.active_tasks:
            del self.active_tasks[task.task_id]

agent_orchestrator = AgentOrchestrator()
