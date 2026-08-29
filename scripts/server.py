"""
Localhost Ingestion HTTP Server for LeetCode Lab.
Provides a secure loopback endpoint (127.0.0.1:8765/ingest) for receiving accepted
submissions from the browser userscript and routing them to the core Python engine.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import os
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from .engine.validator import SubmissionPayload, ValidationError, validate_submission
from .engine.problem_manager import ProblemManager, SolutionConflictError
from .engine.ledger_updater import DelimiterError
from .engine.statistics import DashboardUpdater
from .engine.git_manager import GitManager, GitSafetyError

# Maximum allowed payload size (1 MB)
MAX_PAYLOAD_BYTES = 1024 * 1024

# Allowed browser origins
ALLOWED_ORIGINS: Set[str] = {
    "https://leetcode.com",
    "https://leetcode.cn",
}

logger = logging.getLogger("leetcode_lab_server")

# Process-level lock: ensures only one ingest runs at a time.
# Prevents race conditions on the working tree and git operations.
_INGEST_LOCK = threading.Lock()


def configure_logging() -> None:
    """Configure structured logging for both interactive and launchd (file) operation.

    When running under launchd, stdout/stderr are redirected to log files.
    This sets up clean timestamped output that is readable in both terminal
    and log file contexts.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )


def log_startup(host: str, port: int, repo_root: Path, auto_push: bool) -> None:
    """Emit a structured startup banner to stdout (captured by launchd logs)."""
    print(f"[INFO] LeetCode Lab server starting", flush=True)
    print(f"[INFO] PID          : {os.getpid()}", flush=True)
    print(f"[INFO] Endpoint     : http://{host}:{port}/ingest", flush=True)
    print(f"[INFO] Repository   : {repo_root}", flush=True)
    print(f"[INFO] Auto-Push    : {'enabled (origin/main)' if auto_push else 'disabled'}", flush=True)
    print(f"[INFO] Press Ctrl+C to stop (or launchctl bootout to unload)", flush=True)


class IngestionRequestHandler(BaseHTTPRequestHandler):
    """Secure HTTP Request Handler for /ingest endpoint."""

    server_version = "LeetCodeLab/1.0"

    def __init__(
        self,
        *args,
        repo_root: Optional[Path] = None,
        allow_local_origin: bool = False,
        auto_commit: bool = True,
        auto_push: bool = False,
        **kwargs,
    ):
        self.repo_root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parent.parent
        self.allow_local_origin = allow_local_origin
        self.auto_commit = auto_commit
        self.auto_push = auto_push
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        """Custom clean logging to stderr."""
        sys.stderr.write(f"[{self.log_date_time_string()}] {self.address_string()} - {format % args}\n")

    def _send_json_response(self, status_code: int, data: Dict[str, Any], origin: Optional[str] = None) -> None:
        """Sends a JSON response with strict security headers."""
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))

        # Send CORS header if origin is valid
        if origin and self._is_origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(response_bytes)

    def _is_origin_allowed(self, origin: str) -> bool:
        """Validates request origin."""
        if not origin:
            return False
        clean_origin = origin.strip().rstrip("/")
        if clean_origin in ALLOWED_ORIGINS:
            return True
        if self.allow_local_origin and clean_origin in {"http://localhost", "http://127.0.0.1", "http://localhost:8765", "http://127.0.0.1:8765"}:
            return True
        return False

    def do_OPTIONS(self) -> None:
        """Handles CORS preflight requests."""
        if self.path != "/ingest":
            self._send_json_response(404, {"ok": False, "error": "Endpoint not found"})
            return

        origin = self.headers.get("Origin")
        if origin and not self._is_origin_allowed(origin):
            self._send_json_response(403, {"ok": False, "error": "Origin not allowed"})
            return

        self.send_response(204)
        if origin and self._is_origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        """Rejects GET requests."""
        origin = self.headers.get("Origin")
        if self.path == "/ingest":
            self._send_json_response(405, {"ok": False, "error": "Method Not Allowed. Use POST /ingest."}, origin=origin)
        elif self.path == "/":
            self._send_json_response(200, {"ok": True, "service": "LeetCode Lab Ingestion Server", "status": "running"}, origin=origin)
        else:
            self._send_json_response(404, {"ok": False, "error": "Endpoint not found"}, origin=origin)

    def do_POST(self) -> None:
        """Handles POST /ingest requests."""
        origin = self.headers.get("Origin")

        # 1. Path check
        if self.path != "/ingest":
            self._send_json_response(404, {"ok": False, "error": "Endpoint not found"}, origin=origin)
            return

        # 2. Origin check (when Origin header is supplied by browser)
        if origin and not self._is_origin_allowed(origin):
            self._send_json_response(403, {"ok": False, "error": f"Forbidden: Origin '{origin}' not allowed"}, origin=origin)
            return

        # 3. Content-Type check
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            self._send_json_response(415, {"ok": False, "error": "Unsupported Media Type. Content-Type must be application/json."}, origin=origin)
            return

        # 4. Content-Length & Size check
        content_length_str = self.headers.get("Content-Length")
        if not content_length_str:
            self._send_json_response(411, {"ok": False, "error": "Length Required: Missing Content-Length header"}, origin=origin)
            return

        try:
            content_length = int(content_length_str)
        except ValueError:
            self._send_json_response(400, {"ok": False, "error": "Invalid Content-Length header"}, origin=origin)
            return

        if content_length > MAX_PAYLOAD_BYTES:
            self._send_json_response(413, {"ok": False, "error": f"Payload Too Large (Max: {MAX_PAYLOAD_BYTES} bytes)"}, origin=origin)
            return

        # 5. Read body — cap actual read to MAX_PAYLOAD_BYTES regardless of Content-Length claim
        try:
            body_bytes = self.rfile.read(min(content_length, MAX_PAYLOAD_BYTES))
            if len(body_bytes) == 0:
                self._send_json_response(400, {"ok": False, "error": "Empty request body"}, origin=origin)
                return
            raw_payload = json.loads(body_bytes.decode("utf-8"))
        except json.JSONDecodeError as e:
            self._send_json_response(400, {"ok": False, "error": f"Malformed JSON: {str(e)}"}, origin=origin)
            return
        except Exception:
            self._send_json_response(400, {"ok": False, "error": "Failed to parse request body"}, origin=origin)
            return

        # 6. Validate Submission Payload
        try:
            payload: SubmissionPayload = validate_submission(raw_payload)
        except ValidationError as e:
            self._send_json_response(400, {"ok": False, "error": str(e)}, origin=origin)
            return
        except Exception:
            self._send_json_response(400, {"ok": False, "error": "Validation failed on input payload"}, origin=origin)
            return

        # 7. Ingest — serialized via lock to prevent concurrent git/filesystem races
        with _INGEST_LOCK:
            self._run_ingest(payload, origin)

    def _run_ingest(self, payload: SubmissionPayload, origin: Optional[str]) -> None:
        """
        Runs the full transactional ingest pipeline under the process lock.

        Transaction model:
          - Back up README.md and PROGRESS.md before any writes.
          - If dashboard update or Git operations fail after file writes, restore backups.
          - Never leaves README.md/PROGRESS.md in a partially-written state.
          - SolutionConflictError (identical code or changed code) is not a failure —
            the conflict is surfaced to the caller without rollback.
        """
        readme_file = self.repo_root / "README.md"
        progress_file = self.repo_root / "PROGRESS.md"

        # Snapshot dashboard files before any write (in-memory, no temp files needed)
        readme_backup: Optional[str] = None
        progress_backup: Optional[str] = None
        if readme_file.exists():
            readme_backup = readme_file.read_text(encoding="utf-8")
        if progress_file.exists():
            progress_backup = progress_file.read_text(encoding="utf-8")

        has_committed = False

        try:
            manager = ProblemManager(self.repo_root)
            result = manager.import_submission(payload, dry_run=False)

            updater = DashboardUpdater(self.repo_root)
            r_changed, p_changed, stats = updater.update_all()

            commit_msg = None
            if self.auto_commit:
                git_mgr = GitManager(self.repo_root)
                if git_mgr.is_git_repo():
                    git_mgr.stage_submission(payload)
                    commit_msg = git_mgr.format_commit_message(payload, result)
                    committed = git_mgr.commit(commit_msg)
                    if committed:
                        has_committed = True
                    if committed and self.auto_push:
                        git_mgr.push()

            status_msg = "imported" if (result.is_new_problem or result.is_new_language) else "updated"

            resp_data: Dict[str, Any] = {
                "ok": True,
                "status": status_msg,
                "problem_id": payload.problem_id,
                "slug": payload.slug,
                "title": payload.title,
                "difficulty": payload.difficulty,
                "language": payload.language,
                "canonical_dir": payload.canonical_dir_name,
                "actions": result.actions,
                "total_solved": stats.total_solved,
            }
            if commit_msg:
                resp_data["commit"] = commit_msg

            self._send_json_response(200, resp_data, origin=origin)

        except SolutionConflictError as e:
            # Conflict is surfaced as-is; no dashboard was written yet so no rollback needed
            self._send_json_response(409, {"ok": False, "error": str(e)}, origin=origin)

        except (DelimiterError, GitSafetyError, Exception) as e:
            # Restore dashboard files to pre-ingest state ONLY if we haven't committed yet.
            # If the commit succeeded but a later step (like push) failed, the commit must
            # remain intact and the working tree must match the commit.
            if not has_committed:
                try:
                    if readme_backup is not None:
                        readme_file.write_text(readme_backup, encoding="utf-8")
                    if progress_backup is not None:
                        progress_file.write_text(progress_backup, encoding="utf-8")
                except Exception as restore_err:
                    logger.error("Failed to restore dashboard backups after error: %s", restore_err)

            if isinstance(e, DelimiterError):
                self._send_json_response(500, {"ok": False, "error": f"Delimiter error in repository docs: {str(e)}"}, origin=origin)
            elif isinstance(e, GitSafetyError):
                self._send_json_response(500, {"ok": False, "error": f"Git Safety Error: {str(e)}"}, origin=origin)
            else:
                logger.error("Internal error during ingestion: %s", str(e), exc_info=True)
                self._send_json_response(500, {"ok": False, "error": "Internal laboratory processing error"}, origin=origin)



def make_handler_class(
    repo_root: Path,
    allow_local_origin: bool = False,
    auto_commit: bool = True,
    auto_push: bool = False,
):
    """Factory creating handler with custom repo_root, local origin, and git settings."""
    class CustomIngestionHandler(IngestionRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(
                *args,
                repo_root=repo_root,
                allow_local_origin=allow_local_origin,
                auto_commit=auto_commit,
                auto_push=auto_push,
                **kwargs,
            )
    return CustomIngestionHandler


def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    repo_root: Optional[Path] = None,
    allow_local_origin: bool = False,
    auto_commit: bool = True,
    auto_push: bool = False,
) -> HTTPServer:
    """Creates and starts the HTTPServer bound strictly to loopback."""
    if host != "127.0.0.1":
        raise ValueError(f"Security constraint violated: server may ONLY bind to 127.0.0.1, got '{host}'")

    root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parent.parent
    handler_class = make_handler_class(
        root,
        allow_local_origin=allow_local_origin,
        auto_commit=auto_commit,
        auto_push=auto_push,
    )
    server = HTTPServer((host, port), handler_class)
    return server
