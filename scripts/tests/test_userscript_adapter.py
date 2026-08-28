"""
Unit tests for the Userscript Adapter simulation and payload generation.
Verifies contract compatibility between browser output and localhost server.
All tests run in isolated temporary repositories.
"""

from http.client import HTTPConnection
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from scripts.server import run_server


class TestUserscriptAdapter(unittest.TestCase):

    def setUp(self):
        self.tmp_dir_obj = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmp_dir_obj.name).resolve()

        (self.repo_root / "problems" / "easy").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "problems" / "medium").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "problems" / "hard").mkdir(parents=True, exist_ok=True)

        (self.repo_root / "README.md").write_text(
            "# LeetCode Lab\n\n"
            "<!-- AUTOMATION_METRICS_START -->\n<!-- AUTOMATION_METRICS_END -->\n\n"
            "<!-- AUTOMATION_RECENT_SOLVES_START -->\n<!-- AUTOMATION_RECENT_SOLVES_END -->\n\n"
            "<!-- AUTOMATION_MILESTONES_START -->\n<!-- AUTOMATION_MILESTONES_END -->\n",
            encoding="utf-8",
        )
        (self.repo_root / "PROGRESS.md").write_text(
            "# Progress\n\n"
            "<!-- AUTOMATION_CATEGORY_TELEMETRY_START -->\n<!-- AUTOMATION_CATEGORY_TELEMETRY_END -->\n\n"
            "<!-- AUTOMATION_PROBLEM_LOG_START -->\n<!-- AUTOMATION_PROBLEM_LOG_END -->\n",
            encoding="utf-8",
        )

        self.server = run_server(host="127.0.0.1", port=0, repo_root=self.repo_root)
        self.port = self.server.server_port
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        time.sleep(0.05)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=1.0)
        self.tmp_dir_obj.cleanup()

    def _post(self, payload: dict, origin: str = "https://leetcode.com"):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {
            "Content-Type": "application/json",
            "Origin": origin,
        }
        conn.request("POST", "/ingest", body=json.dumps(payload), headers=headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        conn.close()
        try:
            return res.status, json.loads(data)
        except json.JSONDecodeError:
            return res.status, {"raw": data}

    # 1. Accepted submission
    def test_accepted_submission_simulation(self):
        payload = {
            "submission_id": "10001",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "class Solution { public: vector<int> twoSum() {} };",
            "status": "Accepted",
            "runtime": "0 ms",
            "memory": "10.5 MB",
            "leetcode_tags": ["Array", "Hash Table"],
        }
        status, body = self._post(payload)
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["problem_id"], 1)

    # 2. Wrong Answer rejected
    def test_wrong_answer_rejected(self):
        payload = {
            "submission_id": "10002",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// wrong code",
            "status": "Wrong Answer",
        }
        status, body = self._post(payload)
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])

    # 3. Runtime Error rejected
    def test_runtime_error_rejected(self):
        payload = {
            "submission_id": "10003",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// error code",
            "status": "Runtime Error",
        }
        status, body = self._post(payload)
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])

    # 4. Missing submission ID rejected
    def test_missing_submission_id(self):
        payload = {
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// code",
            "status": "Accepted",
        }
        status, body = self._post(payload)
        self.assertEqual(status, 400)

    # 5. Missing source code rejected
    def test_missing_source_code(self):
        payload = {
            "submission_id": "10005",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "",
            "status": "Accepted",
        }
        status, body = self._post(payload)
        self.assertEqual(status, 400)

    # 6. Missing problem metadata rejected
    def test_missing_problem_metadata(self):
        payload = {
            "submission_id": "10006",
            "code": "print(1)",
            "language": "python3",
            "status": "Accepted",
        }
        status, body = self._post(payload)
        self.assertEqual(status, 400)

    # 7. Duplicate submission handled safely
    def test_duplicate_submission_safety(self):
        payload = {
            "submission_id": "10007",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// code",
            "status": "Accepted",
        }
        # First send
        s1, b1 = self._post(payload)
        self.assertEqual(s1, 200)

        # Second send identical
        s2, b2 = self._post(payload)
        self.assertEqual(s2, 200)
        self.assertTrue(b2["ok"])


if __name__ == "__main__":
    unittest.main()
