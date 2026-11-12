import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.database import db

AGENTS_MD_TEMPLATE = """# Project Guidelines for AI Agents

## Overview
Describe the purpose and architecture of this project here.

## Build, Test & Run Commands
- Run: `python main.py`
- Test: `pytest` or `python -m unittest`

## Code Style & Guidelines
- Follow standard project conventions.
- Inspect files before modifying them.
- Verify changes by running tests or executing scripts.
"""

class ProjectService:
    """
    Manages Antigravity-style projects, workspace directory resolution,
    and project instruction files (AGENTS.md).
    """

    def __init__(self):
        self._active_project_id: Optional[str] = None

    def get_active_project(self) -> Optional[Dict[str, Any]]:
        if not self._active_project_id:
            # Check most recently opened project
            projects = db.list_projects()
            if projects:
                self._active_project_id = projects[0]["id"]
                return projects[0]
            return None
        return db.get_project(self._active_project_id)

    def set_active_project(self, project_id: Optional[str]) -> Optional[Dict[str, Any]]:
        self._active_project_id = project_id
        if project_id:
            proj = db.get_project(project_id)
            if proj:
                db.update_project(project_id, touch_opened=True)
                return proj
        return None

    def close_active_project(self):
        self._active_project_id = None

    def list_projects(self) -> List[Dict[str, Any]]:
        return db.list_projects()

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        return db.get_project(project_id)

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        path: Optional[str] = None,
        instructions: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        success = db.update_project(project_id, name=name, path=path, instructions=instructions)
        if not success:
            return None
        proj = db.get_project(project_id)
        if proj and instructions is not None:
            # Sync instructions to AGENTS.md in the project directory
            try:
                agents_md = Path(proj["path"]) / "AGENTS.md"
                with open(agents_md, "w", encoding="utf-8") as f:
                    f.write(instructions)
            except Exception:
                pass
        return proj

    def delete_project(self, project_id: str) -> bool:
        if self._active_project_id == project_id:
            self._active_project_id = None
        return db.delete_project(project_id)

    def open_or_create_project(self, path_str: str, name: Optional[str] = None, instructions: Optional[str] = None, set_active: bool = True) -> Dict[str, Any]:
        """
        Opens an existing folder as a project, or creates the folder if it does not exist.
        Registers the project in the database and ensures AGENTS.md exists or is scanned.
        """
        p = Path(path_str).resolve()
        p.mkdir(parents=True, exist_ok=True)

        proj_name = name.strip() if name and name.strip() else p.name
        if not proj_name:
            proj_name = "Untitled Project"

        existing = db.get_project_by_path(str(p))
        if existing:
            update_kwargs = {"name": proj_name, "touch_opened": True}
            if instructions is not None:
                update_kwargs["instructions"] = instructions
            db.update_project(existing["id"], **update_kwargs)
            if set_active:
                self._active_project_id = existing["id"]
            return db.get_project(existing["id"])

        # Check for existing AGENTS.md in project root or custom instructions passed
        initial_instructions = instructions or ""
        agents_md = p / "AGENTS.md"
        if not initial_instructions:
            if agents_md.exists() and agents_md.is_file():
                try:
                    with open(agents_md, "r", encoding="utf-8", errors="replace") as f:
                        initial_instructions = f.read()
                except Exception:
                    pass
            else:
                # Create a default AGENTS.md template for the user
                try:
                    with open(agents_md, "w", encoding="utf-8") as f:
                        f.write(AGENTS_MD_TEMPLATE)
                    initial_instructions = AGENTS_MD_TEMPLATE
                except Exception:
                    pass
        else:
            try:
                with open(agents_md, "w", encoding="utf-8") as f:
                    f.write(initial_instructions)
            except Exception:
                pass

        proj = db.create_project(name=proj_name, path=str(p), instructions=initial_instructions)
        if set_active:
            self._active_project_id = proj["id"]
        return proj

    def get_project_agents_instructions(self, target: Any) -> str:
        """
        Reads project-specific instructions from AGENTS.md or .agentrules if present.
        Accepts project_id, project dict, Path, or string path.
        """
        project_path = None
        if isinstance(target, Path):
            project_path = target
        elif isinstance(target, dict) and "path" in target:
            project_path = Path(target["path"])
        elif isinstance(target, str):
            # Check if target is project_id
            proj = db.get_project(target)
            if proj:
                project_path = Path(proj["path"])
            else:
                project_path = Path(target)

        if not project_path or not project_path.exists():
            return ""

        for filename in ("AGENTS.md", "agents.md", ".agentrules", "CLAUDE.md"):
            candidate = project_path / filename
            if candidate.exists() and candidate.is_file():
                try:
                    with open(candidate, "r", encoding="utf-8", errors="replace") as f:
                        return f.read().strip()
                except Exception:
                    pass
        return ""

    def get_project_overview(self, target: Any, max_depth: int = 3, max_entries: int = 60) -> Dict[str, Any]:
        """
        Scans project directory and generates file tree structure and language stats.
        Accepts project_id, project dict, Path, or string path.
        """
        project_path = None
        if isinstance(target, Path):
            project_path = target
        elif isinstance(target, dict) and "path" in target:
            project_path = Path(target["path"])
        elif isinstance(target, str):
            proj = db.get_project(target)
            if proj:
                project_path = Path(proj["path"])
            else:
                project_path = Path(target)

        if not project_path or not project_path.exists() or not project_path.is_dir():
            return {"error": "Invalid project directory"}

        file_tree = []
        extension_counts = {}
        total_files = 0
        total_dirs = 0

        skip_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", ".idea", ".vscode", "dist", "build"}

        for root, dirs, files in os.walk(str(project_path)):
            rel_root = Path(root).relative_to(project_path)
            depth = len(rel_root.parts)
            if depth >= max_depth:
                dirs.clear()
                continue

            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            total_dirs += len(dirs)

            for f in files:
                if f.startswith("."):
                    continue
                total_files += 1
                ext = Path(f).suffix.lower() or "other"
                extension_counts[ext] = extension_counts.get(ext, 0) + 1

                if len(file_tree) < max_entries:
                    rel_p = (rel_root / f) if str(rel_root) != "." else Path(f)
                    file_tree.append(str(rel_p))

        return {
            "root_path": str(project_path),
            "total_files": total_files,
            "total_dirs": total_dirs,
            "file_tree": file_tree,
            "languages": extension_counts
        }

project_service = ProjectService()
