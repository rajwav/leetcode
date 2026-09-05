#!/usr/bin/env python3
"""
LeetCode Lab CLI
Master command-line interface for the LeetCode DSA laboratory.
"""

import argparse
import json
import signal
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.engine.validator import SubmissionPayload, ValidationError, validate_submission
from scripts.engine.problem_manager import ProblemManager, DelimiterError
from scripts.engine.statistics import RepositoryScanner, DashboardUpdater
from scripts.engine.git_manager import GitManager, GitSafetyError


def load_payload_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    """Loads and parses raw JSON payload from file, string argument, or stdin."""
    if getattr(args, "file", None):
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ Error: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON in {file_path}: {e}", file=sys.stderr)
            sys.exit(1)

    if getattr(args, "json_str", None):
        try:
            return json.loads(args.json_str)
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON string: {e}", file=sys.stderr)
            sys.exit(1)

    # If stdin has data (and not a tty)
    if not sys.stdin.isatty():
        try:
            content = sys.stdin.read()
            if content.strip():
                return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON from stdin: {e}", file=sys.stderr)
            sys.exit(1)

    print("❌ Error: No input payload provided. Use --file <path>, --json '<json>', or pipe via stdin.", file=sys.stderr)
    sys.exit(1)


def cmd_validate(args: argparse.Namespace) -> None:
    """Validates a submission payload without writing anything to disk."""
    raw = load_payload_from_args(args)
    try:
        payload = validate_submission(raw)
        print(f"✅ Payload Validated Successfully:")
        print(f"   • Problem:     #{payload.problem_id} {payload.title}")
        print(f"   • Difficulty:  {payload.difficulty}")
        print(f"   • Language:    {payload.language} (.{payload.extension})")
        print(f"   • Target Path: {payload.canonical_relative_path}")
        print(f"   • Status:      {payload.status}")
        if payload.runtime:
            print(f"   • Runtime:     {payload.runtime}")
        if payload.memory:
            print(f"   • Memory:      {payload.memory}")
        if payload.leetcode_tags:
            print(f"   • Tags:        {', '.join(payload.leetcode_tags)}")
    except ValidationError as e:
        print(f"❌ Validation Failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_import(args: argparse.Namespace) -> None:
    """Imports a validated submission into the canonical repository structure."""
    raw = load_payload_from_args(args)
    try:
        payload = validate_submission(raw)
    except ValidationError as e:
        print(f"❌ Validation Failed: {e}", file=sys.stderr)
        sys.exit(1)

    manager = ProblemManager(PROJECT_ROOT)

    if args.dry_run:
        print("🔍 [DRY RUN] Ingestion Preview (No disk changes made):")
        print(f"   • Problem:        #{payload.problem_id} {payload.title}")
        print(f"   • Difficulty:     {payload.difficulty}")
        print(f"   • Canonical Dir:  {payload.canonical_relative_path}")
        print(f"   • Solution File:  {payload.canonical_relative_path}solution.{payload.extension}")
        print(f"   • Problem README: {payload.canonical_relative_path}README.md")
        target_dir = manager.get_canonical_dir(payload)
        sol_file = target_dir / f"solution.{payload.extension}"
        print(f"   • Action Plan:")
        if not target_dir.exists():
            print(f"     + Create directory {payload.canonical_relative_path}")
            print(f"     + Create solution file solution.{payload.extension}")
            print(f"     + Create problem README.md")
        else:
            if sol_file.exists():
                print(f"     = Check existing solution.{payload.extension} for idempotency/conflict")
            else:
                print(f"     + Co-locate new language solution.{payload.extension}")
            print(f"     + Update problem README.md (preserve manual notes)")
        print(f"     + Recalculate repository statistics and update README.md / PROGRESS.md")
        if not args.no_commit:
            print(f"     + Stage {payload.canonical_relative_path}, README.md, PROGRESS.md and commit")
            if args.push:
                print(f"     + Push commit to origin/main")
        return

    try:
        res = manager.import_submission(payload, dry_run=False)
        print(f"✅ Successfully Processed #{payload.problem_id} {payload.title}:")
        print(f"   • Directory: {res.problem_dir.relative_to(PROJECT_ROOT)}")
        for act in res.actions:
            print(f"   • Action:    {act}")
        print(f"   • Languages: {', '.join(res.languages)}")

        # Automatically update repository dashboards and ledgers
        updater = DashboardUpdater(PROJECT_ROOT)
        r_changed, p_changed, stats = updater.update_all()
        if r_changed:
            print("   • Updated:   README.md (Metrics, Recent Solves, Milestones)")
        if p_changed:
            print("   • Updated:   PROGRESS.md (Category Telemetry, Master Log)")

        # Git operations
        if not args.no_commit:
            git_mgr = GitManager(PROJECT_ROOT)
            if git_mgr.is_git_repo():
                git_mgr.stage_submission(payload)
                commit_msg = git_mgr.format_commit_message(payload, res)
                committed = git_mgr.commit(commit_msg)
                if committed:
                    print(f"   • Git Commit: {commit_msg}")
                    if args.push:
                        git_mgr.push()
                        print("   • Git Push:   Pushed to origin/main")


    except DelimiterError as e:
        print(f"❌ Delimiter Error: {e}", file=sys.stderr)
        sys.exit(1)
    except GitSafetyError as e:
        print(f"❌ Git Safety Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_stats(args: argparse.Namespace) -> None:
    """Displays real repository statistics calculated from problems/."""
    scanner = RepositoryScanner(PROJECT_ROOT)
    stats = scanner.scan()

    print("⚡ LeetCode Lab Statistics")
    print("───────────────────────────────")
    print(f"Total Solved : {stats.total_solved}")
    print(f"🟢 Easy      : {stats.easy_count}")
    print(f"🟡 Medium    : {stats.medium_count}")
    print(f"🔴 Hard      : {stats.hard_count}")
    print("\n💻 Languages:")
    if stats.language_counts:
        for lang, count in stats.language_counts.items():
            print(f"  • {lang:12}: {count}")
    else:
        print("  None yet")

    print("\n🏆 Milestones:")
    for milestone, reached in stats.milestones.items():
        symbol = "●" if reached else "○"
        status = "Completed" if reached else "Upcoming"
        print(f"  {milestone:4d} {symbol} ({status})")


def cmd_test(args: argparse.Namespace) -> None:
    """Runs the test suite."""
    import unittest
    test_dir = PROJECT_ROOT / "scripts" / "tests"
    suite = unittest.defaultTestLoader.discover(str(test_dir), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


def cmd_listen(args: argparse.Namespace) -> None:
    """Starts localhost ingestion HTTP server.

    Designed to run correctly both interactively (Terminal) and as a
    launchd background agent. Uses structured log output compatible with
    launchd's StandardOutPath/StandardErrorPath log files.
    """
    import socket
    from scripts.server import run_server, configure_logging, log_startup

    configure_logging()

    port = args.port
    host = "127.0.0.1"

    # Build server (bind to port) before setting up signal handlers
    try:
        server = run_server(
            host=host,
            port=port,
            repo_root=PROJECT_ROOT,
            auto_commit=not args.no_commit,
            auto_push=args.push,
        )
    except OSError as e:
        if e.errno == 48 or "Address already in use" in str(e):
            print(
                f"[ERROR] Port {port} is already in use. "
                f"Another LeetCode Lab server may be running.",
                file=sys.stderr,
                flush=True,
            )
            print(
                f"[ERROR] Check: lsof -i :{port}",
                file=sys.stderr,
                flush=True,
            )
            print(
                f"[ERROR] Status: ./scripts/status_launchd.sh",
                file=sys.stderr,
                flush=True,
            )
            sys.exit(1)
        raise

    # Register SIGTERM handler for clean launchd shutdown.
    # launchd sends SIGTERM before SIGKILL when stopping the agent.
    # We MUST call server.shutdown() in a separate thread. If called from the
    # signal handler (which runs in the main thread), it will deadlock waiting
    # for serve_forever() to terminate, which it cannot do because the main
    # thread is blocked in the signal handler.
    def _handle_sigterm(signum: int, frame: object) -> None:
        print("[INFO] Received SIGTERM — shutting down gracefully.", flush=True)
        import threading
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _handle_sigterm)

    log_startup(host, port, PROJECT_ROOT, args.push)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Keyboard interrupt received — shutting down.", flush=True)
    finally:
        server.shutdown()
        server.server_close()
        print("[INFO] Server stopped.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lab.py",
        description="LeetCode Lab CLI — Local-First Automation Engine",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate a submission payload")
    p_validate.add_argument("--file", "-f", help="Path to JSON payload file")
    p_validate.add_argument("--json", "-j", dest="json_str", help="Raw JSON payload string")

    # import
    p_import = subparsers.add_parser("import", help="Import an accepted LeetCode submission")
    p_import.add_argument("--file", "-f", help="Path to JSON payload file")
    p_import.add_argument("--json", "-j", dest="json_str", help="Raw JSON payload string")
    p_import.add_argument("--dry-run", action="store_true", help="Simulate import without modifying files")
    p_import.add_argument("--no-commit", action="store_true", help="Skip Git commit")
    p_import.add_argument("--push", action="store_true", help="Push commit to origin/main")

    # stats
    p_stats = subparsers.add_parser("stats", help="Display aggregated repository statistics")

    # test
    p_test = subparsers.add_parser("test", help="Run automated test suite")
    p_test.add_argument("-v", "--verbose", action="store_true", help="Verbose test output")

    # listen
    p_listen = subparsers.add_parser("listen", help="Start local ingestion HTTP server")
    p_listen.add_argument("--port", type=int, default=8765, help="Port to listen on (default: 8765)")
    p_listen.add_argument("--no-commit", action="store_true", help="Disable automatic Git commits on ingest")
    p_listen.add_argument("--push", action="store_true", help="Automatically push commits to remote")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "validate":
        cmd_validate(args)
    elif args.command == "import":
        cmd_import(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "listen":
        cmd_listen(args)


if __name__ == "__main__":
    main()
