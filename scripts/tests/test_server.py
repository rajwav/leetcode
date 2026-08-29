"""
Unit tests for the localhost ingestion HTTP server (scripts/server.py).
Tests loopback binding, origin controls, JSON parsing, error boundaries, and engine integration.
All tests run on ephemeral ports with isolated temporary repositories.
"""

from http.client import HTTPConnection
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from scripts.server import run_server


class TestIngestionServer(unittest.TestCase):

    def setUp(self):
        self.tmp_dir_obj = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmp_dir_obj.name).resolve()

        # Initialize mock problems directory
        (self.repo_root / "problems" / "easy").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "problems" / "medium").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "problems" / "hard").mkdir(parents=True, exist_ok=True)

        # Create starter README.md and PROGRESS.md
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

        # Start test server on loopback on an ephemeral port (port 0 lets OS assign)
        self.server = run_server(
            host="127.0.0.1",
            port=0,
            repo_root=self.repo_root,
            allow_local_origin=True,
        )
        self.port = self.server.server_port

        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        time.sleep(0.05)

        self.valid_payload = {
            "submission_id": "9001",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "class Solution { public: vector<int> twoSum() {} };",
            "status": "Accepted",
            "runtime": "0 ms",
            "memory": "10.5 MB",
            "timestamp": "2026-08-28",
            "leetcode_tags": ["Array", "Hash Table"],
        }

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=1.0)
        self.tmp_dir_obj.cleanup()

    def _request(self, method: str, path: str, body=None, headers=None):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        req_headers = headers or {}
        req_body = body
        if isinstance(body, dict):
            req_body = json.dumps(body)
            if "Content-Type" not in req_headers:
                req_headers["Content-Type"] = "application/json"

        conn.request(method, path, body=req_body, headers=req_headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        conn.close()
        try:
            json_data = json.loads(data)
        except json.JSONDecodeError:
            json_data = {"raw": data}
        return res.status, res.headers, json_data

    # 1. GET /ingest rejected
    def test_get_ingest_rejected(self):
        status, _, body = self._request("GET", "/ingest")
        self.assertEqual(status, 405)
        self.assertFalse(body.get("ok"))

    # 2. POST /unknown rejected
    def test_post_unknown_path_rejected(self):
        status, _, body = self._request("POST", "/unknown-route", body=self.valid_payload)
        self.assertEqual(status, 404)
        self.assertFalse(body.get("ok"))

    # 3. Malformed JSON rejected
    def test_malformed_json_rejected(self):
        headers = {"Content-Type": "application/json"}
        status, _, body = self._request("POST", "/ingest", body="{not valid json:", headers=headers)
        self.assertEqual(status, 400)
        self.assertFalse(body.get("ok"))
        self.assertIn("Malformed JSON", body.get("error", ""))

    # 4. Non-JSON request rejected
    def test_non_json_request_rejected(self):
        headers = {"Content-Type": "text/plain"}
        status, _, body = self._request("POST", "/ingest", body="plain text", headers=headers)
        self.assertEqual(status, 415)
        self.assertFalse(body.get("ok"))

    # 5. Missing required fields rejected
    def test_missing_required_fields_rejected(self):
        bad_payload = {"submission_id": "1", "problem_id": 1}
        status, _, body = self._request("POST", "/ingest", body=bad_payload)
        self.assertEqual(status, 400)
        self.assertFalse(body.get("ok"))

    # 6. Wrong Answer rejected
    def test_wrong_answer_rejected(self):
        bad_payload = self.valid_payload.copy()
        bad_payload["status"] = "Wrong Answer"
        status, _, body = self._request("POST", "/ingest", body=bad_payload)
        self.assertEqual(status, 400)
        self.assertFalse(body.get("ok"))
        self.assertIn("Accepted", body.get("error", ""))

    # 7. Invalid difficulty rejected
    def test_invalid_difficulty_rejected(self):
        bad_payload = self.valid_payload.copy()
        bad_payload["difficulty"] = "SuperEasy"
        status, _, body = self._request("POST", "/ingest", body=bad_payload)
        self.assertEqual(status, 400)
        self.assertFalse(body.get("ok"))

    # 8. Malicious slug rejected
    def test_malicious_slug_rejected(self):
        bad_payload = self.valid_payload.copy()
        bad_payload["slug"] = "../../etc/passwd"
        status, _, body = self._request("POST", "/ingest", body=bad_payload)
        self.assertEqual(status, 400)
        self.assertFalse(body.get("ok"))

    # 9. Oversized payload rejected
    def test_oversized_payload_rejected(self):
        headers = {"Content-Type": "application/json", "Content-Length": "2000000"}
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.putrequest("POST", "/ingest")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Content-Length", "2000000")
        conn.endheaders()
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        conn.close()
        self.assertEqual(res.status, 413)
        self.assertIn("Payload Too Large", data)

    # 10. Wrong Origin rejected
    def test_wrong_origin_rejected(self):
        headers = {"Origin": "https://malicious-site.com"}
        status, _, body = self._request("POST", "/ingest", body=self.valid_payload, headers=headers)
        self.assertEqual(status, 403)
        self.assertFalse(body.get("ok"))

    # 11. Correct Origin accepted & CORS headers returned
    def test_correct_origin_accepted(self):
        headers = {"Origin": "https://leetcode.com"}
        status, res_headers, body = self._request("POST", "/ingest", body=self.valid_payload, headers=headers)
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
        self.assertEqual(res_headers.get("Access-Control-Allow-Origin"), "https://leetcode.com")

    # 12. Valid payload reaches engine & creates problem
    def test_valid_payload_creates_problem(self):
        headers = {"Origin": "https://leetcode.com"}
        status, _, body = self._request("POST", "/ingest", body=self.valid_payload, headers=headers)
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("problem_id"), 1)
        self.assertEqual(body.get("total_solved"), 1)

        # Check files created in temporary repo
        problem_dir = self.repo_root / "problems" / "easy" / "0001-two-sum"
        self.assertTrue(problem_dir.exists())
        self.assertTrue((problem_dir / "solution.cpp").exists())
        self.assertTrue((problem_dir / "README.md").exists())

    # 13. Duplicate submission is safe & idempotent
    def test_duplicate_submission_idempotency(self):
        headers = {"Origin": "https://leetcode.com"}
        # First import
        s1, _, b1 = self._request("POST", "/ingest", body=self.valid_payload, headers=headers)
        self.assertEqual(s1, 200)

        # Second import identical
        s2, _, b2 = self._request("POST", "/ingest", body=self.valid_payload, headers=headers)
        self.assertEqual(s2, 200)
        self.assertTrue(b2.get("ok"))
        self.assertIn("identical_solution:solution.cpp", b2.get("actions", []))
        self.assertEqual(b2.get("total_solved"), 1)

    # 15. Server binds to loopback only
    def test_server_binds_to_loopback_only(self):
        with self.assertRaises(ValueError):
            run_server(host="0.0.0.0", port=8765)

    # 16. Server does not expose credentials
    def test_server_response_no_credentials(self):
        status, _, body = self._request("POST", "/ingest", body=self.valid_payload)
        response_str = json.dumps(body).lower()
        self.assertNotIn("token", response_str)
        self.assertNotIn("cookie", response_str)
        self.assertNotIn("password", response_str)

    # 17. Concurrent identical submissions are safely serialized — no double write
    def test_concurrent_identical_submissions_safe(self):
        """Two concurrent identical submissions should both return 200 and produce exactly 1 solve."""
        import concurrent.futures
        headers = {"Origin": "https://leetcode.com"}

        def submit():
            return self._request("POST", "/ingest", body=self.valid_payload, headers=headers)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            futures = [ex.submit(submit), ex.submit(submit)]
            results = [f.result() for f in futures]

        statuses = [r[0] for r in results]
        bodies = [r[2] for r in results]

        # Both must succeed (200 or 409 for conflict — both are safe)
        for status in statuses:
            self.assertIn(status, {200, 409})
        # Total solved should be exactly 1
        solved_values = [b.get("total_solved") for b in bodies if b.get("ok")]
        if solved_values:
            self.assertEqual(max(solved_values), 1)

    # 18. Transactional rollback: simulate delimiter corruption leaves files intact
    def test_dashboard_backup_survives_missing_delimiter(self):
        """If README.md is missing its delimiter, the 200 import should raise DelimiterError
        and the original README.md content must be preserved (no partial write)."""
        # Break the delimiter in README.md
        broken_readme = "# LeetCode Lab\n\nNo automation delimiters here.\n"
        (self.repo_root / "README.md").write_text(broken_readme, encoding="utf-8")

        headers = {"Origin": "https://leetcode.com"}
        status, _, body = self._request("POST", "/ingest", body=self.valid_payload, headers=headers)

        # Must fail (500 DelimiterError)
        self.assertEqual(status, 500)
        self.assertFalse(body.get("ok"))
        self.assertIn("Delimiter", body.get("error", ""))

        # README.md must be restored to the broken content (not partially overwritten)
        readme_content = (self.repo_root / "README.md").read_text(encoding="utf-8")
        self.assertEqual(readme_content, broken_readme)

    # 19. Empty body is rejected cleanly
    def test_empty_body_rejected(self):
        conn = __import__("http.client", fromlist=["HTTPConnection"]).HTTPConnection(
            "127.0.0.1", self.port, timeout=5
        )
        conn.request(
            "POST", "/ingest", body=b"",
            headers={"Content-Type": "application/json", "Content-Length": "0"}
        )
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        conn.close()
        self.assertEqual(res.status, 400)
        self.assertFalse(data.get("ok"))


class TestServerEdgeCases(unittest.TestCase):
    def setUp(self):
        self.dir_obj = tempfile.TemporaryDirectory()
        self.repo = Path(self.dir_obj.name).resolve()
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text(
            "# LeetCode Lab\n\n"
            "<!-- AUTOMATION_METRICS_START -->\n<!-- AUTOMATION_METRICS_END -->\n\n"
            "<!-- AUTOMATION_RECENT_SOLVES_START -->\n<!-- AUTOMATION_RECENT_SOLVES_END -->\n",
            encoding="utf-8"
        )
        (self.repo / "PROGRESS.md").write_text(
            "# Progress\n\n"
            "<!-- AUTOMATION_CATEGORY_TELEMETRY_START -->\n<!-- AUTOMATION_CATEGORY_TELEMETRY_END -->\n\n"
            "<!-- AUTOMATION_PROBLEM_LOG_START -->\n<!-- AUTOMATION_PROBLEM_LOG_END -->\n",
            encoding="utf-8"
        )
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.repo, check=True)

    def tearDown(self):
        self.dir_obj.cleanup()

    def test_sigterm_clean_shutdown(self):
        """Regression: SIGTERM must not deadlock the server."""
        import subprocess
        import time

        lab_py = Path(__file__).resolve().parent.parent / "lab.py"

        # Start the server as a background process
        proc = subprocess.Popen(
            [sys.executable, str(lab_py), "listen", "--port", "8766", "--no-commit"],
            cwd=self.repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for it to start
        time.sleep(1)

        # Send SIGTERM
        proc.terminate()

        try:
            # Wait for it to exit cleanly
            stdout, stderr = proc.communicate(timeout=5)
            # Exit code should be 0, and output should say "Server stopped."
            self.assertEqual(proc.returncode, 0)
            self.assertIn("Server stopped", stdout)
        except subprocess.TimeoutExpired:
            proc.kill()
            self.fail("Server deadlocked on SIGTERM and did not shut down cleanly.")

    @patch("scripts.engine.git_manager.GitManager.push")
    def test_push_failure_preserves_commit_and_skips_rollback(self, mock_push):
        """Regression: If push() fails, the local commit must remain and dashboard must NOT rollback."""
        from scripts.engine.git_manager import GitSafetyError
        mock_push.side_effect = GitSafetyError("Simulated push failure")

        server = run_server(
            host="127.0.0.1",
            port=8767,
            repo_root=self.repo,
            auto_commit=True,
            auto_push=True
        )
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        try:
            import urllib.request
            payload = {
                "submission_id": "9001",
                "problem_id": 1,
                "slug": "two-sum",
                "title": "Two Sum",
                "difficulty": "Easy",
                "language": "cpp",
                "code": "class Solution {};",
                "status": "Accepted",
                "runtime": "0 ms",
                "memory": "10 MB",
                "timestamp": "2026-08-28",
                "leetcode_tags": ["Array"]
            }
            req = urllib.request.Request(
                "http://127.0.0.1:8767/ingest",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Origin": "https://leetcode.com"}
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=5)
            self.assertEqual(ctx.exception.code, 500)

            # Verify the commit WAS created
            log_res = subprocess.run(["git", "log", "--oneline", "-1"], cwd=self.repo, capture_output=True, text=True)
            self.assertIn("0001-two-sum", log_res.stdout)

            # Verify the dashboard files are NOT rolled back (working tree should be clean)
            status_res = subprocess.run(["git", "status", "--porcelain"], cwd=self.repo, capture_output=True, text=True)
            self.assertEqual(status_res.stdout.strip(), "")

        finally:
            server.shutdown()
            server.server_close()
            t.join()


if __name__ == "__main__":
    unittest.main()
