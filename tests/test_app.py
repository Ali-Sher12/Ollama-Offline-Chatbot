import os
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import db
from app.services.file_service import file_service
from app.services.rag_service import rag_service
from app.services.analytics_service import analytics_service
from app.services.llm_service import llm_service
from app.config import config_manager
from fastapi.testclient import TestClient
from app.server import app

class TestOllamaChatbot(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_database_lifecycle(self):
        # 1. Create conversation
        conv = db.create_conversation(title="Test Convo", provider="ollama", model="llama3.2:1b")
        self.assertIsNotNone(conv["id"])
        self.assertEqual(conv["title"], "Test Convo")

        # 2. Add user message
        msg1 = db.add_message(
            conversation_id=conv["id"],
            role="user",
            content="Hello world",
            prompt_tokens=5,
            completion_tokens=0
        )
        self.assertIsNotNone(msg1["id"])

        # 3. Add assistant message
        msg2 = db.add_message(
            conversation_id=conv["id"],
            role="assistant",
            content="Hi there! How can I help you?",
            prompt_tokens=5,
            completion_tokens=8,
            duration_sec=0.5
        )
        self.assertIsNotNone(msg2["id"])

        # 4. Fetch full conversation
        loaded = db.get_conversation(conv["id"])
        self.assertEqual(len(loaded["messages"]), 2)

        # 5. Test export to docx
        export_file = db.export_docx(conv["id"])
        self.assertTrue(os.path.exists(export_file))
        os.remove(export_file)

        # 6. Update title
        updated = db.update_conversation_title(conv["id"], "Renamed Convo")
        self.assertTrue(updated)
        loaded = db.get_conversation(conv["id"])
        self.assertEqual(loaded["title"], "Renamed Convo")

        # 7. Delete conversation
        deleted = db.delete_conversation(conv["id"])
        self.assertTrue(deleted)
        self.assertIsNone(db.get_conversation(conv["id"]))

    def test_file_service(self):
        test_txt = Path(__file__).resolve().parent / "sample.txt"
        with open(test_txt, "w") as f:
            f.write("Line 1\nLine 2 sample text")
        
        meta = file_service.get_file_metadata(test_txt)
        self.assertEqual(meta["filename"], "sample.txt")
        self.assertIn("Line 1", meta["content"])
        os.remove(test_txt)

    def test_rag_augmentation(self):
        augmented = rag_service.build_augmented_context(
            user_message="Explain quantum computing",
            attachments=[{"filename": "doc.txt", "content": "Quantum notes"}],
            search_results=[{"title": "Quantum Wiki", "url": "https://wiki.org", "snippet": "A quantum is..."}]
        )
        self.assertIn("Quantum notes", augmented)
        self.assertIn("Quantum Wiki", augmented)
        self.assertIn("Explain quantum computing", augmented)

    def test_analytics_and_budget(self):
        tokens = analytics_service.estimate_tokens("Hello world this is a test")
        self.assertGreater(tokens, 0)

        # Budget status
        status = analytics_service.get_budget_status(total_tokens_used=50000, budget_limit=100000)
        self.assertEqual(status["percentage_used"], 50.0)
        self.assertEqual(status["remaining_tokens"], 50000)
        self.assertFalse(status["is_approaching_limit"])

        # Warning when approaching limit (>= 80%)
        status_warn = analytics_service.get_budget_status(total_tokens_used=85000, budget_limit=100000)
        self.assertTrue(status_warn["is_approaching_limit"])
        self.assertFalse(status_warn["is_exceeded"])

        # Exceeded
        status_exceed = analytics_service.get_budget_status(total_tokens_used=105000, budget_limit=100000)
        self.assertTrue(status_exceed["is_exceeded"])

    def test_api_endpoints(self):
        # /api/models
        res = self.client.get("/api/models")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("ollama", data)
        self.assertIn("openai", data)

        # /api/conversations
        res = self.client.get("/api/conversations")
        self.assertEqual(res.status_code, 200)

        # /api/settings
        res = self.client.get("/api/settings")
        self.assertEqual(res.status_code, 200)

        # /api/analytics
        res = self.client.get("/api/analytics")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("summary", data)
        self.assertIn("budget_status", data)

    def test_delete_message_pair(self):
        conv = db.create_conversation(title="Delete Pair Test", provider="ollama", model="llama3.2:1b")
        user_one = db.add_message(conv["id"], "user", "First prompt")
        assistant_one = db.add_message(conv["id"], "assistant", "First reply")
        user_two = db.add_message(conv["id"], "user", "Second prompt")
        assistant_two = db.add_message(conv["id"], "assistant", "Second reply")

        # Deleting from the assistant side removes the whole second pair.
        result = db.delete_message_pair(conv["id"], assistant_two["id"])
        self.assertTrue(result["success"])
        self.assertEqual(
            set(result["deleted_ids"]),
            {user_two["id"], assistant_two["id"]}
        )
        remaining = db.get_conversation(conv["id"])["messages"]
        self.assertEqual([m["id"] for m in remaining], [user_one["id"], assistant_one["id"]])

        # Deleting from the user side removes the whole first pair.
        result = db.delete_message_pair(conv["id"], user_one["id"])
        self.assertTrue(result["success"])
        self.assertEqual(
            set(result["deleted_ids"]),
            {user_one["id"], assistant_one["id"]}
        )
        self.assertEqual(db.get_conversation(conv["id"])["messages"], [])

        # Unknown message ids are rejected.
        result = db.delete_message_pair(conv["id"], "missing-message-id")
        self.assertFalse(result["success"])

        db.delete_conversation(conv["id"])

    def test_delete_message_pair_with_identical_timestamps(self):
        """Pairs stay aligned even when messages share the same timestamp."""
        conv = db.create_conversation(title="Tie Pair Test", provider="ollama", model="llama3.2:1b")
        user_one = db.add_message(conv["id"], "user", "First prompt")
        assistant_one = db.add_message(conv["id"], "assistant", "First reply")
        user_two = db.add_message(conv["id"], "user", "Second prompt")
        assistant_two = db.add_message(conv["id"], "assistant", "Second reply")

        # Force every row to the same timestamp so only the rowid tie-breaker
        # can keep them in insertion order.
        with db._get_connection() as conn:
            conn.execute(
                "UPDATE messages SET created_at = ? WHERE conversation_id = ?",
                ("2026-01-01T00:00:00+00:00", conv["id"])
            )
            conn.commit()

        ordered = [m["id"] for m in db.get_conversation(conv["id"])["messages"]]
        self.assertEqual(
            ordered,
            [user_one["id"], assistant_one["id"], user_two["id"], assistant_two["id"]]
        )

        result = db.delete_message_pair(conv["id"], assistant_two["id"])
        self.assertTrue(result["success"])
        self.assertEqual(
            set(result["deleted_ids"]),
            {user_two["id"], assistant_two["id"]}
        )
        remaining = [m["id"] for m in db.get_conversation(conv["id"])["messages"]]
        self.assertEqual(remaining, [user_one["id"], assistant_one["id"]])

        db.delete_conversation(conv["id"])

    def test_append_chat_option(self):
        conv = db.create_conversation(title="Append Test", provider="ollama", model="llama3.2:1b")
        # Turn 1
        db.add_message(conv["id"], "user", "My favorite color is emerald green")
        db.add_message(conv["id"], "assistant", "I will remember that your favorite color is emerald green.")

        # Test request with append_chat=False vs append_chat=True
        req_append_off = {
            "conversation_id": conv["id"],
            "message": "What is my favorite color?",
            "append_chat": False
        }
        res = self.client.post("/api/chat", json=req_append_off)
        self.assertEqual(res.status_code, 200)

        db.delete_conversation(conv["id"])

    def test_local_ollama_discovery(self):
        models = llm_service.get_ollama_models()
        print(f"\n[Test] Found {len(models)} local Ollama model(s): {[m['id'] for m in models]}")
        # If Ollama is running, check models list
        if models:
            self.assertTrue(any("qwen2.5" in m["id"] or "llama" in m["id"] for m in models))

if __name__ == "__main__":
    unittest.main()
