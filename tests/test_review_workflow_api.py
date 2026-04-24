"""End-to-end tests for the internal review workflow."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from backend.pet_writing_api.server import create_server


class ReviewWorkflowApiTest(unittest.TestCase):
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
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_required_review_flows_through_queue_and_completion(self) -> None:
        status, prompts = self.request("GET", "/api/v1/writing/prompts")
        self.assertEqual(status, 200)
        prompt_id = next(item["prompt_id"] for item in prompts["items"] if item["task_type"] == "email")

        status, attempt = self.request(
            "POST",
            "/api/v1/writing/attempts",
            {"student_id": "stu_review", "prompt_id": prompt_id},
        )
        self.assertEqual(status, 201)
        attempt_id = attempt["attempt_id"]

        short_essay = (
            "Dear Sam,\n"
            "I joined a music club at school because it is fun and the teacher is kind. "
            "We sing after class on Tuesday, and I enjoy seeing my friends there. "
            "Please come next week."
        )
        status, submission = self.request(
            "POST",
            f"/api/v1/writing/attempts/{attempt_id}/submissions",
            {
                "draft_number": 1,
                "text": short_essay,
                "time_spent_sec": 240,
                "word_count_client": 18,
            },
        )
        self.assertEqual(status, 201)
        submission_id = submission["submission_id"]

        status, attempt_state = self.request("GET", f"/api/v1/writing/attempts/{attempt_id}")
        self.assertEqual(status, 200)
        self.assertEqual(attempt_state["status"], "review_required")
        self.assertEqual(attempt_state["review_status"], "required")

        status, report = self.request("GET", f"/api/v1/writing/submissions/{submission_id}/report")
        self.assertEqual(status, 200)
        self.assertTrue(report["review"]["needs_review"])
        self.assertEqual(report["review"]["review_status"], "required")
        self.assertIn("below_target_word_count", report["review"]["review_reason_codes"])

        status, rewrite_blocked = self.request("POST", f"/api/v1/writing/attempts/{attempt_id}/rewrite")
        self.assertEqual(status, 409)
        self.assertEqual(rewrite_blocked["error"]["code"], "REVIEW_REQUIRED")

        status, queue = self.request("GET", "/api/v1/internal/writing/reviews/queue")
        self.assertEqual(status, 200)
        self.assertEqual(len(queue["items"]), 1)
        self.assertEqual(queue["items"][0]["submission_id"], submission_id)
        self.assertIn("below_target_word_count", queue["items"][0]["review_reason_codes"])

        status, review = self.request(
            "POST",
            "/api/v1/internal/writing/reviews",
            {
                "submission_id": submission_id,
                "reviewer_id": "teacher_01",
                "scores": {
                    "task_achievement": 3,
                    "organization_coherence": 3,
                    "grammar_control": 3,
                    "lexical_range_accuracy": 3,
                    "overall": 12,
                },
                "comment": "Human review accepted the essay as a borderline draft.",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(review["status"], "reviewed")

        status, reviewed_report = self.request("GET", f"/api/v1/writing/submissions/{submission_id}/report")
        self.assertEqual(status, 200)
        self.assertEqual(reviewed_report["scores"]["overall"]["score"], 12)
        self.assertFalse(reviewed_report["review"]["needs_review"])
        self.assertEqual(reviewed_report["review"]["review_status"], "reviewed")
        self.assertEqual(reviewed_report["review"]["review_reason_codes"], [])

        status, rewrite = self.request("POST", f"/api/v1/writing/attempts/{attempt_id}/rewrite")
        self.assertEqual(status, 200)
        self.assertEqual(rewrite["status"], "rewrite_in_progress")


if __name__ == "__main__":
    unittest.main()
