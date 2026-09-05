"""
Comprehensive unit tests for ProblemManager, multi-language co-location,
conflict safety, and non-destructive manual content preservation.
All tests run in isolated temporary directories.
"""

import tempfile
import unittest
from pathlib import Path

from scripts.engine.ledger_updater import DelimiterError
from scripts.engine.problem_manager import ProblemManager
from scripts.engine.validator import validate_submission


class TestProblemManager(unittest.TestCase):

    def setUp(self):
        self.tmp_dir_obj = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmp_dir_obj.name).resolve()
        self.problem_manager = ProblemManager(self.repo_root)

        self.two_sum_cpp = validate_submission({
            "submission_id": "1001",
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
        })

        self.two_sum_py = validate_submission({
            "submission_id": "1002",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "python3",
            "code": "class Solution:\n    def twoSum(self): pass",
            "status": "Accepted",
            "runtime": "45 ms",
            "memory": "17.2 MB",
            "timestamp": "2026-08-28",
            "leetcode_tags": ["Array", "Hash Table"],
        })

        self.three_sum_cpp = validate_submission({
            "submission_id": "2001",
            "problem_id": 15,
            "slug": "3sum",
            "title": "3Sum",
            "difficulty": "Medium",
            "language": "cpp",
            "code": "class Solution { public: vector<vector<int>> threeSum() {} };",
            "status": "Accepted",
            "runtime": "25 ms",
            "memory": "20.1 MB",
            "timestamp": "2026-08-28",
            "leetcode_tags": ["Array", "Two Pointers", "Sorting"],
        })

    def tearDown(self):
        self.tmp_dir_obj.cleanup()

    # A & B & C & D & E: First problem import, directory, zero-padding, extension, README
    def test_first_problem_import(self):
        res = self.problem_manager.import_submission(self.two_sum_cpp)
        self.assertTrue(res.is_new_problem)
        self.assertEqual(res.problem_dir, self.repo_root / "problems" / "easy" / "0001-two-sum")
        self.assertTrue(res.problem_dir.exists())

        # Check solution file
        sol_file = res.problem_dir / "solution.cpp"
        self.assertTrue(sol_file.exists())
        self.assertIn("vector<int> twoSum", sol_file.read_text(encoding="utf-8"))

        # Check README
        readme_file = res.problem_dir / "README.md"
        self.assertTrue(readme_file.exists())
        content = readme_file.read_text(encoding="utf-8")
        self.assertIn("# 0001 — Two Sum", content)
        self.assertIn("> Easy · LeetCode #1", content)
        self.assertIn("problem_id: 1", content)
        self.assertIn('- "C++"', content)
        self.assertIn("## 💡 Engineering Intuition", content)
        self.assertIn("## ⚙️ Approach", content)
        self.assertIn("## 📊 Complexity Analysis", content)

    # B & C: Medium difficulty zero-padded ID
    def test_medium_difficulty_zero_padded(self):
        res = self.problem_manager.import_submission(self.three_sum_cpp)
        self.assertEqual(res.problem_dir, self.repo_root / "problems" / "medium" / "0015-3sum")
        self.assertTrue(res.problem_dir.exists())

    # F & G: Second language co-location & duplicate language prevention
    def test_second_language_colocation(self):
        # First import in C++
        self.problem_manager.import_submission(self.two_sum_cpp)

        # Second import in Python
        res_py = self.problem_manager.import_submission(self.two_sum_py)
        self.assertFalse(res_py.is_new_problem)
        self.assertTrue(res_py.is_new_language)

        problem_dir = self.repo_root / "problems" / "easy" / "0001-two-sum"
        cpp_sol = problem_dir / "solution.cpp"
        py_sol = problem_dir / "solution.py"

        # Both solution files must exist side-by-side
        self.assertTrue(cpp_sol.exists())
        self.assertTrue(py_sol.exists())

        # README must list both languages without duplication
        readme_content = (problem_dir / "README.md").read_text(encoding="utf-8")
        self.assertIn('- "C++"', readme_content)
        self.assertIn('- "Python"', readme_content)
        self.assertIn("- **Languages**: C++, Python", readme_content)

    # H: Duplicate submission idempotency
    def test_duplicate_submission_idempotency(self):
        # Import first time
        res1 = self.problem_manager.import_submission(self.two_sum_cpp)
        readme1 = (res1.problem_dir / "README.md").read_text(encoding="utf-8")

        # Import second time with exact same code
        res2 = self.problem_manager.import_submission(self.two_sum_cpp)
        readme2 = (res2.problem_dir / "README.md").read_text(encoding="utf-8")

        self.assertIn("identical_solution:solution.cpp", res2.actions)
        self.assertEqual(readme1, readme2)

    # I: Versioned file creation on different code (Alternatives architecture)
    def test_different_solution_creates_alternative(self):
        # 1. Initial submission
        self.problem_manager.import_submission(self.two_sum_cpp)

        # 2. Conflicting submission
        conflicting_submission = validate_submission({
            "submission_id": "9999",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// Completely different implementation\nclass Solution { ... };",
            "status": "Accepted",
        })

        res = self.problem_manager.import_submission(conflicting_submission)
        
        self.assertIn("update_solution:solution.cpp", res.actions)
        self.assertIn("preserve_alternative:solution_1001.cpp", res.actions)

        # The NEW code must be in solution.cpp (canonical)
        sol_file = self.repo_root / "problems" / "easy" / "0001-two-sum" / "solution.cpp"
        self.assertIn("// Completely different implementation", sol_file.read_text(encoding="utf-8"))

        # The OLD code must be in alternatives/solution_1001.cpp
        alt_sol_file = self.repo_root / "problems" / "easy" / "0001-two-sum" / "alternatives" / "solution_1001.cpp"
        self.assertTrue(alt_sol_file.exists())
        self.assertIn("vector<int> twoSum", alt_sol_file.read_text(encoding="utf-8"))
        
        # 3. Duplicate submission ID testing
        conflicting_submission_update = validate_submission({
            "submission_id": "9999",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// Completely different implementation v2\nclass Solution { ... };",
            "status": "Accepted",
        })
        res2 = self.problem_manager.import_submission(conflicting_submission_update)
        self.assertIn("update_solution:solution.cpp", res2.actions)
        self.assertIn("preserve_alternative:solution_9999.cpp", res2.actions)
        
        sol_file2 = self.repo_root / "problems" / "easy" / "0001-two-sum" / "solution.cpp"
        self.assertIn("v2", sol_file2.read_text(encoding="utf-8"))
        
        alt_sol_file2 = self.repo_root / "problems" / "easy" / "0001-two-sum" / "alternatives" / "solution_9999.cpp"
        self.assertTrue(alt_sol_file2.exists())
        self.assertIn("// Completely different implementation\nclass Solution", alt_sol_file2.read_text(encoding="utf-8"))
        
        # Test directory traversal safety
        with self.assertRaises(Exception) as ctx:
            validate_submission({
                "submission_id": "../../../9999",
                "problem_id": 1,
                "slug": "two-sum",
                "title": "Two Sum",
                "difficulty": "Easy",
                "language": "cpp",
                "code": "// Evil code",
                "status": "Accepted",
            })
        self.assertTrue("Invalid 'submission_id'" in str(ctx.exception) or "ValidationError" in str(type(ctx.exception)))

    # J, K, L: Manual content preservation
    def test_manual_sections_preservation(self):
        # Initial import
        self.problem_manager.import_submission(self.two_sum_cpp)
        readme_path = self.repo_root / "problems" / "easy" / "0001-two-sum" / "README.md"

        # User writes custom manual notes
        custom_readme = (
            readme_path.read_text(encoding="utf-8")
            .replace(
                "<!-- Add personal intuition, key invariants, and pattern recognition triggers here -->",
                "MY CRITICAL INVARIANT: The complement target - x must exist in hash table.",
            )
            .replace(
                "<!-- Step-by-step algorithmic approach and state transitions -->",
                "MY 1-PASS HASH MAP APPROACH: Scan once while inserting complements.",
            )
            .replace(
                "- **Time Complexity**: $O(\\dots)",
                "- **Time Complexity**: $O(N)$ because single pass hash lookup.",
            )
        )
        readme_path.write_text(custom_readme, encoding="utf-8")

        # Now import second language (Python)
        self.problem_manager.import_submission(self.two_sum_py)

        # Verify all manual content survived 100% untouched
        updated_readme = readme_path.read_text(encoding="utf-8")
        self.assertIn("MY CRITICAL INVARIANT: The complement target - x must exist in hash table.", updated_readme)
        self.assertIn("MY 1-PASS HASH MAP APPROACH: Scan once while inserting complements.", updated_readme)
        self.assertIn("- **Time Complexity**: $O(N)$ because single pass hash lookup.", updated_readme)

    # M & N: Missing and malformed delimiter rejection
    def test_missing_or_malformed_delimiters_abort(self):
        self.problem_manager.import_submission(self.two_sum_cpp)
        readme_path = self.repo_root / "problems" / "easy" / "0001-two-sum" / "README.md"

        # Corrupt the delimiter in the README
        corrupted = readme_path.read_text(encoding="utf-8").replace("<!-- AUTOMATION_STATS_END -->", "")
        readme_path.write_text(corrupted, encoding="utf-8")

        with self.assertRaises(DelimiterError):
            self.problem_manager.import_submission(self.two_sum_py)

    # P: Primary pattern manual override preservation
    def test_primary_pattern_preservation(self):
        self.problem_manager.import_submission(self.two_sum_cpp)
        readme_path = self.repo_root / "problems" / "easy" / "0001-two-sum" / "README.md"

        # User manually sets primary_pattern: "Two Pointers / Hash Map"
        content = readme_path.read_text(encoding="utf-8")
        content = content.replace('primary_pattern: ""', 'primary_pattern: "Hash Table"')
        readme_path.write_text(content, encoding="utf-8")

        # Re-import Python submission
        self.problem_manager.import_submission(self.two_sum_py)

        updated_content = readme_path.read_text(encoding="utf-8")
        self.assertIn('primary_pattern: "Hash Table"', updated_content)


if __name__ == "__main__":
    unittest.main()
