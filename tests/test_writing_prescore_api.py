"""API tests for the stateless writing pre-score route."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from backend.pet_writing_api.server import create_server


class WritingPreScoreApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        self.server = create_server("127.0.0.1", 0, self.db_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            url=f"{self.base_url}{path}",
            method=method,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_prescore_is_stateless_and_returns_review(self) -> None:
        status, prompts = self.request("GET", "/api/v1/writing/prompts")
        self.assertEqual(status, 200)
        prompt_id = prompts["items"][0]["prompt_id"]

        status, payload = self.request(
            "POST",
            "/api/v1/writing/prescore",
            {
                "prompt_id": prompt_id,
                "text": "Hello. I like school.",
                "time_spent_sec": 120,
                "word_count_client": 4,
            },
        )
        self.assertEqual(status, 200)
        self.assertNotIn("submission_id", payload)
        self.assertIn("scores", payload)
        self.assertIn("review", payload)
        self.assertTrue(payload["review"]["needs_review"])
        self.assertIn("signals", payload)


if __name__ == "__main__":
    unittest.main()
