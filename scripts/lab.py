#!/usr/bin/env python3
"""
LeetCode Lab CLI
Master command-line interface for the LeetCode DSA laboratory.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.engine.validator import SubmissionPayload, ValidationError, validate_submission
from scripts.engine.problem_manager import ProblemManager, SolutionConflictError, DelimiterError


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
        return

    try:
        res = manager.import_submission(payload, dry_run=False)
        print(f"✅ Successfully Processed #{payload.problem_id} {payload.title}:")
        print(f"   • Directory: {res.problem_dir.relative_to(PROJECT_ROOT)}")
        for act in res.actions:
            print(f"   • Action:    {act}")
        print(f"   • Languages: {', '.join(res.languages)}")
    except SolutionConflictError as e:
        print(f"⚠️ Conflict Error: {e}", file=sys.stderr)
        sys.exit(1)
    except DelimiterError as e:
        print(f"❌ Delimiter Error: {e}", file=sys.stderr)
        sys.exit(1)


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
    """Starts localhost ingestion server (Phase 6)."""
    print("ℹ️ Localhost ingestion server will be initialized in Phase 6.")


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
    p_import.add_argument("--no-push", action="store_true", help="Skip Git push")

    # test
    p_test = subparsers.add_parser("test", help="Run automated test suite")
    p_test.add_argument("-v", "--verbose", action="store_true", help="Verbose test output")

    # listen
    p_listen = subparsers.add_parser("listen", help="Start local ingestion HTTP server")
    p_listen.add_argument("--port", type=int, default=8765, help="Port to listen on (default: 8765)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "validate":
        cmd_validate(args)
    elif args.command == "import":
        cmd_import(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "listen":
        cmd_listen(args)


if __name__ == "__main__":
    main()
