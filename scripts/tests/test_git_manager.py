"""
Unit tests for GitManager (scripts/engine/git_manager.py).
Tests staging validation, forbidden file rejection, commit authoring, and repo detection.
All tests run inside isolated temporary Git repositories.
"""

from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.engine.git_manager import GitManager, GitSafetyError
from scripts.engine.problem_manager import ImportResult
from scripts.engine.validator import validate_submission


class TestGitManager(unittest.TestCase):

    def setUp(self):
        self.tmp_dir_obj = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmp_dir_obj.name).resolve()

        # Initialize real temporary Git repository
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Engineer"], cwd=self.repo_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo_root, check=True, capture_output=True)

        # Create starter directories
        (self.repo_root / "problems" / "easy").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "README.md").write_text("# Test Repo\n", encoding="utf-8")
        (self.repo_root / "PROGRESS.md").write_text("# Progress\n", encoding="utf-8")

        # Initial commit
        subprocess.run(["git", "add", "."], cwd=self.repo_root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "chore: initial test commit"], cwd=self.repo_root, check=True, capture_output=True)

        self.git_mgr = GitManager(self.repo_root)

    def tearDown(self):
        self.tmp_dir_obj.cleanup()

    # 1. Repository detection
    def test_is_git_repo(self):
        self.assertTrue(self.git_mgr.is_git_repo())

        # Non-repo folder
        with tempfile.TemporaryDirectory() as non_repo:
            mgr = GitManager(Path(non_repo))
            self.assertFalse(mgr.is_git_repo())

    # 2. Commit message formatting for new problem
    def test_format_commit_message_new_problem(self):
        payload = validate_submission({
            "submission_id": "1",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// cpp code",
            "status": "Accepted",
        })
        prob_dir = self.repo_root / "problems" / "easy" / "0001-two-sum"
        res = ImportResult(
            problem_dir=prob_dir,
            solution_file=prob_dir / "solution.cpp",
            readme_file=prob_dir / "README.md",
            is_new_problem=True,
            is_new_language=True,
            languages=["C++"],
            actions=["create_directory", "create_solution:solution.cpp"],
        )
        msg = self.git_mgr.format_commit_message(payload, res)
        self.assertEqual(msg, "feat(problems): add 0001-two-sum [Easy] [cpp]")

    # 3. Commit message formatting for new language
    def test_format_commit_message_new_language(self):
        payload = validate_submission({
            "submission_id": "2",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "python3",
            "code": "# py code",
            "status": "Accepted",
        })
        prob_dir = self.repo_root / "problems" / "easy" / "0001-two-sum"
        res = ImportResult(
            problem_dir=prob_dir,
            solution_file=prob_dir / "solution.py",
            readme_file=prob_dir / "README.md",
            is_new_problem=False,
            is_new_language=True,
            languages=["C++", "Python"],
            actions=["colocate_solution:solution.py"],
        )
        msg = self.git_mgr.format_commit_message(payload, res)
        self.assertEqual(msg, "feat(problems): add Python solution for 0001-two-sum")

    # 4. Commit message formatting for solution refactor
    def test_format_commit_message_refactor(self):
        payload = validate_submission({
            "submission_id": "3",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// new cpp code",
            "status": "Accepted",
        })
        prob_dir = self.repo_root / "problems" / "easy" / "0001-two-sum"
        res = ImportResult(
            problem_dir=prob_dir,
            solution_file=prob_dir / "solution.cpp",
            readme_file=prob_dir / "README.md",
            is_new_problem=False,
            is_new_language=False,
            languages=["C++"],
            actions=["update_solution:solution.cpp"],
        )
        msg = self.git_mgr.format_commit_message(payload, res)
        self.assertEqual(msg, "refactor(problems): update C++ solution for 0001-two-sum")

    # 5. Staging validation prevents forbidden files (.env, credentials)
    def test_forbidden_file_staging_rejection(self):
        with self.assertRaises(GitSafetyError):
            self.git_mgr.validate_paths_for_staging([".env", "problems/easy/0001-two-sum/solution.cpp"])

        with self.assertRaises(GitSafetyError):
            self.git_mgr.validate_paths_for_staging(["id_rsa", "problems/easy/0001-two-sum/solution.cpp"])

        with self.assertRaises(GitSafetyError):
            self.git_mgr.validate_paths_for_staging(["secret.pem"])

    # 6. Staging validation prevents files outside allowed boundaries
    def test_outside_boundary_staging_rejection(self):
        with self.assertRaises(GitSafetyError):
            self.git_mgr.validate_paths_for_staging(["scripts/server.py"])

    # 7. Safe stage and commit execution
    def test_stage_and_commit_execution(self):
        # Create problem files on disk
        prob_dir = self.repo_root / "problems" / "easy" / "0001-two-sum"
        prob_dir.mkdir(parents=True, exist_ok=True)
        (prob_dir / "solution.cpp").write_text("class Solution {};", encoding="utf-8")
        (prob_dir / "README.md").write_text("# Two Sum\n", encoding="utf-8")

        payload = validate_submission({
            "submission_id": "1",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "class Solution {};",
            "status": "Accepted",
        })

        self.git_mgr.stage_submission(payload)
        committed = self.git_mgr.commit("feat(problems): add 0001-two-sum [Easy] [cpp]")
        self.assertTrue(committed)

        # Verify git log
        log_res = subprocess.run(["git", "log", "-1", "--oneline"], cwd=self.repo_root, capture_output=True, text=True)
        self.assertIn("feat(problems): add 0001-two-sum [Easy] [cpp]", log_res.stdout)

    # 8. No commit when working tree is clean
    def test_commit_noop_when_clean(self):
        committed = self.git_mgr.commit("feat: noop")
        self.assertFalse(committed)

    # 9. get_current_branch returns correct branch name
    def test_get_current_branch(self):
        branch = self.git_mgr.get_current_branch()
        self.assertEqual(branch, "main")

    # 10. get_remote_url returns None when no remote configured
    def test_get_remote_url_no_remote(self):
        url = self.git_mgr.get_remote_url("origin")
        self.assertIsNone(url)

    # 11. check_no_foreign_staged_files passes when nothing staged
    def test_no_foreign_staged_files_clean(self):
        # Should not raise when nothing is staged
        self.git_mgr.check_no_foreign_staged_files()

    # 12. check_no_foreign_staged_files raises when unrelated file is staged
    def test_foreign_staged_file_detected(self):
        # Stage a file outside allowed prefixes
        foreign_file = self.repo_root / "scripts" / "server.py"
        foreign_file.parent.mkdir(parents=True, exist_ok=True)
        foreign_file.write_text("# server\n", encoding="utf-8")
        subprocess.run(["git", "add", "scripts/server.py"], cwd=self.repo_root, check=True, capture_output=True)
        with self.assertRaises(GitSafetyError):
            self.git_mgr.check_no_foreign_staged_files()

    # 13. stage_submission aborts if foreign file already staged
    def test_stage_submission_aborts_on_foreign_staged(self):
        foreign_file = self.repo_root / "scripts" / "lab.py"
        foreign_file.parent.mkdir(parents=True, exist_ok=True)
        foreign_file.write_text("# lab\n", encoding="utf-8")
        subprocess.run(["git", "add", "scripts/lab.py"], cwd=self.repo_root, check=True, capture_output=True)

        payload = validate_submission({
            "submission_id": "1",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// code",
            "status": "Accepted",
        })
        with self.assertRaises(GitSafetyError):
            self.git_mgr.stage_submission(payload)

    # 14. push raises GitSafetyError on branch mismatch
    def test_push_rejects_wrong_branch(self):
        # Create and checkout a different branch
        subprocess.run(["git", "checkout", "-b", "feature-branch"], cwd=self.repo_root, check=True, capture_output=True)
        mgr = GitManager(self.repo_root)
        with self.assertRaises(GitSafetyError) as ctx:
            mgr.push(remote="origin", branch="main")
        self.assertIn("Branch mismatch", str(ctx.exception))

    # 15. push raises GitSafetyError when remote not configured
    def test_push_rejects_missing_remote(self):
        with self.assertRaises(GitSafetyError) as ctx:
            self.git_mgr.push(remote="origin", branch="main")
        self.assertIn("not configured", str(ctx.exception))

    # 16. format_commit_message uses exact display name from LANGUAGE_DISPLAY_NAMES
    def test_format_commit_message_uses_display_names(self):
        """display_lang must come from LANGUAGE_DISPLAY_NAMES, not sorted list position."""
        # Test Go — alphabetically first, should NOT pick a wrong language
        payload_go = validate_submission({
            "submission_id": "10",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "go",
            "code": "// go code",
            "status": "Accepted",
        })
        prob_dir = self.repo_root / "problems" / "easy" / "0001-two-sum"
        result_new_lang = ImportResult(
            problem_dir=prob_dir,
            solution_file=prob_dir / "solution.go",
            readme_file=prob_dir / "README.md",
            is_new_problem=False,
            is_new_language=True,
            # Go sorts before Python alphabetically — result.languages[-1] would be wrong
            languages=["C++", "Go", "Python"],
            actions=[],
        )
        msg = self.git_mgr.format_commit_message(payload_go, result_new_lang)
        # Should say "Go", not "Python" (the sorted-last entry)
        self.assertEqual(msg, "feat(problems): add Go solution for 0001-two-sum")

    # 17. Forbidden file patterns cover new additions
    def test_forbidden_patterns_extended(self):
        with self.assertRaises(GitSafetyError):
            self.git_mgr.validate_paths_for_staging(["problems/easy/0001/secret.secret"])
        with self.assertRaises(GitSafetyError):
            self.git_mgr.validate_paths_for_staging(["problems/easy/0001/credentials.json"])


if __name__ == "__main__":
    unittest.main()
