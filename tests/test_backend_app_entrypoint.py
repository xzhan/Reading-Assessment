"""Tests for the backend command-line entrypoint."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class BackendAppEntrypointTest(unittest.TestCase):
    def test_backend_app_help_runs_from_repo_root(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "backend/app.py", "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Run the PET Writing backend.", result.stdout)


if __name__ == "__main__":
    unittest.main()
