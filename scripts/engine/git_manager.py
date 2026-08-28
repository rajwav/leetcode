"""
Git Manager module for LeetCode Lab.
Provides boundary-safe, deterministic Git commit authoring and pushing using
existing local authentication.

Safety guarantees:
  - Never stages arbitrary repository files.
  - Allowlist-only staging with pattern-based forbidden file rejection.
  - Detects unexpected pre-existing staged changes and aborts before automation stages.
  - Verifies current branch and remote URL before any push.
  - Detects remote divergence and refuses non-fast-forward pushes.
  - Never force-pushes, never resets, never cleans.
  - Avoids empty commits.
  - All git invocations use argument arrays (no shell interpolation).
"""

from pathlib import Path
import re
import subprocess
from typing import List, Optional

from .validator import SubmissionPayload
from .problem_manager import ImportResult, LANGUAGE_DISPLAY_NAMES


# Patterns that must NEVER be committed — matched against the file basename
DISALLOWED_FILE_PATTERNS = {
    r"^\.env",
    r".*\.pem$",
    r".*\.key$",
    r"^id_rsa",
    r".*\.token$",
    r".*\.DS_Store$",
    r".*__pycache__.*",
    r".*\.pyc$",
    r".*\.secret$",
    r".*credentials.*",
    r".*password.*",
    r".*cookie.*",
}

# Directories/files allowed for automated staging (relative to repo root)
ALLOWED_STAGING_PREFIXES = (
    "problems/easy/",
    "problems/medium/",
    "problems/hard/",
    "README.md",
    "PROGRESS.md",
    "patterns/",
    "data-structures/",
    "algorithms/",
)


class GitSafetyError(Exception):
    """Raised when a Git safety invariant is violated."""
    pass


class GitManager:
    """Manages Git repository staging, deterministic commit authoring, and remote pushing."""

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()

    def _run_git(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Executes a git command inside the repository root using an argument array (no shell)."""
        cmd = ["git"] + args
        return subprocess.run(
            cmd,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=check,
        )

    def is_git_repo(self) -> bool:
        """Checks if the repository root is an initialized Git work tree."""
        res = self._run_git(["rev-parse", "--is-inside-work-tree"], check=False)
        return res.returncode == 0 and res.stdout.strip() == "true"

    def get_current_branch(self) -> Optional[str]:
        """Returns the current branch name, or None if in detached HEAD state."""
        res = self._run_git(["symbolic-ref", "--short", "HEAD"], check=False)
        if res.returncode != 0:
            return None
        return res.stdout.strip() or None

    def get_remote_url(self, remote: str = "origin") -> Optional[str]:
        """Returns the push URL of the named remote, or None if not configured."""
        res = self._run_git(["remote", "get-url", "--push", remote], check=False)
        if res.returncode != 0:
            return None
        return res.stdout.strip() or None

    def format_commit_message(self, payload: SubmissionPayload, result: ImportResult) -> str:
        """Generates a clean, deterministic commit message.

        Uses LANGUAGE_DISPLAY_NAMES for the exact display name of the submitted language
        (e.g. "cpp" → "C++", "python3" → "Python"). Never derives the name from sorted
        list position, which is order-dependent.
        """
        lang_tag = payload.language.lower()
        # LANGUAGE_DISPLAY_NAMES is the authoritative mapping: "cpp" -> "C++", etc.
        display_lang = LANGUAGE_DISPLAY_NAMES.get(payload.language, payload.language)

        if result.is_new_problem:
            return f"feat(problems): add {payload.canonical_dir_name} [{payload.difficulty}] [{lang_tag}]"
        elif result.is_new_language:
            return f"feat(problems): add {display_lang} solution for {payload.canonical_dir_name}"
        else:
            return f"refactor(problems): update {display_lang} solution for {payload.canonical_dir_name}"

    def validate_paths_for_staging(self, rel_paths: List[str]) -> None:
        """Ensures all staged files conform to security and location constraints."""
        for path_str in rel_paths:
            basename = Path(path_str).name
            for pat in DISALLOWED_FILE_PATTERNS:
                if re.match(pat, basename, re.IGNORECASE):
                    raise GitSafetyError(
                        f"Security violation: Attempted to stage forbidden file '{path_str}'"
                    )

            is_allowed = any(
                path_str.startswith(prefix) or path_str == prefix.rstrip("/")
                for prefix in ALLOWED_STAGING_PREFIXES
            )
            if not is_allowed:
                raise GitSafetyError(
                    f"Scope violation: Path '{path_str}' is outside allowed automation boundaries"
                )

    def check_no_foreign_staged_files(self) -> None:
        """
        Aborts if files that do NOT belong to the automation allowlist are already staged.
        Prevents the automated commit from sweeping in unrelated user changes.
        """
        res = self._run_git(["diff", "--cached", "--name-only"])
        already_staged = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        if not already_staged:
            return
        for path_str in already_staged:
            is_allowed = any(
                path_str.startswith(prefix) or path_str == prefix.rstrip("/")
                for prefix in ALLOWED_STAGING_PREFIXES
            )
            if not is_allowed:
                raise GitSafetyError(
                    f"Pre-existing staged changes detected outside automation boundaries: "
                    f"'{path_str}'. Automation aborted to protect your staged work. "
                    f"Please commit or unstage your changes first."
                )

    def stage_submission(
        self,
        payload: SubmissionPayload,
        additional_files: Optional[List[str]] = None,
    ) -> List[str]:
        """Stages canonical problem directory and updated docs, validating safety first."""
        # Safety: abort if unrelated files are already staged
        self.check_no_foreign_staged_files()

        rel_dir = payload.canonical_relative_path
        staged_targets = [
            rel_dir,
            "README.md",
            "PROGRESS.md",
        ]
        if additional_files:
            staged_targets.extend(additional_files)

        self.validate_paths_for_staging(staged_targets)
        self._run_git(["add"] + staged_targets)
        return staged_targets

    def commit(self, message: str) -> bool:
        """Commits staged changes if any exist. Returns False (no-op) if nothing staged."""
        status_res = self._run_git(["diff", "--cached", "--name-only"])
        staged = [line.strip() for line in status_res.stdout.splitlines() if line.strip()]

        if not staged:
            return False

        # Final safety check on what is actually staged at commit time
        self.validate_paths_for_staging(staged)
        self._run_git(["commit", "-m", message])
        return True

    def push(self, remote: str = "origin", branch: str = "main") -> bool:
        """
        Pushes local commits to the configured remote branch.

        Safety checks performed before push:
          1. Verifies we are currently on the expected branch.
          2. Verifies the remote URL is configured.
          3. Fetches remote state and checks for divergence (refuses non-fast-forward).
          4. Never force-pushes.
        """
        # 1. Branch check
        current_branch = self.get_current_branch()
        if current_branch != branch:
            raise GitSafetyError(
                f"Branch mismatch: expected '{branch}', currently on '{current_branch}'. "
                f"Refusing to push."
            )

        # 2. Remote URL check
        remote_url = self.get_remote_url(remote)
        if not remote_url:
            raise GitSafetyError(
                f"Remote '{remote}' is not configured or has no push URL."
            )

        # 3. Fetch remote state to detect divergence (non-destructive)
        fetch_res = self._run_git(["fetch", remote, branch], check=False)
        if fetch_res.returncode == 0:
            remote_ref = f"{remote}/{branch}"
            behind_res = self._run_git(
                ["rev-list", "--count", f"HEAD..{remote_ref}"], check=False
            )
            if behind_res.returncode == 0:
                behind_count = int(behind_res.stdout.strip() or "0")
                if behind_count > 0:
                    raise GitSafetyError(
                        f"Remote '{remote}/{branch}' has {behind_count} commit(s) not in local. "
                        f"Pull first to avoid non-fast-forward. Refusing to push."
                    )

        # 4. Push (standard, no force)
        res = self._run_git(["push", remote, branch], check=False)
        if res.returncode != 0:
            stderr = res.stderr.strip()
            if "Authentication" in stderr or "authentication" in stderr or "403" in stderr:
                raise GitSafetyError(
                    f"Push authentication failed for '{remote}/{branch}'. "
                    f"Ensure `gh auth login` or SSH keys are configured. Details: {stderr}"
                )
            raise GitSafetyError(
                f"Git push to '{remote}/{branch}' failed: {stderr}"
            )
        return True
