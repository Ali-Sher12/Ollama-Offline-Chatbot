import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import db
from app.services.project_service import project_service
from app.services.llm_service import llm_service
from app.agent.permissions import permission_manager
from app.agent.orchestrator import agent_orchestrator
from app.server import app


class TestProjectSystem(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.temp_dir = tempfile.mkdtemp(prefix="ollama_test_proj_")
        self.proj_path = Path(self.temp_dir) / "test_app"
        self.proj_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        permission_manager.set_active_workspace(None)
        project_service.close_active_project()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. Project Creation, AGENTS.md, Overview & CRUD
    # -------------------------------------------------------------------------
    def test_project_service_open_and_agents_md(self):
        # Open or create project
        proj = project_service.open_or_create_project(
            path_str=str(self.proj_path),
            name="My Test App"
        )
        self.assertIsNotNone(proj)
        self.assertEqual(proj["name"], "My Test App")
        self.assertEqual(proj["path"], str(self.proj_path.resolve()))

        # Check AGENTS.md was automatically generated
        agents_md = self.proj_path / "AGENTS.md"
        self.assertTrue(agents_md.exists())
        content = agents_md.read_text(encoding="utf-8")
        self.assertIn("# Project Guidelines for AI Agents", content)

        # Instructions retrieval
        instructions = project_service.get_project_agents_instructions(proj["id"])
        self.assertIn("# Project Guidelines for AI Agents", instructions)

        # Add a couple of files to test overview
        (self.proj_path / "main.py").write_text("print('hello')", encoding="utf-8")
        (self.proj_path / "README.md").write_text("# Readme", encoding="utf-8")

        overview = project_service.get_project_overview(proj["id"])
        self.assertIn("total_files", overview)
        self.assertGreaterEqual(overview["total_files"], 2)
        self.assertIn(".py", overview["languages"])

        # Update project instructions
        updated = project_service.update_project(
            project_id=proj["id"],
            name="Renamed App",
            instructions="# Custom instructions\n- Run tests often"
        )
        self.assertEqual(updated["name"], "Renamed App")
        self.assertEqual(agents_md.read_text(encoding="utf-8"), "# Custom instructions\n- Run tests often")

        # Active project state
        active = project_service.get_active_project()
        self.assertEqual(active["id"], proj["id"])

        project_service.close_active_project()
        self.assertIsNone(project_service._active_project_id)

        # Delete project
        del_res = project_service.delete_project(proj["id"])
        self.assertTrue(del_res)
        self.assertIsNone(project_service.get_project(proj["id"]))
        # Directory on disk remains intact
        self.assertTrue(self.proj_path.exists())

    # -------------------------------------------------------------------------
    # 2. Conversation Isolation per Project
    # -------------------------------------------------------------------------
    def test_conversation_project_isolation(self):
        # Create two projects
        p1 = project_service.open_or_create_project(str(self.proj_path / "p1"), "Project One")
        p2 = project_service.open_or_create_project(str(self.proj_path / "p2"), "Project Two")

        # Create conversations
        conv1 = db.create_conversation("Chat P1", "ollama", "llama3.2:1b", project_id=p1["id"])
        conv2 = db.create_conversation("Chat P2", "ollama", "llama3.2:1b", project_id=p2["id"])
        conv_global = db.create_conversation("Chat Global", "ollama", "llama3.2:1b", project_id=None)

        # Query isolated lists
        p1_convs = db.list_conversations(project_id=p1["id"])
        p2_convs = db.list_conversations(project_id=p2["id"])
        global_convs = db.list_conversations(project_id=None)

        p1_ids = [c["id"] for c in p1_convs]
        p2_ids = [c["id"] for c in p2_convs]
        global_ids = [c["id"] for c in global_convs]

        self.assertIn(conv1["id"], p1_ids)
        self.assertNotIn(conv2["id"], p1_ids)
        self.assertNotIn(conv_global["id"], p1_ids)

        self.assertIn(conv2["id"], p2_ids)
        self.assertNotIn(conv1["id"], p2_ids)
        self.assertNotIn(conv_global["id"], p2_ids)

        self.assertIn(conv_global["id"], global_ids)
        self.assertNotIn(conv1["id"], global_ids)
        self.assertNotIn(conv2["id"], global_ids)

        # Clean up
        db.delete_conversation(conv1["id"])
        db.delete_conversation(conv2["id"])
        db.delete_conversation(conv_global["id"])
        project_service.delete_project(p1["id"])
        project_service.delete_project(p2["id"])

    # -------------------------------------------------------------------------
    # 3. Hardware Specs & Model Recommendation Star (⭐)
    # -------------------------------------------------------------------------
    def test_hardware_specs_and_model_stars(self):
        specs = llm_service.get_device_specs()
        self.assertIn("cpu_cores", specs)
        self.assertIn("ram_total_gb", specs)
        self.assertIn("ram_total_bytes", specs)
        self.assertGreater(specs["cpu_cores"], 0)
        self.assertGreater(specs["ram_total_gb"], 0)

        models_data = llm_service.get_all_available_models()
        self.assertIn("device_specs", models_data)
        self.assertIn("ollama", models_data)

        # Verify models have is_recommended and recommendation_reason fields
        ollama_models = models_data["ollama"].get("models", [])
        for m in ollama_models:
            self.assertIn("is_recommended", m)
            self.assertIn("recommendation_reason", m)

        # Recommended local model (e.g. llama3.2:1b under RAM limit)
        for m in ollama_models:
            if "1b" in m["id"] or "1.5b" in m["id"]:
                self.assertTrue(m["is_recommended"])
                self.assertIn("Fits comfortably", m["recommendation_reason"])

        # Cloud models (e.g. gemini-2.0-flash, gpt-4o-mini) are recommended
        for prov in ["openai", "gemini", "anthropic", "groq"]:
            if prov in models_data:
                for m in models_data[prov].get("models", []):
                    self.assertIn("is_recommended", m)

    # -------------------------------------------------------------------------
    # 4. Project-Aware Agent Orchestration & Sandboxing
    # -------------------------------------------------------------------------
    def test_project_aware_agent_workspace(self):
        proj = project_service.open_or_create_project(str(self.proj_path / "sandbox"), "Sandbox App")
        
        # Test setting active workspace
        permission_manager.set_active_workspace(proj["path"])
        active_ws = permission_manager.get_workspace_dir()
        self.assertEqual(active_ws, Path(proj["path"]).resolve())

        # File creation inside project workspace works
        safe_file = permission_manager.resolve_safe_path("app.py")
        self.assertTrue(safe_file.is_relative_to(Path(proj["path"]).resolve()))

        # Reset workspace
        permission_manager.set_active_workspace(None)
        project_service.delete_project(proj["id"])

    # -------------------------------------------------------------------------
    # 5. REST API Endpoints
    # -------------------------------------------------------------------------
    def test_api_endpoints(self):
        # 1. GET /api/system/specs
        res = self.client.get("/api/system/specs")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("cpu_cores", data)
        self.assertIn("ram_total_gb", data)

        # 2. POST /api/projects
        res = self.client.post("/api/projects", json={
            "path": str(self.proj_path / "api_test"),
            "name": "API Test Project",
            "instructions": "# Custom Guide"
        })
        self.assertEqual(res.status_code, 200)
        proj_data = res.json()
        proj_id = proj_data["id"]
        self.assertEqual(proj_data["name"], "API Test Project")

        # 3. GET /api/projects
        res = self.client.get("/api/projects")
        self.assertEqual(res.status_code, 200)
        proj_list = res.json()
        self.assertTrue(any(p["id"] == proj_id for p in proj_list))

        # 4. GET /api/projects/active
        res = self.client.get("/api/projects/active")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], proj_id)

        # 5. GET /api/projects/{id}
        res = self.client.get(f"/api/projects/{proj_id}")
        self.assertEqual(res.status_code, 200)
        detail = res.json()
        self.assertIn("overview", detail)
        self.assertEqual(detail["instructions_content"], "# Custom Guide")

        # 6. PATCH /api/projects/{id}
        res = self.client.patch(f"/api/projects/{proj_id}", json={
            "name": "Updated API Project"
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["name"], "Updated API Project")

        # 7. POST /api/projects/close
        res = self.client.post("/api/projects/close")
        self.assertEqual(res.status_code, 200)

        # 8. POST /api/projects/{id}/open
        res = self.client.post(f"/api/projects/{proj_id}/open")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], proj_id)

        # 9. GET /api/conversations?project_id=
        res = self.client.post("/api/conversations", json={
            "title": "API Conv In Project",
            "project_id": proj_id
        })
        self.assertEqual(res.status_code, 200)
        conv_id = res.json()["id"]

        res = self.client.get(f"/api/conversations?project_id={proj_id}")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(any(c["id"] == conv_id for c in res.json()))

        # 10. DELETE /api/projects/{id}
        res = self.client.delete(f"/api/projects/{proj_id}")
        self.assertEqual(res.status_code, 200)

        # Clean conversation
        db.delete_conversation(conv_id)


if __name__ == "__main__":
    unittest.main()
