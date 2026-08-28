"""
Unit tests for submission payload validator and security boundaries.
"""

import unittest
from scripts.engine.validator import (
    SubmissionPayload,
    ValidationError,
    validate_submission,
    MAX_CODE_SIZE_BYTES,
)


class TestSubmissionValidator(unittest.TestCase):

    def setUp(self):
        self.valid_payload = {
            "submission_id": "12345678",
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

    def test_valid_payload_cpp(self):
        payload = validate_submission(self.valid_payload)
        self.assertIsInstance(payload, SubmissionPayload)
        self.assertEqual(payload.problem_id, 1)
        self.assertEqual(payload.slug, "two-sum")
        self.assertEqual(payload.difficulty, "Easy")
        self.assertEqual(payload.language, "cpp")
        self.assertEqual(payload.extension, "cpp")
        self.assertEqual(payload.canonical_dir_name, "0001-two-sum")
        self.assertEqual(payload.canonical_relative_path, "problems/easy/0001-two-sum/")
        self.assertEqual(payload.leetcode_tags, ["Array", "Hash Table"])

    def test_language_normalization(self):
        cases = [
            ("python", "python3", "py"),
            ("python3", "python3", "py"),
            ("py", "python3", "py"),
            ("c++", "cpp", "cpp"),
            ("g++", "cpp", "cpp"),
            ("java", "java", "java"),
            ("javascript", "javascript", "js"),
            ("js", "javascript", "js"),
            ("typescript", "typescript", "ts"),
            ("ts", "typescript", "ts"),
            ("c", "c", "c"),
            ("go", "go", "go"),
            ("golang", "go", "go"),
            ("rust", "rust", "rs"),
            ("rs", "rust", "rs"),
        ]
        for input_lang, expected_lang, expected_ext in cases:
            raw = self.valid_payload.copy()
            raw["language"] = input_lang
            parsed = validate_submission(raw)
            self.assertEqual(parsed.language, expected_lang)
            self.assertEqual(parsed.extension, expected_ext)

    def test_rejection_of_non_accepted_statuses(self):
        invalid_statuses = [
            "Wrong Answer",
            "Time Limit Exceeded",
            "Memory Limit Exceeded",
            "Runtime Error",
            "Compile Error",
            "",
            None,
        ]
        for status in invalid_statuses:
            raw = self.valid_payload.copy()
            raw["status"] = status
            with self.assertRaises(ValidationError) as ctx:
                validate_submission(raw)
            self.assertIn("Accepted", str(ctx.exception))

    def test_rejection_of_invalid_difficulty(self):
        for diff in ["Insane", "SuperEasy", "123", "", None]:
            raw = self.valid_payload.copy()
            raw["difficulty"] = diff
            with self.assertRaises(ValidationError):
                validate_submission(raw)

    def test_rejection_of_path_traversal_and_malicious_slugs(self):
        malicious_slugs = [
            "../../etc/passwd",
            "../two-sum",
            "two/sum",
            "two\\sum",
            "two..sum",
            "-two-sum",
            "two-sum-",
            "two sum",
            "two_sum",
            "two$um",
            "",
            None,
        ]
        for slug in malicious_slugs:
            raw = self.valid_payload.copy()
            raw["slug"] = slug
            with self.assertRaises(ValidationError):
                validate_submission(raw)

    def test_rejection_of_unsupported_language(self):
        for lang in ["brainfuck", "fortran", "pascal", "ruby", "", None]:
            raw = self.valid_payload.copy()
            raw["language"] = lang
            with self.assertRaises(ValidationError):
                validate_submission(raw)

    def test_rejection_of_empty_code(self):
        for empty_code in ["", "   \n\t  ", None]:
            raw = self.valid_payload.copy()
            raw["code"] = empty_code
            with self.assertRaises(ValidationError):
                validate_submission(raw)

    def test_rejection_of_oversized_code(self):
        raw = self.valid_payload.copy()
        raw["code"] = "x = 1\n" * (MAX_CODE_SIZE_BYTES // 4)
        with self.assertRaises(ValidationError):
            validate_submission(raw)

    def test_rejection_of_invalid_problem_id(self):
        for bad_id in [0, -5, "abc", None, 1000000]:
            raw = self.valid_payload.copy()
            raw["problem_id"] = bad_id
            with self.assertRaises(ValidationError):
                validate_submission(raw)

    def test_graphql_tag_objects_handling(self):
        raw = self.valid_payload.copy()
        raw["leetcode_tags"] = [{"name": "Dynamic Programming", "slug": "dynamic-programming"}, {"name": "Array"}]
        parsed = validate_submission(raw)
        self.assertEqual(parsed.leetcode_tags, ["Dynamic Programming", "Array"])


if __name__ == "__main__":
    unittest.main()
