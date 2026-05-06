"""Smoke tests for the served reading assessment app."""

from __future__ import annotations

import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from backend.pet_writing_api.server import create_server


class ReadingAppRouteTest(unittest.TestCase):
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

    def test_reading_app_route_serves_real_app_shell(self) -> None:
        with urllib.request.urlopen(f"{self.base_url}/app/reading", timeout=5) as response:
            html = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn("text/html", response.headers["Content-Type"])
        self.assertIn("data-reading-app", html)
        self.assertIn("Parent Reading Guide", html)
        self.assertIn("/api/v1/reading/assessments", html)
        self.assertIn("/next", html)
        self.assertIn("/responses", html)
        self.assertIn("/complete", html)
        self.assertIn("/materials", html)


if __name__ == "__main__":
    unittest.main()
