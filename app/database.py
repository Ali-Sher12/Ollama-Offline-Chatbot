import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from docx import Document

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chatbot.db"

class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                instructions TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                project_id TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
            )
            """)

            # Safe migration: add project_id column if table already exists without it
            cursor.execute("PRAGMA table_info(conversations)")
            cols = [row["name"] for row in cursor.fetchall()]
            if "project_id" not in cols:
                cursor.execute("ALTER TABLE conversations ADD COLUMN project_id TEXT DEFAULT NULL")

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                attachments TEXT,
                search_results TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                duration_sec REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                estimated_cost REAL DEFAULT 0.0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()

    # -------------------------------------------------------------------------
    # Project Management
    # -------------------------------------------------------------------------
    def create_project(self, name: str, path: str, instructions: str = "") -> Dict[str, Any]:
        proj_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO projects (id, name, path, instructions, created_at, updated_at, last_opened_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (proj_id, name, path, instructions, now, now, now)
            )
            conn.commit()
        return {
            "id": proj_id,
            "name": name,
            "path": path,
            "instructions": instructions,
            "created_at": now,
            "updated_at": now,
            "last_opened_at": now
        }

    def list_projects(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*,
                       COUNT(DISTINCT c.id) as conversation_count
                FROM projects p
                LEFT JOIN conversations c ON p.id = c.project_id
                GROUP BY p.id
                ORDER BY p.last_opened_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_project_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE path = ?", (path,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        path: Optional[str] = None,
        instructions: Optional[str] = None,
        touch_opened: bool = False
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        updates = ["updated_at = ?"]
        params = [now]

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if path is not None:
            updates.append("path = ?")
            params.append(path)
        if instructions is not None:
            updates.append("instructions = ?")
            params.append(instructions)
        if touch_opened:
            updates.append("last_opened_at = ?")
            params.append(now)

        params.append(project_id)
        query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            conn.commit()
            return cursor.rowcount > 0

    def delete_project(self, project_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Set project_id to NULL on any associated conversations
            cursor.execute("UPDATE conversations SET project_id = NULL WHERE project_id = ?", (project_id,))
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return cursor.rowcount > 0

    # -------------------------------------------------------------------------
    # Conversations
    # -------------------------------------------------------------------------
    def create_conversation(
        self,
        title: str = "New Chat",
        provider: str = "ollama",
        model: str = "llama3.2:1b",
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        conv_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (id, title, provider, model, project_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (conv_id, title, provider, model, project_id, now, now)
            )
            # If project_id is provided, touch last_opened_at on project
            if project_id:
                cursor.execute("UPDATE projects SET last_opened_at = ?, updated_at = ? WHERE id = ?", (now, now, project_id))
            conn.commit()
        return {
            "id": conv_id,
            "title": title,
            "provider": provider,
            "model": model,
            "project_id": project_id,
            "created_at": now,
            "updated_at": now,
            "messages": []
        }

    def list_conversations(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            base_query = """
                SELECT c.id, c.title, c.provider, c.model, c.project_id, c.created_at, c.updated_at,
                       COUNT(m.id) as message_count,
                       COALESCE(SUM(m.prompt_tokens + m.completion_tokens), 0) as total_tokens
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
            """
            params = []
            if project_id == "all":
                where_clause = ""
            elif project_id is not None:
                where_clause = "WHERE c.project_id = ?"
                params.append(project_id)
            else:
                where_clause = "WHERE c.project_id IS NULL"

            full_query = f"""
                {base_query}
                {where_clause}
                GROUP BY c.id
                ORDER BY c.updated_at DESC
            """
            cursor.execute(full_query, tuple(params))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
            conv = cursor.fetchone()
            if not conv:
                return None
            
            cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conv_id,))
            messages = cursor.fetchall()
            
            msg_list = []
            for msg in messages:
                m = dict(msg)
                m["attachments"] = json.loads(m["attachments"]) if m["attachments"] else []
                m["search_results"] = json.loads(m["search_results"]) if m["search_results"] else []
                msg_list.append(m)

            conv_dict = dict(conv)
            conv_dict["messages"] = msg_list
            return conv_dict

    def update_conversation_title(self, conv_id: str, title: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                           (title, datetime.now(timezone.utc).isoformat(), conv_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_conversation(self, conv_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            conn.commit()
            return cursor.rowcount > 0

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        search_results: Optional[List[Dict[str, Any]]] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        duration_sec: float = 0.0
    ) -> Dict[str, Any]:
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        att_json = json.dumps(attachments or [])
        sr_json = json.dumps(search_results or [])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (id, conversation_id, role, content, attachments, search_results, prompt_tokens, completion_tokens, duration_sec, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (msg_id, conversation_id, role, content, att_json, sr_json, prompt_tokens, completion_tokens, duration_sec, now))

            cursor.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
            conn.commit()

        return {
            "id": msg_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "attachments": attachments or [],
            "search_results": search_results or [],
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "duration_sec": duration_sec,
            "created_at": now
        }

    def record_analytics(
        self,
        conversation_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost: float = 0.0
    ) -> None:
        total = prompt_tokens + completion_tokens
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analytics (conversation_id, provider, model, prompt_tokens, completion_tokens, total_tokens, estimated_cost, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (conversation_id, provider, model, prompt_tokens, completion_tokens, total, estimated_cost, datetime.now(timezone.utc).isoformat()))
            conn.commit()

    def get_analytics_summary(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
                    COALESCE(SUM(total_tokens), 0) as grand_total_tokens,
                    COALESCE(SUM(estimated_cost), 0.0) as total_estimated_cost,
                    COUNT(id) as total_requests
                FROM analytics
            """)
            overall = dict(cursor.fetchone())

            cursor.execute("""
                SELECT model, provider, 
                       SUM(prompt_tokens) as prompt_tokens, 
                       SUM(completion_tokens) as completion_tokens, 
                       SUM(total_tokens) as total_tokens,
                       COUNT(id) as request_count
                FROM analytics
                GROUP BY model, provider
                ORDER BY total_tokens DESC
            """)
            by_model = [dict(row) for row in cursor.fetchall()]

            return {
                "overall": overall,
                "by_model": by_model
            }

    def export_docx(self, conv_id: str, output_dir: Optional[Path] = None) -> Optional[str]:
        conv = self.get_conversation(conv_id)
        if not conv:
            return None
        
        if output_dir is None:
            output_dir = Path(__file__).resolve().parent.parent / "OutWrite Documents"
        output_dir.mkdir(parents=True, exist_ok=True)

        doc = Document()
        doc.add_heading(f"Chat: {conv['title']}", level=0)
        doc.add_paragraph(f"Model: {conv['model']} ({conv['provider']})")
        doc.add_paragraph(f"Exported At: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
        doc.add_paragraph("__________________________________________________________________")

        for msg in conv.get("messages", []):
            role_title = "User" if msg["role"] == "user" else "Assistant"
            doc.add_heading(role_title, level=2)
            
            # Mention attachments if any
            if msg.get("attachments"):
                doc.add_paragraph("Attached Files: " + ", ".join(a.get("filename", "") for a in msg["attachments"]))
            
            # Content
            doc.add_paragraph(msg["content"])
            doc.add_paragraph("__________________________________________________________________")

        timestamp = datetime.now().strftime("%Y-%m-%d_%I-%M-%S_%p")
        safe_title = "".join(c for c in conv['title'] if c.isalnum() or c in (' ', '_', '-')).strip()[:30]
        filename = f"chat_{safe_title}_{timestamp}.docx"
        filepath = output_dir / filename
        doc.save(str(filepath))
        return str(filepath)

db = Database()
