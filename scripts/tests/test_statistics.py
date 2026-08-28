"""
Unit tests for repository scanner, statistics calculation, and deterministic dashboard rendering.
All tests run in isolated temporary directories.
"""

import tempfile
import unittest
from pathlib import Path

from scripts.engine.ledger_updater import DelimiterError
from scripts.engine.problem_manager import ProblemManager
from scripts.engine.statistics import (
    DashboardRenderer,
    DashboardUpdater,
    RepositoryScanner,
    RepositoryStats,
)
from scripts.engine.validator import validate_submission


class TestStatisticsAndDashboard(unittest.TestCase):

    def setUp(self):
        self.tmp_dir_obj = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmp_dir_obj.name).resolve()

        # Initialize mock problems directory
        (self.repo_root / "problems" / "easy").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "problems" / "medium").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "problems" / "hard").mkdir(parents=True, exist_ok=True)

        # Create starter README.md and PROGRESS.md with delimiters
        self.readme_path = self.repo_root / "README.md"
        self.progress_path = self.repo_root / "PROGRESS.md"

        self.readme_path.write_text(
            "# LeetCode Lab\n\n"
            "<!-- AUTOMATION_METRICS_START -->\nold metrics\n<!-- AUTOMATION_METRICS_END -->\n\n"
            "<!-- AUTOMATION_RECENT_SOLVES_START -->\nold recent\n<!-- AUTOMATION_RECENT_SOLVES_END -->\n\n"
            "<!-- AUTOMATION_MILESTONES_START -->\nold milestones\n<!-- AUTOMATION_MILESTONES_END -->\n",
            encoding="utf-8",
        )

        self.progress_path.write_text(
            "# Progress\n\n"
            "<!-- AUTOMATION_CATEGORY_TELEMETRY_START -->\nold category\n<!-- AUTOMATION_CATEGORY_TELEMETRY_END -->\n\n"
            "<!-- AUTOMATION_PROBLEM_LOG_START -->\nold log\n<!-- AUTOMATION_PROBLEM_LOG_END -->\n",
            encoding="utf-8",
        )

        self.problem_manager = ProblemManager(self.repo_root)
        self.scanner = RepositoryScanner(self.repo_root)
        self.updater = DashboardUpdater(self.repo_root)

    def tearDown(self):
        self.tmp_dir_obj.cleanup()

    # 1. Empty repository
    def test_empty_repository(self):
        stats = self.scanner.scan()
        self.assertEqual(stats.total_solved, 0)
        self.assertEqual(stats.easy_count, 0)
        self.assertEqual(stats.medium_count, 0)
        self.assertEqual(stats.hard_count, 0)
        self.assertEqual(stats.language_counts, {})
        self.assertEqual(len(stats.all_problems), 0)
        self.assertEqual(len(stats.recent_solves), 0)
        self.assertFalse(any(stats.milestones.values()))

    # 2. One Easy problem
    def test_one_easy_problem(self):
        p1 = validate_submission({
            "submission_id": "1",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "class Solution {};",
            "status": "Accepted",
            "runtime": "0 ms",
            "memory": "10.5 MB",
            "timestamp": "2026-08-28",
            "leetcode_tags": ["Array", "Hash Table"],
        })
        self.problem_manager.import_submission(p1)

        stats = self.scanner.scan()
        self.assertEqual(stats.total_solved, 1)
        self.assertEqual(stats.easy_count, 1)
        self.assertEqual(stats.medium_count, 0)
        self.assertEqual(stats.hard_count, 0)
        self.assertEqual(stats.language_counts, {"C++": 1})
        self.assertEqual(len(stats.all_problems), 1)
        self.assertEqual(stats.all_problems[0].problem_id, 1)

    # 3. Easy + Medium + Hard
    def test_easy_medium_hard_distribution(self):
        p_easy = validate_submission({
            "submission_id": "1",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// code",
            "status": "Accepted",
        })
        p_med = validate_submission({
            "submission_id": "2",
            "problem_id": 15,
            "slug": "3sum",
            "title": "3Sum",
            "difficulty": "Medium",
            "language": "python3",
            "code": "# code",
            "status": "Accepted",
        })
        p_hard = validate_submission({
            "submission_id": "3",
            "problem_id": 42,
            "slug": "trapping-rain-water",
            "title": "Trapping Rain Water",
            "difficulty": "Hard",
            "language": "rust",
            "code": "// rust code",
            "status": "Accepted",
        })

        self.problem_manager.import_submission(p_easy)
        self.problem_manager.import_submission(p_med)
        self.problem_manager.import_submission(p_hard)

        stats = self.scanner.scan()
        self.assertEqual(stats.total_solved, 3)
        self.assertEqual(stats.easy_count, 1)
        self.assertEqual(stats.medium_count, 1)
        self.assertEqual(stats.hard_count, 1)
        self.assertEqual(stats.language_counts, {"C++": 1, "Python": 1, "Rust": 1})

    # 4. Multiple languages for ONE problem counts as 1 problem
    def test_multi_language_single_problem_count(self):
        p1_cpp = validate_submission({
            "submission_id": "1",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// cpp code",
            "status": "Accepted",
        })
        p1_py = validate_submission({
            "submission_id": "2",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "python3",
            "code": "# py code",
            "status": "Accepted",
        })

        self.problem_manager.import_submission(p1_cpp)
        self.problem_manager.import_submission(p1_py)

        stats = self.scanner.scan()
        # Must still be exactly 1 solved problem
        self.assertEqual(stats.total_solved, 1)
        self.assertEqual(stats.easy_count, 1)
        # But both languages are tracked
        self.assertEqual(stats.language_counts, {"C++": 1, "Python": 1})
        self.assertEqual(stats.all_problems[0].languages, ["C++", "Python"])

    # 8. Milestone calculation
    def test_milestone_threshold_activation(self):
        # Create 10 dummy problems
        for i in range(1, 11):
            p = validate_submission({
                "submission_id": str(i),
                "problem_id": i,
                "slug": f"problem-{i}",
                "title": f"Problem {i}",
                "difficulty": "Easy",
                "language": "cpp",
                "code": "// code",
                "status": "Accepted",
            })
            self.problem_manager.import_submission(p)

        stats = self.scanner.scan()
        self.assertEqual(stats.total_solved, 10)
        self.assertTrue(stats.milestones[10])
        self.assertFalse(stats.milestones[50])
        self.assertFalse(stats.milestones[100])

        milestone_md = DashboardRenderer.render_milestones(stats)
        self.assertIn("- [x] **10 Solved**", milestone_md)
        self.assertIn("- [ ] **50 Solved**", milestone_md)

    # 11. Malformed directories and .gitkeep ignored safely
    def test_malformed_directories_ignored(self):
        # Add .gitkeep
        (self.repo_root / "problems" / "easy" / ".gitkeep").touch()
        # Add non-zero padded directory
        (self.repo_root / "problems" / "easy" / "random-folder").mkdir()
        # Add file in problems
        (self.repo_root / "problems" / "easy" / "notes.txt").write_text("random notes")

        stats = self.scanner.scan()
        self.assertEqual(stats.total_solved, 0)

    # 12. Deterministic output
    def test_deterministic_output(self):
        p1 = validate_submission({
            "submission_id": "1",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// code",
            "status": "Accepted",
            "timestamp": "2026-08-28",
        })
        self.problem_manager.import_submission(p1)

        stats1 = self.scanner.scan()
        m1 = DashboardRenderer.render_metrics_dashboard(stats1)
        r1 = DashboardRenderer.render_recent_solves(stats1)

        stats2 = self.scanner.scan()
        m2 = DashboardRenderer.render_metrics_dashboard(stats2)
        r2 = DashboardRenderer.render_recent_solves(stats2)

        self.assertEqual(m1, m2)
        self.assertEqual(r1, r2)

    # 13, 14. DashboardUpdater updates README.md & PROGRESS.md in-place
    def test_dashboard_updater_updates_files(self):
        p1 = validate_submission({
            "submission_id": "1",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// code",
            "status": "Accepted",
            "timestamp": "2026-08-28",
            "leetcode_tags": ["Array", "Hash Table"],
        })
        self.problem_manager.import_submission(p1)

        readme_changed, progress_changed, stats = self.updater.update_all()
        self.assertTrue(readme_changed)
        self.assertTrue(progress_changed)

        readme_content = self.readme_path.read_text(encoding="utf-8")
        progress_content = self.progress_path.read_text(encoding="utf-8")

        self.assertIn("**Total Solved** | **1**", readme_content)
        self.assertIn("| 1 | [Two Sum]", readme_content)
        self.assertIn("| 0001 | Two Sum |", progress_content)
        self.assertIn("| **Arrays & Strings** | 1 |", progress_content)

    # 15. Missing delimiters cause safe failure
    def test_missing_delimiters_cause_safe_failure(self):
        self.readme_path.write_text("# Corrupted README without delimiters\n", encoding="utf-8")
        with self.assertRaises(DelimiterError):
            self.updater.update_all()


if __name__ == "__main__":
    unittest.main()
