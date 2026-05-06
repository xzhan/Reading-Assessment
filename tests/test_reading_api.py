"""Smoke tests for the reading Lexile-like assessment API."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
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

    def request_allow_error(self, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
        try:
            return self.request(method, path, payload)
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

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
        self.assertIn("benchmark", report)
        self.assertIn("reading_recommendation", report)
        self.assertIn("test_fidelity", report)
        self.assertIn("report_metadata", report)
        self.assertIn("testing_scope", report)

    def test_report_covers_star_report_terms_with_internal_statuses(self) -> None:
        status, created = self.request(
            "POST",
            "/api/v1/reading/assessments",
            {"student_id": "stu_terms", "grade_level": 6},
        )
        self.assertEqual(status, 201)
        assessment_id = created["assessment_id"]

        for selected_choice in ("B", "B", "A"):
            status, next_payload = self.request("GET", f"/api/v1/reading/assessments/{assessment_id}/next")
            self.assertEqual(status, 200)
            responses = [
                {
                    "item_id": item["item_id"],
                    "selected_choice": selected_choice,
                    "time_spent_sec": 42,
                }
                for item in next_payload["items"]
            ]
            status, _ = self.request(
                "POST",
                f"/api/v1/reading/assessments/{assessment_id}/responses",
                {
                    "passage_id": next_payload["passage"]["passage_id"],
                    "time_spent_sec": 420,
                    "responses": responses,
                },
            )
            self.assertEqual(status, 200)

        status, report = self.request("POST", f"/api/v1/reading/assessments/{assessment_id}/complete")
        self.assertEqual(status, 200)

        expected_terms = {
            "scaled_score_like",
            "percentile_rank",
            "grade_equivalent_like",
            "instructional_reading_level_like",
            "zpd_like",
            "benchmark",
            "official_domain_groups",
            "reading_recommendation",
            "test_duration",
            "test_fidelity",
            "report_metadata",
            "testing_scope",
            "report_term_coverage",
        }
        self.assertTrue(expected_terms.issubset(report.keys()))
        self.assertEqual(report["report_metadata"]["scale"], "Lexile-like Scale")
        self.assertEqual(report["report_metadata"]["benchmark_type"], "Internal Grade Band")
        self.assertEqual(report["percentile_rank"]["status"], "not_available")
        self.assertEqual(report["benchmark"]["status"], "internal_estimate")
        self.assertIn(report["benchmark"]["label"], {"urgent_intervention", "intervention", "on_watch", "at_or_above_benchmark"})
        self.assertEqual(set(report["official_domain_groups"]), {"literature", "informational_text", "vocabulary"})
        self.assertEqual(report["testing_scope"]["target_range"], "grades_6_8")
        self.assertEqual(report["testing_scope"]["passages_completed"], 3)
        self.assertIn("official_star_scaled_score", report["testing_scope"]["official_terms_requiring_external_norms"])
        self.assertEqual(report["test_fidelity"]["status"], "valid")
        parent_guidance = report["reading_recommendation"]["parent_material_guidance"]
        self.assertEqual(
            set(parent_guidance),
            {
                "confidence_or_warmup",
                "best_fit_daily_reading",
                "supported_challenge",
                "frustration_risk",
            },
        )
        self.assertIn("parents", parent_guidance["best_fit_daily_reading"]["use"])
        self.assertEqual(
            set(report["report_term_coverage"]),
            {
                "district_benchmark",
                "scaled_score_ss",
                "percentile_rank_pr",
                "grade_equivalent_ge",
                "instructional_reading_level_irl",
                "domain_scores",
                "reading_recommendation",
                "test_duration_and_fidelity",
                "diagnostic_report_metadata",
                "zpd",
            },
        )
        self.assertEqual(report["report_term_coverage"]["percentile_rank_pr"]["status"], "not_available")
        self.assertEqual(report["report_term_coverage"]["district_benchmark"]["field"], "benchmark")

    def test_parent_material_recommendations_help_choose_reading_materials(self) -> None:
        status, created = self.request(
            "POST",
            "/api/v1/reading/assessments",
            {"student_id": "stu_materials", "grade_level": 6},
        )
        self.assertEqual(status, 201)
        assessment_id = created["assessment_id"]

        status, not_ready = self.request_allow_error(
            "GET",
            f"/api/v1/reading/assessments/{assessment_id}/materials",
        )
        self.assertEqual(status, 404)
        self.assertEqual(not_ready["error"]["code"], "READING_REPORT_NOT_READY")

        for selected_choice in ("B", "B", "A"):
            status, next_payload = self.request("GET", f"/api/v1/reading/assessments/{assessment_id}/next")
            self.assertEqual(status, 200)
            responses = [
                {
                    "item_id": item["item_id"],
                    "selected_choice": selected_choice,
                    "time_spent_sec": 42,
                }
                for item in next_payload["items"]
            ]
            status, _ = self.request(
                "POST",
                f"/api/v1/reading/assessments/{assessment_id}/responses",
                {
                    "passage_id": next_payload["passage"]["passage_id"],
                    "time_spent_sec": 420,
                    "responses": responses,
                },
            )
            self.assertEqual(status, 200)

        status, report = self.request("POST", f"/api/v1/reading/assessments/{assessment_id}/complete")
        self.assertEqual(status, 200)
        status, materials = self.request("GET", f"/api/v1/reading/assessments/{assessment_id}/materials")
        self.assertEqual(status, 200)
        self.assertEqual(materials["assessment_id"], assessment_id)
        self.assertEqual(materials["goal"], "parent_material_selection")
        self.assertEqual(
            set(materials["buckets"]),
            {
                "confidence_or_warmup",
                "best_fit_daily_reading",
                "supported_challenge",
                "frustration_risk",
            },
        )
        self.assertEqual(
            materials["buckets"]["best_fit_daily_reading"]["range"],
            report["reading_recommendation"]["parent_material_guidance"]["best_fit_daily_reading"]["range"],
        )
        best_fit = materials["buckets"]["best_fit_daily_reading"]["materials"]
        self.assertGreaterEqual(len(best_fit), 1)
        self.assertEqual(best_fit[0]["fit_label"], "best_fit_daily_reading")
        self.assertIn("why_this_fits", best_fit[0])
        self.assertIn("parent_action", best_fit[0])


if __name__ == "__main__":
    unittest.main()
