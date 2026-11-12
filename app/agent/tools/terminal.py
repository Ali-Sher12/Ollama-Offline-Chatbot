"""
Agent Terminal Tool — Unrestricted, full-power shell execution.

Supports:
  • Any shell command (bash, python, node, git, docker, ffmpeg, etc.)
  • Long-running commands with configurable timeout (up to 5 minutes)
  • stdin piping (pass input directly to interactive commands)
  • Background process launching and listing
  • Per-command environment variable overrides
  • Auto-detects virtual environments (.venv, venv, conda)
  • Captures stdout + stderr with large buffer support
"""

import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.agent.permissions import permission_manager

# Truly catastrophic patterns — the only hard blocks
CATASTROPHIC_PATTERNS = [
    r"(?i)\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\s+(/|/\*|~/?)\s*$",
    r"(?i)\bmkfs(\.[a-z0-9]+)?\b",
    r"(?i)\bdd\b.+\bof=/dev/(sda|nvme|hda|sdb)\b",
    r":\(\)\s*\{.*:\s*\|.*:\s*&\s*\}",  # fork bomb
    r"(?i)\b(shutdown|poweroff)\s+-[hPrn]",
]

import re as _re

def _is_catastrophic(command: str) -> bool:
    for pat in CATASTROPHIC_PATTERNS:
        if _re.search(pat, command):
            return True
    return False


def _build_env(workspace: Path, extra_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Build an enriched environment with venv / conda awareness."""
    env = os.environ.copy()

    # Inject virtual environment if one exists in workspace
    for venv_candidate in [".venv", "venv", ".env"]:
        venv_bin = workspace / venv_candidate / "bin"
        if venv_bin.exists():
            env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
            env["VIRTUAL_ENV"] = str(workspace / venv_candidate)
            break

    # Merge caller-supplied extras
    if extra_env:
        env.update(extra_env)

    return env


def run_terminal(
    command: str,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    stdin_input: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Execute any shell command and return the full output.

    Parameters
    ----------
    command     : Shell command string (passed to bash -c).
    cwd         : Working directory. Relative paths are resolved from workspace root.
                  Absolute paths outside workspace are allowed.
    timeout     : Max seconds to wait (default 300, max 300 / 5 min).
    stdin_input : Optional text to pipe into the command's stdin.
    env_vars    : Extra environment variables to set for this command only.
    """
    command = (command or "").strip()
    if not command:
        return _error("Command cannot be empty.")

    if _is_catastrophic(command):
        return _error(
            f"Command blocked: matches a catastrophic safety pattern. "
            f"If you need this for a legitimate reason, run a safer variant."
        )

    # Resolve working directory — allow absolute paths outside workspace
    workspace = permission_manager.get_workspace_dir()
    try:
        if cwd:
            work_dir = Path(cwd)
            if not work_dir.is_absolute():
                work_dir = (workspace / work_dir).resolve()
            else:
                work_dir = work_dir.resolve()
            if not work_dir.exists():
                # Try to create it so the agent can mkdir and immediately cd
                work_dir.mkdir(parents=True, exist_ok=True)
        else:
            work_dir = workspace
    except Exception as e:
        return _error(f"Invalid working directory '{cwd}': {e}")

    exec_timeout = _clamp_timeout(timeout)
    env = _build_env(workspace, env_vars)

    start = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,
            executable="/bin/bash",
            cwd=str(work_dir),
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=exec_timeout,
            env=env,
        )
        duration = round(time.time() - start, 2)

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        exit_code = result.returncode
        success = exit_code == 0

        return {
            "success": success,
            "exit_code": exit_code,
            "stdout": _truncate(stdout, 32_000),
            "stderr": _truncate(stderr, 8_000),
            "cwd": str(work_dir),
            "duration_sec": duration,
            "command": command,
            "error": None if success else f"Exit code {exit_code}" + (f"\n{stderr.strip()}" if stderr.strip() else ""),
        }

    except subprocess.TimeoutExpired:
        duration = round(time.time() - start, 2)
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Timed out after {exec_timeout}s",
            "cwd": str(work_dir),
            "duration_sec": duration,
            "command": command,
            "error": f"Command exceeded timeout of {exec_timeout} seconds. Use a larger timeout or break the task into smaller steps.",
        }
    except Exception as e:
        duration = round(time.time() - start, 2)
        return _error(str(e), duration=duration, cwd=str(work_dir), command=command)


def run_script(
    code: str,
    language: str = "python",
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    env_vars: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Write a code snippet to a temporary file and execute it.

    Parameters
    ----------
    code     : Source code to execute.
    language : 'python', 'bash', 'node', 'ruby', 'perl', or 'php'.
    cwd      : Working directory.
    timeout  : Execution timeout in seconds.
    env_vars : Extra environment variables.
    """
    import tempfile

    lang_map = {
        "python": ("python3", ".py"),
        "bash":   ("bash",    ".sh"),
        "node":   ("node",    ".js"),
        "javascript": ("node", ".js"),
        "ruby":   ("ruby",   ".rb"),
        "perl":   ("perl",   ".pl"),
        "php":    ("php",    ".php"),
    }
    lang = language.lower().strip()
    interpreter, ext = lang_map.get(lang, ("python3", ".py"))

    with tempfile.NamedTemporaryFile(
        suffix=ext, mode="w", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        return run_terminal(
            command=f"{interpreter} {tmp_path}",
            cwd=cwd,
            timeout=timeout,
            env_vars=env_vars,
        )
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def read_binary_file(path: str) -> Dict[str, Any]:
    """
    Read a binary file and return its contents as a base64-encoded string.
    Useful for inspecting images, compiled artifacts, etc.
    """
    try:
        import base64
        file_path = permission_manager.resolve_safe_path(path, allow_outside=True)
        if not file_path.exists():
            return {"success": False, "error": f"File '{path}' does not exist"}
        size = file_path.stat().st_size
        with open(file_path, "rb") as f:
            data = f.read()
        return {
            "success": True,
            "path": str(file_path),
            "size_bytes": size,
            "encoding": "base64",
            "content": base64.b64encode(data).decode("ascii"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_binary_file(path: str, content_base64: str) -> Dict[str, Any]:
    """
    Write a base64-encoded blob to a file.
    Useful for creating binary artifacts (images, zips, etc.)
    """
    try:
        import base64
        file_path = permission_manager.resolve_safe_path(path, allow_outside=False)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        data = base64.b64decode(content_base64)
        with open(file_path, "wb") as f:
            f.write(data)
        return {"success": True, "path": str(file_path), "bytes_written": len(data)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Background process management ──────────────────────────────────────────

_background_procs: Dict[str, Dict[str, Any]] = {}
_bg_lock = threading.Lock()


def start_background_process(
    command: str,
    cwd: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Launch a long-running process in the background (e.g. a dev server).
    Returns immediately with a process_id you can use to check status or kill it.
    """
    if _is_catastrophic(command):
        return _error("Command blocked: catastrophic safety pattern.")

    workspace = permission_manager.get_workspace_dir()
    work_dir = Path(cwd).resolve() if cwd else workspace
    env = _build_env(workspace, env_vars)
    pid_key = f"bg_{int(time.time() * 1000)}"

    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            executable="/bin/bash",
            cwd=str(work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        with _bg_lock:
            _background_procs[pid_key] = {
                "process_id": pid_key,
                "pid": proc.pid,
                "command": command,
                "label": label or command[:60],
                "cwd": str(work_dir),
                "started_at": time.time(),
                "proc": proc,
                "output_lines": [],
                "status": "running",
            }

        # Drain output in background thread
        def _drain(entry):
            proc_ref = entry["proc"]
            try:
                for line in proc_ref.stdout:
                    with _bg_lock:
                        entry["output_lines"].append(line.rstrip())
                        if len(entry["output_lines"]) > 2000:
                            entry["output_lines"] = entry["output_lines"][-2000:]
            except Exception:
                pass
            with _bg_lock:
                entry["status"] = "finished" if proc_ref.returncode == 0 else "exited"

        with _bg_lock:
            entry = _background_procs[pid_key]
        t = threading.Thread(target=_drain, args=(entry,), daemon=True)
        t.start()

        return {
            "success": True,
            "process_id": pid_key,
            "pid": proc.pid,
            "command": command,
            "cwd": str(work_dir),
            "message": "Process started in background. Use get_background_process_output() to read its output.",
        }
    except Exception as e:
        return _error(str(e))


def get_background_process_output(process_id: str, last_n_lines: int = 100) -> Dict[str, Any]:
    """Check the status and recent output of a background process."""
    with _bg_lock:
        entry = _background_procs.get(process_id)
    if not entry:
        return {"success": False, "error": f"No background process with id '{process_id}'"}

    proc: subprocess.Popen = entry["proc"]
    exit_code = proc.poll()
    status = "running" if exit_code is None else ("finished" if exit_code == 0 else f"exited:{exit_code}")

    with _bg_lock:
        lines = entry["output_lines"][-last_n_lines:]

    return {
        "success": True,
        "process_id": process_id,
        "pid": entry["pid"],
        "command": entry["command"],
        "status": status,
        "exit_code": exit_code,
        "output": "\n".join(lines),
        "uptime_sec": round(time.time() - entry["started_at"], 1),
    }


def kill_background_process(process_id: str) -> Dict[str, Any]:
    """Kill a running background process."""
    with _bg_lock:
        entry = _background_procs.get(process_id)
    if not entry:
        return {"success": False, "error": f"No background process with id '{process_id}'"}

    proc: subprocess.Popen = entry["proc"]
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

    with _bg_lock:
        _background_procs.pop(process_id, None)

    return {"success": True, "process_id": process_id, "message": "Process terminated."}


def list_background_processes() -> Dict[str, Any]:
    """List all running background processes."""
    with _bg_lock:
        procs = [
            {
                "process_id": k,
                "pid": v["pid"],
                "label": v["label"],
                "command": v["command"],
                "status": v["status"],
                "uptime_sec": round(time.time() - v["started_at"], 1),
            }
            for k, v in _background_procs.items()
        ]
    return {"success": True, "count": len(procs), "processes": procs}


# ── Helpers ────────────────────────────────────────────────────────────────

def _clamp_timeout(requested: Optional[int]) -> int:
    if requested and requested > 0:
        return min(int(requested), 300)   # up to 5 minutes
    return 300  # default: 5 minutes


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + f"\n\n... [{len(text) - limit} characters truncated] ...\n\n" + text[-half:]


def _error(msg: str, duration: float = 0.0, cwd: str = "", command: str = "") -> Dict[str, Any]:
    return {
        "success": False,
        "exit_code": -1,
        "stdout": "",
        "stderr": msg,
        "cwd": cwd,
        "duration_sec": duration,
        "command": command,
        "error": msg,
    }
