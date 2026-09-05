import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.engine.problem_manager import ProblemManager
from scripts.engine.validator import validate_submission

class TestProblemManagerFailures(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
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
        })
        self.problem_manager.import_submission(self.two_sum_cpp)

        self.new_submission = validate_submission({
            "submission_id": "9999",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "// Completely different implementation\nclass Solution { ... };",
            "status": "Accepted",
            "runtime": "0 ms",
            "memory": "10.5 MB",
        })
        
        self.prob_dir = self.repo_root / "problems" / "easy" / "0001-two-sum"
        self.sol_file = self.prob_dir / "solution.cpp"
        self.readme_file = self.prob_dir / "README.md"
        self.alt_dir = self.prob_dir / "alternatives"
        self.alt_file = self.alt_dir / "solution_1001.cpp"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_failure_during_readme_write(self):
        orig_sol = self.sol_file.read_bytes()
        orig_readme = self.readme_file.read_bytes()
        
        # We want readme_file.write_text to fail
        with patch("pathlib.Path.write_text") as mock_write:
            def side_effect(content, encoding):
                if "Two Sum" in content and "<!--" in content: # It's a README
                    raise OSError("Disk Full")
                # Fallback to actual write
                with open(self.sol_file, "w", encoding=encoding) as f:
                    f.write(content)
            mock_write.side_effect = side_effect
            
            with self.assertRaises(OSError):
                self.problem_manager.import_submission(self.new_submission)

        # Assert full rollback
        self.assertEqual(self.sol_file.read_bytes(), orig_sol)
        self.assertEqual(self.readme_file.read_bytes(), orig_readme)
        self.assertFalse(self.alt_dir.exists())

    def test_failure_during_alternative_copy(self):
        orig_sol = self.sol_file.read_bytes()
        orig_readme = self.readme_file.read_bytes()
        
        with patch("shutil.copy2") as mock_copy:
            mock_copy.side_effect = OSError("Permission Denied")
            
            with self.assertRaises(OSError):
                self.problem_manager.import_submission(self.new_submission)

        self.assertEqual(self.sol_file.read_bytes(), orig_sol)
        self.assertEqual(self.readme_file.read_bytes(), orig_readme)
        self.assertFalse(self.alt_dir.exists())

if __name__ == "__main__":
    unittest.main()
