import os
import sys
import time
import threading
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.permissions import permission_manager, permission_broker, PermissionBroker
from app.agent.task_state import TaskState
from app.agent.tool_registry import tool_registry
from app.agent.tools.terminal import run_terminal
from app.agent.tools.filesystem import (
    list_files, read_file, write_file, edit_file,
    move_file, copy_file, delete_file, search_files
)
from app.agent.tools.docx_tools import manage_docx
from app.agent.tools.image_tools import analyze_image
from app.services.vision_service import vision_service
from app.agent.orchestrator import agent_orchestrator
from fastapi.testclient import TestClient
from app.server import app
from app.database import db

class TestAgentHarness(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.workspace = permission_manager.get_workspace_dir()
        self.test_dir = self.workspace / "test_scratch_agent"
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            import shutil
            shutil.rmtree(str(self.test_dir), ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. Permissions & Sandboxing
    # -------------------------------------------------------------------------
    def test_permissions_sandbox(self):
        # Safe path within workspace
        safe_p = permission_manager.resolve_safe_path("data")
        self.assertTrue(safe_p.is_relative_to(self.workspace))

        # Path traversal attack
        with self.assertRaises(PermissionError):
            permission_manager.resolve_safe_path("../../../etc/passwd")

        # Dangerous command blocking
        safe_cmd, _ = permission_manager.is_safe_command("python -c 'print(1)'")
        self.assertTrue(safe_cmd)

        bad_cmd, _ = permission_manager.is_safe_command("rm -rf /")
        self.assertFalse(bad_cmd)

        bad_fork, _ = permission_manager.is_safe_command(":(){ :|:& };:")
        self.assertFalse(bad_fork)

    # -------------------------------------------------------------------------
    # 2. Terminal Execution Tool
    # -------------------------------------------------------------------------
    def test_terminal_tool(self):
        # Basic command
        res = run_terminal("echo 'Hello Agent'")
        self.assertTrue(res["success"])
        self.assertIn("Hello Agent", res["stdout"])
        self.assertEqual(res["exit_code"], 0)

        # Python script execution
        py_file = self.test_dir / "counter.py"
        with open(py_file, "w") as f:
            f.write("for i in range(1, 6): print(i)")

        res_py = run_terminal(f"python {py_file}")
        self.assertTrue(res_py["success"])
        self.assertIn("1\n2\n3\n4\n5", res_py["stdout"].strip())

        # Error capture
        res_err = run_terminal("python -c 'raise ValueError(\"Test Error\")'")
        self.assertFalse(res_err["success"])
        self.assertIn("ValueError: Test Error", res_err["stderr"])
        self.assertNotEqual(res_err["exit_code"], 0)

    # -------------------------------------------------------------------------
    # 3. Filesystem Operations
    # -------------------------------------------------------------------------
    def test_filesystem_tools(self):
        # 1. write_file
        rel_file = "test_scratch_agent/sample.py"
        w_res = write_file(rel_file, "def greet():\n    return 'Hello World'\n")
        self.assertTrue(w_res["success"])

        # 2. read_file
        r_res = read_file(rel_file, start_line=1, end_line=2)
        self.assertTrue(r_res["success"])
        self.assertIn("def greet():", r_res["content"])

        # 3. edit_file
        e_res = edit_file(rel_file, target_text="'Hello World'", replacement_text="'Hello AI Agent'")
        self.assertTrue(e_res["success"])
        r_res2 = read_file(rel_file)
        self.assertIn("'Hello AI Agent'", r_res2["content"])

        # 4. search_files
        s_res = search_files(query="Hello AI Agent", directory="test_scratch_agent")
        self.assertTrue(s_res["success"])
        self.assertGreaterEqual(s_res["total_matches"], 1)

        # 5. copy_file
        c_res = copy_file(rel_file, "test_scratch_agent/sample_copy.py")
        self.assertTrue(c_res["success"])

        # 6. list_files
        l_res = list_files(directory="test_scratch_agent")
        self.assertTrue(l_res["success"])
        self.assertGreaterEqual(l_res["count"], 2)

        # 7. move_file
        m_res = move_file("test_scratch_agent/sample_copy.py", "test_scratch_agent/sample_renamed.py")
        self.assertTrue(m_res["success"])

        # 8. delete_file
        # Without confirm=True -> should fail
        d_fail = delete_file("test_scratch_agent/sample_renamed.py", confirm=False)
        self.assertFalse(d_fail["success"])

        d_succ = delete_file("test_scratch_agent/sample_renamed.py", confirm=True)
        self.assertTrue(d_succ["success"])

    # -------------------------------------------------------------------------
    # 4. DOCX Manipulation Tool
    # -------------------------------------------------------------------------
    def test_docx_tool(self):
        docx_path = "test_scratch_agent/report.docx"

        # 1. Create DOCX with text and table
        c_res = manage_docx(
            action="create",
            file_path=docx_path,
            text="Initial Project Report",
            heading_level=0,
            table_data=[["Metric", "Value"], ["Accuracy", "95%"], ["Latency", "42ms"]]
        )
        self.assertTrue(c_res["success"])

        # 2. Read DOCX
        r_res = manage_docx(action="read", file_path=docx_path)
        self.assertTrue(r_res["success"])
        self.assertEqual(len(r_res["paragraphs"]), 1)
        self.assertEqual(len(r_res["tables"]), 1)
        self.assertEqual(r_res["tables"][0]["data"][1][1], "95%")

        # 3. Add paragraph
        a_res = manage_docx(
            action="add_paragraph",
            file_path=docx_path,
            text="This section details system performance and latency metrics."
        )
        self.assertTrue(a_res["success"])

        # 4. Replace text
        rep_res = manage_docx(
            action="replace_text",
            file_path=docx_path,
            target_text="Initial Project Report",
            replacement_text="Final Production Report"
        )
        self.assertTrue(rep_res["success"])
        self.assertGreaterEqual(rep_res["occurrences_replaced"], 1)

        # 5. Modify table cell
        mt_res = manage_docx(
            action="modify_table",
            file_path=docx_path,
            table_index=0,
            row_index=1,
            col_index=1,
            new_value="99.4%"
        )
        self.assertTrue(mt_res["success"])

        # Verify read reflects changes
        r_ver = manage_docx(action="read", file_path=docx_path)
        self.assertEqual(r_ver["tables"][0]["data"][1][1], "99.4%")
        self.assertIn("Final Production Report", r_ver["paragraphs"][0]["text"])

    # -------------------------------------------------------------------------
    # 5. Image & Vision Service Tools
    # -------------------------------------------------------------------------
    def test_vision_preprocessing_and_shapes(self):
        from PIL import Image, ImageDraw

        # Generate a synthetic test image with shapes & text
        img = Image.new("RGB", (400, 300), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Draw a rectangle
        draw.rectangle([30, 30, 150, 120], outline=(0, 0, 0), width=3, fill=(180, 200, 240))
        # Draw a circle
        draw.ellipse([220, 30, 340, 150], outline=(0, 0, 0), width=3, fill=(240, 180, 180))
        # Draw text
        draw.text((50, 200), "Sales Growth: Q1 to Q4", fill=(0, 0, 0))

        test_img_path = self.test_dir / "test_diagram.png"
        img.save(test_img_path)

        # 1. Test image preprocessing
        proc_bytes, mime = vision_service.preprocess_image(
            test_img_path,
            grayscale=True,
            contrast_factor=1.5,
            resize_max=(200, 200)
        )
        self.assertGreater(len(proc_bytes), 0)
        self.assertEqual(mime, "image/png")

        # 2. Test geometric shape detection via OpenCV
        geom = vision_service.detect_shapes_and_geometry(test_img_path)
        self.assertTrue(geom["available"])
        self.assertGreaterEqual(geom["detected_shapes_count"], 1)
        shape_types = [s["type"] for s in geom["shapes"]]
        self.assertTrue("rectangle" in shape_types or "square" in shape_types or "circle" in shape_types or "polygon" in shape_types)

        # 3. Test analyze_image tool with geometry mode
        res_tool = analyze_image(image_path=str(test_img_path), mode="geometry")
        self.assertTrue(res_tool["success"])
        self.assertIn("geometric_analysis", res_tool)

    # -------------------------------------------------------------------------
    # 6. Tool Registry
    # -------------------------------------------------------------------------
    def test_tool_registry(self):
        tools = tool_registry.get_tool_definitions()
        self.assertGreaterEqual(len(tools), 11)

        names = tool_registry.list_tool_names()
        expected = [
            "run_terminal", "list_files", "read_file", "write_file",
            "edit_file", "move_file", "copy_file", "delete_file",
            "search_files", "manage_docx", "analyze_image"
        ]
        for exp in expected:
            self.assertIn(exp, names)

        # Test tool execution dispatch
        res = tool_registry.execute_tool("read_file", {"path": "requirements.txt", "start_line": 1, "end_line": 2})
        self.assertTrue(res["success"])
        self.assertIn("fastapi", res["content"])

    # -------------------------------------------------------------------------
    # 7. Agent API Endpoints
    # -------------------------------------------------------------------------
    def test_agent_api_endpoints(self):
        # 1. /api/agent/tools
        res = self.client.get("/api/agent/tools")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("run_terminal", data["names"])
        self.assertIn("manage_docx", data["names"])
        self.assertIn("analyze_image", data["names"])

        # 2. /api/agent/cancel/nonexistent
        res_cancel = self.client.post("/api/agent/cancel/fake_task_id")
        self.assertEqual(res_cancel.status_code, 200)
        self.assertFalse(res_cancel.json()["cancelled"])

    # -------------------------------------------------------------------------
    # 8. Agent Failure Reporting
    # -------------------------------------------------------------------------
    def test_agent_preflight_failure_is_reported(self):
        with patch(
            "app.agent.orchestrator.llm_service.check_agent_readiness",
            return_value=(False, "Model cannot run Agent Mode."),
        ):
            events = list(agent_orchestrator.run_agent_stream(
                objective="test preflight",
                conversation_id="test-preflight",
                provider="ollama",
                model="bad-model",
            ))

        types = [e.get("type") for e in events]
        self.assertNotIn("agent_start", types)
        self.assertEqual(types[-1], "done")
        self.assertEqual(events[-1]["status"], "failed")
        self.assertIn("Model cannot run Agent Mode.", events[-1]["error"])

    def test_agent_failure_does_not_claim_completion(self):
        conv = db.create_conversation(title="Agent failure", provider="ollama", model="test-model")
        try:
            def fake_stream(*args, **kwargs):
                yield {"type": "error", "error": "The model returned an empty response."}
                yield {
                    "type": "done",
                    "task_id": "test-task",
                    "status": "failed",
                    "final_answer": "",
                    "error": "The model returned an empty response.",
                    "iterations": 1,
                    "prompt_tokens": 1,
                    "completion_tokens": 0,
                    "total_tokens": 1,
                    "duration_sec": 0.1,
                    "tokens_per_sec": 0.0,
                    "estimated_cost": 0.0,
                }

            with patch("app.server.agent_orchestrator.run_agent_stream", side_effect=fake_stream):
                res = self.client.post("/api/chat", json={
                    "conversation_id": conv["id"],
                    "message": "do something",
                    "agent_mode": True,
                })

            self.assertEqual(res.status_code, 200)
            self.assertIn("Agent task failed", res.text)
            self.assertNotIn("Task execution completed", res.text)
        finally:
            db.delete_conversation(conv["id"])

    # -------------------------------------------------------------------------
    # 9. Agent Permission Modes & Approval Flow
    # -------------------------------------------------------------------------
    def test_permission_mode_and_read_only_tools(self):
        def always_ask(key, default=None):
            if key == "agent_permission_mode":
                return "always_ask"
            return default

        with patch("app.agent.permissions.config_manager.get", side_effect=always_ask):
            self.assertTrue(permission_manager.requires_approval("run_terminal", {"command": "ls"}))
            self.assertTrue(permission_manager.requires_approval("write_file", {"path": "x.txt"}))
            self.assertFalse(permission_manager.requires_approval("read_file", {"path": "x.txt"}))
            self.assertFalse(permission_manager.requires_approval("list_files", {}))
            self.assertFalse(permission_manager.requires_approval("manage_docx", {"action": "read"}))
            self.assertTrue(permission_manager.requires_approval("manage_docx", {"action": "create"}))

        def allow_all(key, default=None):
            if key == "agent_permission_mode":
                return "allow_all"
            return default

        with patch("app.agent.permissions.config_manager.get", side_effect=allow_all):
            self.assertFalse(permission_manager.requires_approval("run_terminal", {"command": "ls"}))

    def test_permission_broker_decisions(self):
        broker = PermissionBroker()

        request = broker.create_request("task-a", "run_terminal", {"command": "ls"}, {"title": "Run"})
        self.assertIsNotNone(request)
        self.assertTrue(broker.resolve(request.request_id, "allow"))
        self.assertEqual(
            broker.wait_for_decision(request.request_id, timeout=1),
            ("allow", "allow"),
        )

        request = broker.create_request("task-a", "run_terminal", {"command": "ls"}, {"title": "Run"})
        self.assertIsNotNone(request)
        self.assertTrue(broker.resolve(request.request_id, "always_allow"))
        self.assertEqual(
            broker.wait_for_decision(request.request_id, timeout=1),
            ("allow", "always_allow"),
        )
        self.assertIsNone(
            broker.create_request("task-a", "run_terminal", {"command": "pwd"}, {"title": "Run"})
        )
        task_b_request = broker.create_request(
            "task-b", "run_terminal", {"command": "pwd"}, {"title": "Run"}
        )
        self.assertIsNotNone(task_b_request)
        broker.cancel_task("task-b")
        self.assertEqual(
            broker.wait_for_decision(task_b_request.request_id, timeout=1),
            ("deny", "cancelled"),
        )

        request = broker.create_request("task-timeout", "write_file", {}, {"title": "Write"})
        started = time.time()
        self.assertEqual(
            broker.wait_for_decision(request.request_id, timeout=1),
            ("deny", "timeout"),
        )
        self.assertGreaterEqual(time.time() - started, 0.9)

        cancel_request = broker.create_request("task-cancel", "run_terminal", {}, {"title": "Run"})
        broker.cancel_task("task-cancel")
        self.assertEqual(
            broker.wait_for_decision(cancel_request.request_id, timeout=1),
            ("deny", "cancelled"),
        )

        switch_request = broker.create_request("task-switch", "write_file", {}, {"title": "Write"})
        self.assertEqual(broker.allow_all_pending(), 1)
        self.assertEqual(
            broker.wait_for_decision(switch_request.request_id, timeout=1),
            ("allow", "allow_all"),
        )

        self.assertFalse(broker.resolve("missing-request", "allow"))
        self.assertFalse(broker.resolve(request.request_id, "not-a-decision"))
        broker.cleanup_task("task-a")
        broker.cleanup_task("task-b")

    def test_agent_permission_request_flow(self):
        tool_call_response = {
            "content": "",
            "tool_calls": [{
                "id": "call_permission_test",
                "name": "write_file",
                "arguments": {"path": "permission_test.txt", "content": "hello"},
            }],
            "prompt_tokens": 1,
            "completion_tokens": 1,
        }
        final_response = {
            "content": "Finished after approval.",
            "tool_calls": [],
            "prompt_tokens": 1,
            "completion_tokens": 1,
        }

        events = []
        with patch(
            "app.agent.orchestrator.llm_service.check_agent_readiness",
            return_value=(True, ""),
        ), patch(
            "app.agent.orchestrator.llm_service.chat_with_tools",
            side_effect=[tool_call_response, final_response],
        ), patch(
            "app.agent.orchestrator.permission_manager.requires_approval",
            return_value=True,
        ), patch(
            "app.agent.orchestrator.tool_registry.execute_tool",
            return_value={"success": True, "path": "permission_test.txt"},
        ):
            for event in agent_orchestrator.run_agent_stream(
                objective="write a permission test file",
                conversation_id="permission-flow",
                provider="ollama",
                model="fake-model",
            ):
                events.append(event)
                if event.get("type") == "permission_request":
                    threading.Timer(
                        0.05,
                        lambda rid=event["request_id"]: permission_broker.resolve(rid, "always_allow"),
                    ).start()

        types = [e.get("type") for e in events]
        self.assertIn("permission_request", types)
        self.assertIn("permission_resolved", types)
        resolved = next(e for e in events if e.get("type") == "permission_resolved")
        self.assertEqual(resolved["decision"], "always_allow")
        tool_result = next(e for e in events if e.get("type") == "tool_result")
        self.assertTrue(tool_result["result"]["success"])
        self.assertEqual(events[-1]["status"], "completed")
        self.assertEqual(permission_broker.pending_count(), 0)

    def test_permission_endpoint_resolves_request(self):
        request = permission_broker.create_request(
            "endpoint-test", "run_terminal", {"command": "ls"}, {"title": "Run"}
        )
        self.assertIsNotNone(request)

        res = self.client.post(
            f"/api/agent/permission/{request.request_id}",
            json={"decision": "allow"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            permission_broker.wait_for_decision(request.request_id, timeout=1),
            ("allow", "allow"),
        )

        res_missing = self.client.post(
            "/api/agent/permission/does-not-exist",
            json={"decision": "allow"},
        )
        self.assertEqual(res_missing.status_code, 404)

        res_invalid = self.client.post(
            "/api/agent/permission/does-not-exist",
            json={"decision": "maybe"},
        )
        self.assertEqual(res_invalid.status_code, 400)
        permission_broker.cleanup_task("endpoint-test")


if __name__ == "__main__":
    unittest.main()
