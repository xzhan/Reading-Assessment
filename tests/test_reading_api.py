"""Smoke tests for the reading Lexile-like assessment API."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from backend.pet_writing_api.server import create_server


class ReadingApiFlowTest(unittest.TestCase):
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

    def test_full_reading_flow(self) -> None:
        status, created = self.request(
            "POST",
            "/api/v1/reading/assessments",
            {"student_id": "stu_reader", "grade_level": 7},
        )
        self.assertEqual(status, 201)
        assessment_id = created["assessment_id"]
        self.assertEqual(created["current_anchor_lexile"], 800)

        for _ in range(3):
            status, next_payload = self.request("GET", f"/api/v1/reading/assessments/{assessment_id}/next")
            self.assertEqual(status, 200)
            self.assertIn("passage", next_payload)
            self.assertEqual(len(next_payload["items"]), 5)
            self.assertNotIn("correct_choice", next_payload["items"][0])

            responses = [
                {
                    "item_id": item["item_id"],
                    "selected_choice": "A",
                    "time_spent_sec": 30,
                }
                for item in next_payload["items"]
            ]
            status, result = self.request(
                "POST",
                f"/api/v1/reading/assessments/{assessment_id}/responses",
                {
                    "passage_id": next_payload["passage"]["passage_id"],
                    "time_spent_sec": 360,
                    "responses": responses,
                },
            )
            self.assertEqual(status, 200)
            self.assertIn(result["status"], {"continue", "ready_to_complete"})
            self.assertGreaterEqual(result["passages_completed"], 1)

        status, completed = self.request("POST", f"/api/v1/reading/assessments/{assessment_id}/complete")
        self.assertEqual(status, 200)
        self.assertIn("estimated_range", completed)
        self.assertIn("practice_range", completed)
        self.assertIn("domain_scores", completed)
        self.assertIn("test_duration", completed)
        self.assertIn("zpd_like", completed)
        self.assertIn("star_report_alignment", completed)
        self.assertEqual(completed["star_report_alignment"]["percentile_rank"]["status"], "not_available")
        self.assertEqual(completed["star_report_alignment"]["scaled_score_like"]["status"], "internal_estimate")

        status, report = self.request("GET", f"/api/v1/reading/assessments/{assessment_id}/report")
        self.assertEqual(status, 200)
        self.assertEqual(report["assessment_id"], assessment_id)
        self.assertIn("summary", report)
        self.assertIn("official_domain_groups", report)


if __name__ == "__main__":
    unittest.main()
