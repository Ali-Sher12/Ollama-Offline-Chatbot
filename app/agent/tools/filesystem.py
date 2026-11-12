"""
Agent Filesystem Tools — Full-power file and directory operations.

Supports:
  • Reading any file on disk (text or with line ranges)
  • Writing, appending, and patching files
  • Glob-based directory listing with metadata
  • Recursive directory trees
  • Regex/text search across files (like ripgrep)
  • File moves, copies, and deletes
  • Symlink creation
  • File stat / metadata inspection
  • Patch application (unified diff format)
"""

import os
import re
import shutil
import fnmatch
import hashlib
import difflib
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.agent.permissions import permission_manager


# ─── Path resolution ───────────────────────────────────────────────────────

def _resolve(path_str: str, allow_outside: bool = True) -> Path:
    """
    Resolve path relative to workspace. Absolute paths are always allowed.
    """
    workspace = permission_manager.get_workspace_dir()
    p = Path(path_str)
    if p.is_absolute():
        return p.resolve()
    return (workspace / p).resolve()


# ─── List / Explore ────────────────────────────────────────────────────────

def list_files(
    directory: str = ".",
    pattern: Optional[str] = None,
    recursive: bool = False,
    max_results: int = 500,
    show_hidden: bool = False,
) -> Dict[str, Any]:
    """
    List files and directories. Works with any path on disk.

    Parameters
    ----------
    directory   : Directory to list. Relative paths resolve from workspace root.
    pattern     : Optional glob filter (e.g. '*.py', '*.md').
    recursive   : If True, walk subdirectories.
    max_results : Maximum number of entries to return (default 500).
    show_hidden : Include hidden files/directories (default False).
    """
    try:
        dir_path = _resolve(directory)
        if not dir_path.exists():
            return {"success": False, "error": f"Directory '{directory}' does not exist", "files": []}
        if not dir_path.is_dir():
            return {"success": False, "error": f"'{directory}' is a file, not a directory", "files": []}

        results = []
        skip_dirs = {"__pycache__", "node_modules", ".git"}

        def _add(p: Path, rel_base: Path):
            name = p.name
            if not show_hidden and name.startswith("."):
                return
            is_dir = p.is_dir()
            try:
                size = p.stat().st_size if not is_dir else 0
                mtime = round(p.stat().st_mtime)
            except OSError:
                size, mtime = 0, 0
            try:
                rel_p = str(p.relative_to(rel_base))
            except ValueError:
                rel_p = str(p)
            if pattern and not fnmatch.fnmatch(name, pattern) and not fnmatch.fnmatch(rel_p, pattern):
                return
            results.append({
                "name": name,
                "path": rel_p,
                "is_dir": is_dir,
                "size_bytes": size,
                "modified": mtime,
            })

        if recursive:
            for root, dirs, files in os.walk(str(dir_path)):
                if not show_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".") and d not in skip_dirs]
                for name in sorted(dirs) + sorted(files):
                    full_p = Path(root) / name
                    _add(full_p, dir_path)
                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break
        else:
            for item in sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                _add(item, dir_path)
                if len(results) >= max_results:
                    break

        return {
            "success": True,
            "directory": str(dir_path),
            "count": len(results),
            "truncated": len(results) >= max_results,
            "files": results,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "files": []}


def tree(directory: str = ".", max_depth: int = 4, max_entries: int = 300) -> Dict[str, Any]:
    """
    Return a tree-view of a directory (like the `tree` command).

    Parameters
    ----------
    directory  : Root directory. Relative to workspace if not absolute.
    max_depth  : Maximum depth to traverse (default 4).
    max_entries: Maximum total nodes to include.
    """
    try:
        root = _resolve(directory)
        if not root.exists():
            return {"success": False, "error": f"Path '{directory}' does not exist"}
        lines = []
        total = [0]
        skip_dirs = {"__pycache__", "node_modules", ".git", ".venv", "venv"}

        def _walk(path: Path, prefix: str, depth: int):
            if depth > max_depth or total[0] >= max_entries:
                return
            try:
                children = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except PermissionError:
                return
            for i, child in enumerate(children):
                if child.name.startswith(".") and child.name not in [".env", ".gitignore"]:
                    continue
                connector = "└── " if i == len(children) - 1 else "├── "
                suffix = "/" if child.is_dir() else ""
                lines.append(f"{prefix}{connector}{child.name}{suffix}")
                total[0] += 1
                if child.is_dir() and child.name not in skip_dirs:
                    extension = "    " if i == len(children) - 1 else "│   "
                    _walk(child, prefix + extension, depth + 1)

        lines.append(f"{root.name}/")
        _walk(root, "", 1)

        return {
            "success": True,
            "root": str(root),
            "tree": "\n".join(lines),
            "node_count": total[0],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Read ──────────────────────────────────────────────────────────────────

def read_file(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """
    Read a text file (optionally a line range).

    Parameters
    ----------
    path       : File path (absolute, or relative to workspace).
    start_line : 1-indexed first line to return (inclusive).
    end_line   : 1-indexed last line to return (inclusive).
    encoding   : File encoding (default utf-8).
    """
    try:
        file_path = _resolve(path)
        if not file_path.exists():
            return {"success": False, "error": f"File '{path}' does not exist"}
        if file_path.is_dir():
            return {"success": False, "error": f"'{path}' is a directory — use list_files or tree instead"}

        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            lines = f.readlines()

        total = len(lines)
        s = max(1, start_line) if start_line else 1
        e = min(total, end_line) if end_line else total

        content = "".join(lines[s - 1:e])
        return {
            "success": True,
            "path": str(file_path),
            "total_lines": total,
            "start_line": s,
            "end_line": e,
            "content": content,
        }
    except Exception as ex:
        return {"success": False, "error": str(ex)}


def stat_file(path: str) -> Dict[str, Any]:
    """
    Return metadata for a file or directory (size, permissions, timestamps).
    """
    try:
        p = _resolve(path)
        if not p.exists():
            return {"success": False, "error": f"Path '{path}' does not exist"}
        st = p.stat()
        return {
            "success": True,
            "path": str(p),
            "is_dir": p.is_dir(),
            "is_file": p.is_file(),
            "is_symlink": p.is_symlink(),
            "size_bytes": st.st_size,
            "permissions": oct(st.st_mode),
            "modified": st.st_mtime,
            "created": st.st_ctime,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Write / Create ────────────────────────────────────────────────────────

def write_file(
    path: str,
    content: str,
    overwrite: bool = True,
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """
    Write (create or overwrite) a text file. Parent directories are created automatically.
    """
    try:
        file_path = _resolve(path)
        if file_path.exists() and not overwrite:
            return {"success": False, "error": f"'{path}' already exists. Set overwrite=True to replace it."}

        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)

        return {
            "success": True,
            "path": str(file_path),
            "bytes_written": len(content.encode(encoding)),
            "lines_written": len(content.splitlines()),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def append_file(path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    Append text to the end of a file. Creates the file if it doesn't exist.
    """
    try:
        file_path = _resolve(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "a", encoding=encoding) as f:
            f.write(content)
        return {"success": True, "path": str(file_path), "bytes_appended": len(content.encode(encoding))}
    except Exception as e:
        return {"success": False, "error": str(e)}


def edit_file(
    path: str,
    target_text: str,
    replacement_text: str,
    allow_multiple: bool = False,
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """
    Replace exact text in a file (find-and-replace). The match is literal, not regex.

    If the target text occurs multiple times and allow_multiple is False, the tool
    returns an error so you can narrow down the context.
    """
    try:
        file_path = _resolve(path)
        if not file_path.exists():
            return {"success": False, "error": f"File '{path}' does not exist"}

        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            current = f.read()

        count = current.count(target_text)
        if count == 0:
            # Try to give a helpful diff-like hint
            return {
                "success": False,
                "error": (
                    f"target_text not found verbatim in '{path}'. "
                    "Check whitespace and line endings. "
                    "Use read_file to verify the exact text."
                ),
            }
        if count > 1 and not allow_multiple:
            return {
                "success": False,
                "error": (
                    f"Found {count} occurrences of target_text in '{path}'. "
                    "Set allow_multiple=True to replace all, or add more surrounding context."
                ),
            }

        new_content = current.replace(target_text, replacement_text, None if allow_multiple else 1)
        with open(file_path, "w", encoding=encoding) as f:
            f.write(new_content)

        return {"success": True, "path": str(file_path), "replacements_made": count if allow_multiple else 1}
    except Exception as e:
        return {"success": False, "error": str(e)}


def insert_lines(
    path: str,
    after_line: int,
    content: str,
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """
    Insert lines into a file after a specific 1-indexed line number.
    Use after_line=0 to insert at the beginning of the file.
    """
    try:
        file_path = _resolve(path)
        if not file_path.exists():
            return {"success": False, "error": f"File '{path}' does not exist"}

        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            lines = f.readlines()

        insert_at = max(0, min(after_line, len(lines)))
        new_lines = content if content.endswith("\n") else content + "\n"
        lines.insert(insert_at, new_lines)

        with open(file_path, "w", encoding=encoding) as f:
            f.writelines(lines)

        return {
            "success": True,
            "path": str(file_path),
            "inserted_after_line": after_line,
            "total_lines": len(lines),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def apply_patch(path: str, patch: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    Apply a unified diff patch to a file.

    The patch string should be in standard unified diff format (as produced by `diff -u`).
    """
    try:
        file_path = _resolve(path)
        if not file_path.exists():
            return {"success": False, "error": f"File '{path}' does not exist"}

        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            original_lines = f.readlines()

        patch_lines = patch.splitlines(keepends=True)
        result = list(difflib.restore(patch_lines, 2))  # side 2 = "new" version

        with open(file_path, "w", encoding=encoding) as f:
            f.writelines(result)

        return {
            "success": True,
            "path": str(file_path),
            "original_lines": len(original_lines),
            "patched_lines": len(result),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_directory(path: str) -> Dict[str, Any]:
    """Create a directory (and all intermediate parents) if it doesn't already exist."""
    try:
        dir_path = _resolve(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return {"success": True, "path": str(dir_path)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_symlink(target: str, link_path: str) -> Dict[str, Any]:
    """Create a symbolic link at link_path pointing to target."""
    try:
        t = _resolve(target)
        l = _resolve(link_path)
        l.parent.mkdir(parents=True, exist_ok=True)
        if l.exists() or l.is_symlink():
            l.unlink()
        l.symlink_to(t)
        return {"success": True, "link": str(l), "target": str(t)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Move / Copy / Delete ──────────────────────────────────────────────────

def move_file(source: str, destination: str) -> Dict[str, Any]:
    """Move or rename a file or directory."""
    try:
        src = _resolve(source)
        dst = _resolve(destination)
        if not src.exists():
            return {"success": False, "error": f"Source '{source}' does not exist"}
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {"success": True, "from": str(src), "to": str(dst)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def copy_file(source: str, destination: str) -> Dict[str, Any]:
    """Copy a file or directory tree to a new location."""
    try:
        src = _resolve(source)
        dst = _resolve(destination)
        if not src.exists():
            return {"success": False, "error": f"Source '{source}' does not exist"}
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
        else:
            shutil.copy2(str(src), str(dst))
        return {"success": True, "from": str(src), "to": str(dst)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_file(path: str, confirm: bool = False, recursive: bool = False) -> Dict[str, Any]:
    """
    Delete a file or directory.

    Parameters
    ----------
    path      : Path to delete.
    confirm   : Must be True to proceed (safety guard).
    recursive : If True, delete non-empty directories (like rm -rf). Default False.
    """
    if not confirm:
        return {"success": False, "error": "Set confirm=True to confirm deletion."}
    try:
        target = _resolve(path)
        if not target.exists() and not target.is_symlink():
            return {"success": False, "error": f"Path '{path}' does not exist"}
        if target.is_dir() and not target.is_symlink():
            if recursive:
                shutil.rmtree(str(target))
            else:
                try:
                    target.rmdir()
                except OSError:
                    return {"success": False, "error": f"Directory '{path}' is not empty. Set recursive=True to delete it and its contents."}
        else:
            target.unlink()
        return {"success": True, "deleted": str(target)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Search ────────────────────────────────────────────────────────────────

def search_files(
    query: str,
    directory: str = ".",
    file_pattern: Optional[str] = None,
    is_regex: bool = False,
    case_sensitive: bool = False,
    context_lines: int = 0,
    max_matches: int = 200,
    exclude_dirs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Search for text or regex patterns across files (like ripgrep / grep -r).

    Parameters
    ----------
    query          : Search string or regex pattern.
    directory      : Root directory to search.
    file_pattern   : Optional glob file filter (e.g. '*.py').
    is_regex       : Treat query as a regex (default False).
    case_sensitive : Case-sensitive match (default False).
    context_lines  : Number of context lines to include before/after each match.
    max_matches    : Max total matches (default 200).
    exclude_dirs   : Directory names to skip (e.g. ['dist', 'build']).
    """
    try:
        dir_path = _resolve(directory)
        if not dir_path.exists():
            return {"success": False, "error": f"Directory '{directory}' does not exist", "matches": []}

        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(query, flags) if is_regex else None
        skip_dirs = {"__pycache__", "node_modules", ".git", ".venv", "venv"} | set(exclude_dirs or [])

        matches = []

        for root, dirs, files in os.walk(str(dir_path)):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            for filename in sorted(files):
                if file_pattern and not fnmatch.fnmatch(filename, file_pattern):
                    continue
                full_p = Path(root) / filename
                try:
                    with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                        raw_lines = f.readlines()

                    for i, line in enumerate(raw_lines):
                        if is_regex and pattern:
                            matched = bool(pattern.search(line))
                        else:
                            matched = (query if case_sensitive else query.lower()) in (line if case_sensitive else line.lower())

                        if matched:
                            ctx_before = [raw_lines[j].rstrip() for j in range(max(0, i - context_lines), i)]
                            ctx_after  = [raw_lines[j].rstrip() for j in range(i + 1, min(len(raw_lines), i + 1 + context_lines))]
                            matches.append({
                                "file": str(full_p),
                                "line_number": i + 1,
                                "line": line.rstrip()[:300],
                                "context_before": ctx_before,
                                "context_after": ctx_after,
                            })
                            if len(matches) >= max_matches:
                                break
                except Exception:
                    continue
                if len(matches) >= max_matches:
                    break
            if len(matches) >= max_matches:
                break

        return {
            "success": True,
            "query": query,
            "total_matches": len(matches),
            "truncated": len(matches) >= max_matches,
            "matches": matches,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "matches": []}


def file_hash(path: str, algorithm: str = "sha256") -> Dict[str, Any]:
    """Compute the hash (md5/sha1/sha256/sha512) of a file."""
    try:
        p = _resolve(path)
        if not p.exists():
            return {"success": False, "error": f"File '{path}' does not exist"}
        h = hashlib.new(algorithm)
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return {"success": True, "path": str(p), "algorithm": algorithm, "hash": h.hexdigest()}
    except Exception as e:
        return {"success": False, "error": str(e)}
