"""
Unit tests for ledger and markdown delimiter updater.
"""

import tempfile
import unittest
from pathlib import Path

from scripts.engine.ledger_updater import (
    DelimiterError,
    extract_delimited_block,
    replace_delimited_block,
    update_file_delimited_block,
)


class TestLedgerUpdater(unittest.TestCase):

    def setUp(self):
        self.start_tag = "<!-- TEST_START -->"
        self.end_tag = "<!-- TEST_END -->"
        self.sample_doc = (
            "# Header\n\n"
            "Pre-content\n\n"
            f"{self.start_tag}\n"
            "Original Inner Content\n"
            f"{self.end_tag}\n\n"
            "Post-content\n"
        )

    def test_extract_delimited_block_success(self):
        inner = extract_delimited_block(self.sample_doc, self.start_tag, self.end_tag)
        self.assertEqual(inner.strip(), "Original Inner Content")

    def test_extract_missing_start_tag(self):
        doc = "No start tag\n<!-- TEST_END -->\n"
        with self.assertRaises(DelimiterError) as ctx:
            extract_delimited_block(doc, self.start_tag, self.end_tag)
        self.assertIn("Missing start delimiter", str(ctx.exception))

    def test_extract_missing_end_tag(self):
        doc = "<!-- TEST_START -->\nNo end tag\n"
        with self.assertRaises(DelimiterError) as ctx:
            extract_delimited_block(doc, self.start_tag, self.end_tag)
        self.assertIn("Missing end delimiter", str(ctx.exception))

    def test_extract_duplicate_start_tag(self):
        doc = f"{self.start_tag}\n{self.start_tag}\n{self.end_tag}\n"
        with self.assertRaises(DelimiterError) as ctx:
            extract_delimited_block(doc, self.start_tag, self.end_tag)
        self.assertIn("Duplicate start delimiter", str(ctx.exception))

    def test_extract_duplicate_end_tag(self):
        doc = f"{self.start_tag}\n{self.end_tag}\n{self.end_tag}\n"
        with self.assertRaises(DelimiterError) as ctx:
            extract_delimited_block(doc, self.start_tag, self.end_tag)
        self.assertIn("Duplicate end delimiter", str(ctx.exception))

    def test_extract_inverted_tags(self):
        doc = f"{self.end_tag}\nContent\n{self.start_tag}\n"
        with self.assertRaises(DelimiterError) as ctx:
            extract_delimited_block(doc, self.start_tag, self.end_tag)
        self.assertIn("Malformed delimiters", str(ctx.exception))

    def test_replace_delimited_block_preserves_surrounding_content(self):
        new_content = "Replaced Inner Text"
        updated = replace_delimited_block(self.sample_doc, self.start_tag, self.end_tag, new_content)

        self.assertTrue(updated.startswith("# Header\n\nPre-content\n\n<!-- TEST_START -->\n"))
        self.assertTrue(updated.endswith("<!-- TEST_END -->\n\nPost-content\n"))
        self.assertIn("Replaced Inner Text", updated)
        self.assertNotIn("Original Inner Content", updated)

    def test_update_file_delimited_block(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.md"
            test_file.write_text(self.sample_doc, encoding="utf-8")

            # First update -> changes content
            changed = update_file_delimited_block(test_file, self.start_tag, self.end_tag, "New Data")
            self.assertTrue(changed)
            self.assertIn("New Data", test_file.read_text(encoding="utf-8"))

            # Second update with same data -> no-op
            changed_again = update_file_delimited_block(test_file, self.start_tag, self.end_tag, "New Data")
            self.assertFalse(changed_again)


if __name__ == "__main__":
    unittest.main()
