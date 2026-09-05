import unittest
from pathlib import Path

from scripts.engine.problem_manager import ProblemManager
from scripts.engine.validator import validate_submission

class TestProblemManagerTransactions(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        self.problem_manager = ProblemManager(self.repo_root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_duplicate_submission_collision(self):
        # 1. Create first
        sub1 = validate_submission({
            "submission_id": "100",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "code v1",
            "status": "Accepted",
        })
        self.problem_manager.import_submission(sub1)
        
        # 2. Overwrite with diff code
        sub2 = validate_submission({
            "submission_id": "200",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "code v2",
            "status": "Accepted",
        })
        self.problem_manager.import_submission(sub2)
        
        # alt: solution_100.cpp -> code v1
        
        # 3. Simulate LeetCode glitch: same submission ID as 100, but different code!
        sub3 = validate_submission({
            "submission_id": "100", # DUPLICATE ID
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "code v3",
            "status": "Accepted",
        })
        self.problem_manager.import_submission(sub3)
        
        # alt: solution_200.cpp -> code v2
        
        # 4. Now what happens? It should NOT overwrite solution_100.cpp!
        alt_dir = self.repo_root / "problems/easy/0001-two-sum/alternatives"
        self.assertEqual((alt_dir / "solution_100.cpp").read_text().strip(), "code v1")
        self.assertEqual((alt_dir / "solution_200.cpp").read_text().strip(), "code v2")
        
        # 5. Let's submit 300, it replaces v3
        sub4 = validate_submission({
            "submission_id": "300",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "code v4",
            "status": "Accepted",
        })
        self.problem_manager.import_submission(sub4)
        
        # The previous code v3 was under submission_id "100" (sub3). So it should be backed up as solution_100_1.cpp!
        self.assertEqual((alt_dir / "solution_100_1.cpp").read_text().strip(), "code v3")

    def test_uncommitted_manual_changes(self):
        sub1 = validate_submission({
            "submission_id": "100",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "code v1",
            "status": "Accepted",
        })
        self.problem_manager.import_submission(sub1)
        
        sol_file = self.repo_root / "problems/easy/0001-two-sum/solution.cpp"
        sol_file.write_text("code v1 + uncommitted manual edit")
        
        sub2 = validate_submission({
            "submission_id": "200",
            "problem_id": 1,
            "slug": "two-sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "language": "cpp",
            "code": "code v2",
            "status": "Accepted",
        })
        self.problem_manager.import_submission(sub2)
        
        alt_file = self.repo_root / "problems/easy/0001-two-sum/alternatives/solution_100.cpp"
        self.assertEqual(alt_file.read_text(), "code v1 + uncommitted manual edit")

if __name__ == "__main__":
    unittest.main()
