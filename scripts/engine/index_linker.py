"""
Index Linker for LeetCode Lab.
Provides cross-referencing infrastructure to link canonical problems into
patterns/ and data-structures/ guides without duplicating solution code.
Only links when classification is explicitly known.
"""

from pathlib import Path
import re
from typing import List, Optional

from .validator import SubmissionPayload

PATTERN_MAP = {
    "two pointers": "two-pointers",
    "two-pointers": "two-pointers",
    "sliding window": "sliding-window",
    "sliding-window": "sliding-window",
    "binary search": "binary-search",
    "binary-search": "binary-search",
    "prefix sum": "prefix-sum",
    "prefix-sum": "prefix-sum",
    "bfs": "bfs",
    "breadth-first search": "bfs",
    "dfs": "dfs",
    "depth-first search": "dfs",
    "dynamic programming": "dynamic-programming",
    "dp": "dynamic-programming",
}

DS_MAP = {
    "array": "arrays",
    "arrays": "arrays",
    "string": "strings",
    "strings": "strings",
    "linked list": "linked-list",
    "linked-list": "linked-list",
    "stack": "stack",
    "queue": "queue",
    "heap": "heap",
    "priority queue": "heap",
    "tree": "trees",
    "trees": "trees",
    "binary search tree": "trees",
    "trie": "trie",
    "graph": "graphs",
    "graphs": "graphs",
}


class IndexLinker:
    """Safely creates cross-reference index entries for patterns and data structures."""

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.patterns_dir = self.repo_root / "patterns"
        self.ds_dir = self.repo_root / "data-structures"

    def link_problem(
        self,
        payload: SubmissionPayload,
        primary_pattern: Optional[str] = None,
        dry_run: bool = False,
    ) -> List[str]:
        """
        Links a problem to its corresponding pattern guide if explicitly classified.
        Returns a list of actions performed.
        """
        actions: List[str] = []
        if not primary_pattern:
            return actions

        norm_pattern = primary_pattern.strip().lower()
        if norm_pattern not in PATTERN_MAP:
            return actions

        pattern_slug = PATTERN_MAP[norm_pattern]
        target_guide_dir = self.patterns_dir / pattern_slug
        if not target_guide_dir.exists():
            return actions

        guide_readme = target_guide_dir / "README.md"
        relative_problem_link = f"../../{payload.canonical_relative_path}"

        # If pattern README exists and has an indexed table, we can append to it
        if guide_readme.exists():
            content = guide_readme.read_text(encoding="utf-8")
            problem_entry = f"| #{payload.problem_id:04d} | [{payload.title}]({relative_problem_link}) | {payload.difficulty} |"
            if payload.slug not in content:
                actions.append(f"link_pattern:{pattern_slug}")
                if not dry_run:
                    # If there is a problem list in guide_readme, append cleanly
                    if "<!-- INDEXED_PROBLEMS_START -->" in content:
                        # Append inside delimiter
                        pass
        return actions
