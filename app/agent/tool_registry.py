"""
Agent Tool Registry — registers all tools available to the agent.

Every tool is described by a JSON-schema definition so the LLM can invoke them
through the standard OpenAI-compatible tool-call interface.
"""

import json
import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    tags: List[str] = field(default_factory=list)


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()

    # ── Registration ───────────────────────────────────────────────────────

    def register(self, name: str, description: str, parameters: Dict[str, Any],
                  handler: Callable, tags: Optional[List[str]] = None) -> None:
        self._tools[name] = ToolDefinition(
            name=name, description=description,
            parameters=parameters, handler=handler,
            tags=tags or [],
        )
        logger.debug("Registered tool: %s", name)

    # ── Retrieval ──────────────────────────────────────────────────────────

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    # ── Execution ──────────────────────────────────────────────────────────

    def execute_tool(self, name: str, arguments: Any) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"success": False, "error": f"Unknown tool: '{name}'"}

        try:
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except Exception:
                    arguments = {}
            if not isinstance(arguments, dict):
                arguments = {}

            sig = inspect.signature(tool.handler)
            valid_kwargs: Dict[str, Any] = {}
            missing_required: List[str] = []

            for param_name, param in sig.parameters.items():
                if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    continue
                if param_name in arguments:
                    valid_kwargs[param_name] = arguments[param_name]
                elif param.default is inspect.Parameter.empty:
                    missing_required.append(param_name)

            if missing_required:
                return {
                    "success": False,
                    "error": (
                        f"Tool '{name}' is missing required parameter(s): "
                        f"{', '.join(missing_required)}. "
                        f"Arguments received: {list(arguments.keys())}"
                    ),
                }

            return tool.handler(**valid_kwargs)

        except Exception as e:
            logger.exception("Error executing tool '%s': %s", name, e)
            return {"success": False, "error": f"Execution error in tool '{name}': {str(e)}"}

    # ── Default Tools ──────────────────────────────────────────────────────

    def _register_default_tools(self) -> None:
        from app.agent.tools.filesystem import (
            list_files, tree, read_file, stat_file,
            write_file, append_file, edit_file, insert_lines, apply_patch,
            create_directory, create_symlink,
            move_file, copy_file, delete_file,
            search_files, file_hash,
        )
        from app.agent.tools.terminal import (
            run_terminal, run_script,
            start_background_process, get_background_process_output,
            kill_background_process, list_background_processes,
            read_binary_file, write_binary_file,
        )
        from app.agent.tools.docx_tools import manage_docx
        from app.agent.tools.image_tools import analyze_image

        # ── Terminal ───────────────────────────────────────────────────────

        self.register(
            name="run_terminal",
            description=(
                "Execute any shell command (bash, python, node, git, docker, pip, npm, make, ffmpeg, etc.) "
                "in the workspace or any directory. Captures stdout, stderr, and exit code. "
                "Use this for installing packages, running tests, compiling code, managing files via CLI, "
                "interacting with git, and anything else that requires the shell. "
                "For long-running tasks use a large timeout. For interactive commands that need stdin, "
                "pass the input via stdin_input."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command":     {"type": "string",  "description": "Shell command to execute (runs in bash)."},
                    "cwd":         {"type": "string",  "description": "Working directory (absolute or relative to workspace). Created if it doesn't exist."},
                    "timeout":     {"type": "integer", "description": "Max execution time in seconds (default 120, max 1800)."},
                    "stdin_input": {"type": "string",  "description": "Text to pipe into the command's stdin (for prompts/interactive tools)."},
                    "env_vars":    {"type": "object",  "description": "Extra environment variables {KEY: VALUE} for this command only.",
                                    "additionalProperties": {"type": "string"}},
                },
                "required": ["command"],
            },
            handler=run_terminal,
            tags=["terminal"],
        )

        self.register(
            name="run_script",
            description=(
                "Write a code snippet to a temporary file and execute it. "
                "Supports Python, Bash, Node.js, Ruby, Perl, and PHP. "
                "Great for one-off data transformations, quick calculations, or test scripts."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "code":      {"type": "string", "description": "Source code to execute."},
                    "language":  {"type": "string", "enum": ["python", "bash", "node", "javascript", "ruby", "perl", "php"],
                                  "description": "Language to use (default python)."},
                    "cwd":       {"type": "string", "description": "Working directory."},
                    "timeout":   {"type": "integer", "description": "Max execution time in seconds."},
                    "env_vars":  {"type": "object", "description": "Extra environment variables.",
                                  "additionalProperties": {"type": "string"}},
                },
                "required": ["code"],
            },
            handler=run_script,
            tags=["terminal"],
        )

        self.register(
            name="start_background_process",
            description=(
                "Start a long-running process in the background (e.g. a dev server, watcher, or build daemon). "
                "Returns a process_id immediately — use get_background_process_output() to read its output."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command":   {"type": "string", "description": "Command to run in background."},
                    "cwd":       {"type": "string", "description": "Working directory."},
                    "env_vars":  {"type": "object", "description": "Extra environment variables.",
                                  "additionalProperties": {"type": "string"}},
                    "label":     {"type": "string", "description": "Human-readable label for this process."},
                },
                "required": ["command"],
            },
            handler=start_background_process,
            tags=["terminal"],
        )

        self.register(
            name="get_background_process_output",
            description="Read the status and recent output of a background process started with start_background_process.",
            parameters={
                "type": "object",
                "properties": {
                    "process_id":   {"type": "string",  "description": "Process ID returned by start_background_process."},
                    "last_n_lines": {"type": "integer", "description": "How many tail lines to return (default 100)."},
                },
                "required": ["process_id"],
            },
            handler=get_background_process_output,
            tags=["terminal"],
        )

        self.register(
            name="kill_background_process",
            description="Terminate a background process by its process_id.",
            parameters={
                "type": "object",
                "properties": {
                    "process_id": {"type": "string", "description": "Process ID to kill."},
                },
                "required": ["process_id"],
            },
            handler=kill_background_process,
            tags=["terminal"],
        )

        self.register(
            name="list_background_processes",
            description="List all currently running background processes and their status.",
            parameters={"type": "object", "properties": {}},
            handler=list_background_processes,
            tags=["terminal"],
        )

        # ── Filesystem ─────────────────────────────────────────────────────

        self.register(
            name="list_files",
            description=(
                "List files and directories. Supports any path on disk — absolute or relative to workspace. "
                "Use pattern for glob filtering (e.g. '*.py'). Use recursive=True for deep traversal."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "directory":    {"type": "string",  "description": "Directory to list (default: workspace root)."},
                    "pattern":      {"type": "string",  "description": "Glob filter, e.g. '*.py' or '*.md'."},
                    "recursive":    {"type": "boolean", "description": "Walk subdirectories (default false)."},
                    "max_results":  {"type": "integer", "description": "Max entries to return (default 500)."},
                    "show_hidden":  {"type": "boolean", "description": "Include hidden files/dirs (default false)."},
                },
                "required": [],
            },
            handler=list_files,
            tags=["filesystem"],
        )

        self.register(
            name="tree",
            description=(
                "Display a directory tree (like the `tree` command). "
                "Great for understanding project structure at a glance."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "directory":   {"type": "string",  "description": "Root directory (default: workspace)."},
                    "max_depth":   {"type": "integer", "description": "Maximum depth (default 4)."},
                    "max_entries": {"type": "integer", "description": "Maximum nodes to display (default 300)."},
                },
                "required": [],
            },
            handler=tree,
            tags=["filesystem"],
        )

        self.register(
            name="read_file",
            description=(
                "Read the contents of any text file (source code, config, markdown, logs, etc.). "
                "Optionally specify start_line/end_line for large files."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path":       {"type": "string",  "description": "File path (absolute or relative to workspace)."},
                    "start_line": {"type": "integer", "description": "1-indexed first line to return."},
                    "end_line":   {"type": "integer", "description": "1-indexed last line to return."},
                    "encoding":   {"type": "string",  "description": "File encoding (default utf-8)."},
                },
                "required": ["path"],
            },
            handler=read_file,
            tags=["filesystem"],
        )

        self.register(
            name="stat_file",
            description="Get metadata for a file or directory: size, permissions, timestamps.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to inspect."},
                },
                "required": ["path"],
            },
            handler=stat_file,
            tags=["filesystem"],
        )

        self.register(
            name="write_file",
            description=(
                "Create a new file or overwrite an existing file with the given content. "
                "Parent directories are created automatically. "
                "ALWAYS read the existing file first (read_file) before overwriting it."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path":      {"type": "string",  "description": "Target file path."},
                    "content":   {"type": "string",  "description": "Full text content to write."},
                    "overwrite": {"type": "boolean", "description": "Allow overwriting existing files (default true)."},
                    "encoding":  {"type": "string",  "description": "File encoding (default utf-8)."},
                },
                "required": ["path", "content"],
            },
            handler=write_file,
            tags=["filesystem"],
        )

        self.register(
            name="append_file",
            description="Append text to the end of a file. Creates the file if it doesn't exist.",
            parameters={
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "Target file path."},
                    "content": {"type": "string", "description": "Text to append."},
                },
                "required": ["path", "content"],
            },
            handler=append_file,
            tags=["filesystem"],
        )

        self.register(
            name="edit_file",
            description=(
                "Replace an exact block of text in a file (find-and-replace). "
                "The target_text must match the file content exactly, including whitespace and indentation. "
                "Always use read_file first to get the precise text. "
                "If the target text occurs multiple times, set allow_multiple=True to replace all, "
                "or add more context lines to make it unique."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path":             {"type": "string",  "description": "File to edit."},
                    "target_text":      {"type": "string",  "description": "Exact existing text to find (literal, not regex)."},
                    "replacement_text": {"type": "string",  "description": "Text to replace it with."},
                    "allow_multiple":   {"type": "boolean", "description": "Replace all occurrences if true (default false)."},
                    "encoding":         {"type": "string",  "description": "File encoding (default utf-8)."},
                },
                "required": ["path", "target_text", "replacement_text"],
            },
            handler=edit_file,
            tags=["filesystem"],
        )

        self.register(
            name="insert_lines",
            description=(
                "Insert text into a file after a specific line number. "
                "Use after_line=0 to insert at the top of the file."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path":        {"type": "string",  "description": "File to edit."},
                    "after_line":  {"type": "integer", "description": "1-indexed line number to insert after (0 = beginning)."},
                    "content":     {"type": "string",  "description": "Text to insert (a newline is added if missing)."},
                },
                "required": ["path", "after_line", "content"],
            },
            handler=insert_lines,
            tags=["filesystem"],
        )

        self.register(
            name="apply_patch",
            description=(
                "Apply a unified diff patch to a file. "
                "The patch must be in standard unified diff format (output of `diff -u`)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path":  {"type": "string", "description": "File to patch."},
                    "patch": {"type": "string", "description": "Unified diff patch string."},
                },
                "required": ["path", "patch"],
            },
            handler=apply_patch,
            tags=["filesystem"],
        )

        self.register(
            name="create_directory",
            description="Create a directory (and all parent directories) if it doesn't already exist.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to create."},
                },
                "required": ["path"],
            },
            handler=create_directory,
            tags=["filesystem"],
        )

        self.register(
            name="create_symlink",
            description="Create a symbolic link.",
            parameters={
                "type": "object",
                "properties": {
                    "target":    {"type": "string", "description": "Path the symlink points to."},
                    "link_path": {"type": "string", "description": "Path where the symlink will be created."},
                },
                "required": ["target", "link_path"],
            },
            handler=create_symlink,
            tags=["filesystem"],
        )

        self.register(
            name="move_file",
            description="Move or rename a file or directory.",
            parameters={
                "type": "object",
                "properties": {
                    "source":      {"type": "string", "description": "Current path."},
                    "destination": {"type": "string", "description": "New path."},
                },
                "required": ["source", "destination"],
            },
            handler=move_file,
            tags=["filesystem"],
        )

        self.register(
            name="copy_file",
            description="Copy a file or directory tree to a new location.",
            parameters={
                "type": "object",
                "properties": {
                    "source":      {"type": "string", "description": "Source path."},
                    "destination": {"type": "string", "description": "Destination path."},
                },
                "required": ["source", "destination"],
            },
            handler=copy_file,
            tags=["filesystem"],
        )

        self.register(
            name="delete_file",
            description=(
                "Delete a file or directory. "
                "Set confirm=True to confirm. "
                "Set recursive=True to delete a non-empty directory and all its contents."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path":      {"type": "string",  "description": "Path to delete."},
                    "confirm":   {"type": "boolean", "description": "Must be true to proceed."},
                    "recursive": {"type": "boolean", "description": "Delete non-empty directories (default false)."},
                },
                "required": ["path", "confirm"],
            },
            handler=delete_file,
            tags=["filesystem"],
        )

        self.register(
            name="search_files",
            description=(
                "Search for text or regex patterns across files in a directory (like ripgrep). "
                "Supports context lines, case sensitivity, file filtering, and directory exclusion."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query":          {"type": "string",  "description": "Text or regex pattern to search for."},
                    "directory":      {"type": "string",  "description": "Root directory to search (default: workspace)."},
                    "file_pattern":   {"type": "string",  "description": "Glob filter for filenames, e.g. '*.py'."},
                    "is_regex":       {"type": "boolean", "description": "Treat query as regex (default false)."},
                    "case_sensitive": {"type": "boolean", "description": "Case-sensitive match (default false)."},
                    "context_lines":  {"type": "integer", "description": "Lines of context around each match (default 0)."},
                    "max_matches":    {"type": "integer", "description": "Max total matches to return (default 200)."},
                    "exclude_dirs":   {"type": "array",   "items": {"type": "string"},
                                       "description": "Directory names to skip."},
                },
                "required": ["query"],
            },
            handler=search_files,
            tags=["filesystem"],
        )

        self.register(
            name="file_hash",
            description="Compute the cryptographic hash (md5/sha1/sha256/sha512) of a file.",
            parameters={
                "type": "object",
                "properties": {
                    "path":      {"type": "string", "description": "File to hash."},
                    "algorithm": {"type": "string", "enum": ["md5", "sha1", "sha256", "sha512"],
                                  "description": "Hash algorithm (default sha256)."},
                },
                "required": ["path"],
            },
            handler=file_hash,
            tags=["filesystem"],
        )

        self.register(
            name="read_binary_file",
            description="Read a binary file and return its content as a base64-encoded string. Useful for inspecting compiled artifacts, images, zip files, etc.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the binary file."},
                },
                "required": ["path"],
            },
            handler=read_binary_file,
            tags=["filesystem"],
        )

        self.register(
            name="write_binary_file",
            description="Write a base64-encoded blob to a file. Useful for creating binary files from data the LLM has in memory.",
            parameters={
                "type": "object",
                "properties": {
                    "path":           {"type": "string", "description": "Destination file path."},
                    "content_base64": {"type": "string", "description": "Base64-encoded binary content."},
                },
                "required": ["path", "content_base64"],
            },
            handler=write_binary_file,
            tags=["filesystem"],
        )

        # ── Documents ──────────────────────────────────────────────────────

        self.register(
            name="manage_docx",
            description=(
                "Read, create, and modify Microsoft Word (.docx) documents. "
                "Actions: 'read', 'create', 'add_paragraph', 'modify_paragraph', "
                "'add_table', 'modify_table', 'replace_text', 'add_heading', 'add_image'."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action":       {"type": "string",
                                     "enum": ["read", "create", "add_paragraph", "modify_paragraph",
                                              "add_table", "modify_table", "replace_text", "add_heading", "add_image"],
                                     "description": "Operation to perform."},
                    "file_path":    {"type": "string", "description": "Path to the .docx file."},
                    "output_path":  {"type": "string", "description": "Output path when creating a new document."},
                    "text":         {"type": "string", "description": "Text content for add/modify operations."},
                    "heading_level":{"type": "integer","description": "Heading level 1–9 for add_heading."},
                    "paragraph_index": {"type": "integer", "description": "Zero-based paragraph index."},
                    "target_text":  {"type": "string", "description": "Text to find for replace_text."},
                    "replacement_text": {"type": "string", "description": "Replacement text."},
                    "table_data":   {"type": "array", "items": {"type": "array"},
                                     "description": "2D array of cell values for tables."},
                    "table_index":  {"type": "integer", "description": "Zero-based table index."},
                    "image_path":   {"type": "string", "description": "Path to an image to embed."},
                    "style":        {"type": "string", "description": "Paragraph or character style name."},
                },
                "required": ["action", "file_path"],
            },
            handler=manage_docx,
            tags=["documents"],
        )

        # ── Vision ─────────────────────────────────────────────────────────

        self.register(
            name="analyze_image",
            description=(
                "Analyze an image file using a vision-capable LLM. "
                "Modes: 'describe' (general description), 'ocr' (extract text), "
                "'chart_graph' (interpret charts/graphs), 'diagram' (trace flowcharts/UML)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "image_path":  {"type": "string", "description": "Path to the image file."},
                    "mode":        {"type": "string",
                                    "enum": ["describe", "ocr", "chart_graph", "diagram"],
                                    "description": "Analysis mode (default 'describe')."},
                    "prompt":      {"type": "string", "description": "Custom prompt to guide analysis."},
                },
                "required": ["image_path"],
            },
            handler=analyze_image,
            tags=["vision"],
        )


tool_registry = ToolRegistry()
