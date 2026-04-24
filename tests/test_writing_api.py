"""Smoke tests for the PET Writing MVP backend."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from backend.pet_writing_api.server import create_server


class WritingApiFlowTest(unittest.TestCase):
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
        data = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.base_url}{path}",
            method=method,
            data=data,
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_full_writing_flow(self) -> None:
        status, prompts = self.request("GET", "/api/v1/writing/prompts")
        self.assertEqual(status, 200)
        prompt_id = next(item["prompt_id"] for item in prompts["items"] if item["task_type"] == "email")

        status, attempt = self.request(
            "POST",
            "/api/v1/writing/attempts",
            {"student_id": "stu_demo", "prompt_id": prompt_id},
        )
        self.assertEqual(status, 201)
        attempt_id = attempt["attempt_id"]

        essay_1 = (
            "Dear Sam,\n"
            "I joined the music club at school because I really enjoy singing, learning new songs, and meeting new friends after class. "
            "We practise every Tuesday, and our teacher is very kind, so everyone feels relaxed and ready to try new things.\n"
            "Last week we prepared for a school show, and I liked the club even more because we worked together and helped each other improve. "
            "You should come and visit our club next week because it is fun, friendly, and a very good way to spend time after school. "
            "If you come, I can introduce you to my classmates and show you our favourite songs."
        )
        status, draft = self.request(
            "PUT",
            f"/api/v1/writing/attempts/{attempt_id}/draft",
            {"draft_number": 1, "text": essay_1, "time_spent_sec": 500},
        )
        self.assertEqual(status, 200)
        self.assertGreaterEqual(draft["word_count"], 40)

        status, submission = self.request(
            "POST",
            f"/api/v1/writing/attempts/{attempt_id}/submissions",
            {
                "draft_number": 1,
                "text": essay_1,
                "time_spent_sec": 900,
                "word_count_client": 80,
            },
        )
        self.assertEqual(status, 201)
        submission_id = submission["submission_id"]

        status, report = self.request("GET", f"/api/v1/writing/submissions/{submission_id}/report")
        self.assertEqual(status, 200)
        self.assertIn("scores", report)
        self.assertIn("feedback", report)
        self.assertIn("review", report)
        self.assertFalse(report["review"]["needs_review"])
        self.assertEqual(report["review"]["review_reason_codes"], [])

        status, attempt_state = self.request("GET", f"/api/v1/writing/attempts/{attempt_id}")
        self.assertEqual(status, 200)
        self.assertEqual(attempt_state["review_status"], "not_required")

        status, rewrite = self.request("POST", f"/api/v1/writing/attempts/{attempt_id}/rewrite")
        self.assertEqual(status, 200)
        self.assertEqual(rewrite["next_draft_number"], 2)

        essay_2 = (
            "Dear Sam,\n"
            "I joined the music club at school because I really enjoy singing, learning new songs, and working in a team with other students. "
            "First, we practise every Tuesday after class, and then we prepare for school shows together, which makes the lessons exciting and useful.\n"
            "I especially like the club because the teacher gives us helpful advice, and my friends always encourage me when I feel nervous about performing. "
            "You should come and join us next week because the club is friendly, fun, and a great way to meet students who love music. "
            "I think you will enjoy it a lot, and afterwards we can walk home together and talk about our favourite songs."
        )
        status, second = self.request(
            "POST",
            f"/api/v1/writing/attempts/{attempt_id}/submissions",
            {
                "draft_number": 2,
                "text": essay_2,
                "time_spent_sec": 1100,
                "word_count_client": 100,
            },
        )
        self.assertEqual(status, 201)
        self.assertTrue(second["comparison_ready"])

        status, comparison = self.request("GET", f"/api/v1/writing/attempts/{attempt_id}/comparison")
        self.assertEqual(status, 200)
        self.assertIn("score_delta", comparison)

        status, history = self.request("GET", "/api/v1/students/stu_demo/writing/history")
        self.assertEqual(status, 200)
        self.assertEqual(len(history["items"]), 1)


if __name__ == "__main__":
    unittest.main()
