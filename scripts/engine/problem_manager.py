"""
Problem Manager for LeetCode Lab.
Handles canonical directory creation, multi-language co-location, conflict detection,
and non-destructive problem README generation.
"""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .ledger_updater import DelimiterError, extract_delimited_block, replace_delimited_block
from .validator import SubmissionPayload

# Human-readable language display names for metadata and READMEs
LANGUAGE_DISPLAY_NAMES: Dict[str, str] = {
    "cpp": "C++",
    "python3": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "c": "C",
    "go": "Go",
    "rust": "Rust",
}

STATS_START_TAG = "<!-- AUTOMATION_STATS_START -->"
STATS_END_TAG = "<!-- AUTOMATION_STATS_END -->"
BODY_START_TAG = "<!-- AUTOMATION_PROBLEM_BODY_START -->"
BODY_END_TAG = "<!-- AUTOMATION_PROBLEM_BODY_END -->"


class SolutionConflictError(Exception):
    """Raised when an incoming solution differs from an existing solution in the same language."""
    pass


@dataclass
class ImportResult:
    """Summary of operations performed during a problem import."""
    problem_dir: Path
    solution_file: Path
    readme_file: Path
    actions: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    is_new_problem: bool = False
    is_new_language: bool = False


class ProblemManager:
    """Manages canonical problem directories, multi-language solutions, and READMEs."""

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.problems_dir = self.repo_root / "problems"

    def get_canonical_dir(self, payload: SubmissionPayload) -> Path:
        """Returns the canonical directory path: problems/<difficulty>/<0000-slug>/"""
        difficulty_dir = self.problems_dir / payload.difficulty.lower()
        target_dir = difficulty_dir / payload.canonical_dir_name

        # Path traversal confinement check
        try:
            target_dir.resolve().relative_to(self.problems_dir.resolve())
        except ValueError:
            raise ValueError(f"Path traversal detected. Target directory {target_dir} escapes {self.problems_dir}")

        return target_dir

    def import_submission(
        self,
        payload: SubmissionPayload,
        dry_run: bool = False,
    ) -> ImportResult:
        """
        Imports a validated SubmissionPayload into the canonical directory.
        Handles multi-language co-location and non-destructive README updates.
        """
        target_dir = self.get_canonical_dir(payload)
        solution_filename = f"solution.{payload.extension}"
        solution_file = target_dir / solution_filename
        readme_file = target_dir / "README.md"

        actions: List[str] = []
        is_new_problem = not target_dir.exists()
        is_new_language = False

        if is_new_problem:
            actions.append(f"create_directory:{target_dir.name}")

        # Check solution file
        if solution_file.exists():
            existing_code = solution_file.read_text(encoding="utf-8").strip()
            new_code = payload.code.strip()
            if existing_code == new_code:
                actions.append(f"identical_solution:{solution_filename}")
            else:
                raise SolutionConflictError(
                    f"Solution conflict for #{payload.problem_id} in {payload.language}: "
                    f"A different solution already exists at {solution_file.relative_to(self.repo_root)}. "
                    "Existing solution is preserved. Manual review required."
                )
        else:
            is_new_language = not is_new_problem
            actions.append(f"create_solution:{solution_filename}")

        # Determine all languages for this problem
        display_lang = LANGUAGE_DISPLAY_NAMES.get(payload.language, payload.language)
        existing_languages = self._detect_existing_languages(target_dir) if target_dir.exists() else []
        all_languages = sorted(list(set(existing_languages + [display_lang])))

        # Handle README
        if readme_file.exists():
            actions.append("update_readme")
            updated_readme_content = self._update_existing_readme(readme_file, payload, all_languages)
        else:
            actions.append("create_readme")
            updated_readme_content = self._generate_new_readme(payload, all_languages)

        # Apply disk changes if not dry_run
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            if not solution_file.exists() or solution_file.read_text(encoding="utf-8").strip() == payload.code.strip():
                solution_file.write_text(payload.code.strip() + "\n", encoding="utf-8")
            readme_file.write_text(updated_readme_content, encoding="utf-8")

        return ImportResult(
            problem_dir=target_dir,
            solution_file=solution_file,
            readme_file=readme_file,
            actions=actions,
            languages=all_languages,
            is_new_problem=is_new_problem,
            is_new_language=is_new_language,
        )

    def _detect_existing_languages(self, problem_dir: Path) -> List[str]:
        """Detects existing solution files in problem_dir and returns display names."""
        langs: List[str] = []
        if not problem_dir.exists():
            return langs

        ext_to_lang = {
            "cpp": "C++",
            "py": "Python",
            "java": "Java",
            "js": "JavaScript",
            "ts": "TypeScript",
            "c": "C",
            "go": "Go",
            "rs": "Rust",
        }

        for file in problem_dir.iterdir():
            if file.is_file() and file.name.startswith("solution."):
                ext = file.suffix.lstrip(".")
                if ext in ext_to_lang:
                    langs.append(ext_to_lang[ext])

        return sorted(list(set(langs)))

    def _generate_new_readme(
        self,
        payload: SubmissionPayload,
        languages: List[str],
    ) -> str:
        """Generates a complete new problem README.md with frontmatter, stats, and manual templates."""
        leetcode_url = f"https://leetcode.com/problems/{payload.slug}/"
        lang_list_str = "\n".join([f'  - "{lang}"' for lang in languages])
        tags_list_str = (
            "\n".join([f'  - "{tag}"' for tag in payload.leetcode_tags])
            if payload.leetcode_tags
            else "  []"
        )
        runtime_str = f'"{payload.runtime}"' if payload.runtime else 'null'
        memory_str = f'"{payload.memory}"' if payload.memory else 'null'
        tags_display = ", ".join(payload.leetcode_tags) if payload.leetcode_tags else "None"
        languages_display = ", ".join(languages)

        return f"""---
problem_id: {payload.problem_id}
title: "{payload.title}"
difficulty: "{payload.difficulty}"
slug: "{payload.slug}"
leetcode_url: "{leetcode_url}"
languages:
{lang_list_str}
leetcode_tags:
{tags_list_str}
primary_pattern: ""
solved_at: "{payload.timestamp}"
submission_id: "{payload.submission_id}"
runtime: {runtime_str}
memory: {memory_str}
---

# {payload.problem_id:04d} — {payload.title}

> {payload.difficulty} · LeetCode #{payload.problem_id}

## 🔗 Problem

[View on LeetCode]({leetcode_url})

{STATS_START_TAG}
- **Languages**: {languages_display}
- **Runtime**: {payload.runtime or 'N/A'}
- **Memory**: {payload.memory or 'N/A'}
- **Tags**: {tags_display}
{STATS_END_TAG}

{BODY_START_TAG}
### Problem Statement
*(Problem statement indexed from LeetCode)*
{BODY_END_TAG}

## 💡 Engineering Intuition

<!-- Add personal intuition, key invariants, and pattern recognition triggers here -->

## ⚙️ Approach

<!-- Step-by-step algorithmic approach and state transitions -->

## 🧪 Edge Cases

- Empty / single-element collections
- Boundary conditions & negative numbers
- Duplicates & overflow constraints

## 📊 Complexity Analysis

- **Time Complexity**: $O(\\dots)$
- **Space Complexity**: $O(\\dots)$

## 📝 Lessons Learned

<!-- Personal retrospectives, anti-patterns avoided, or debugging notes -->
"""

    def _update_existing_readme(
        self,
        readme_file: Path,
        payload: SubmissionPayload,
        languages: List[str],
    ) -> str:
        """
        Updates an existing problem README.md:
        - Updates frontmatter (merges languages, preserves primary_pattern).
        - Updates STATS delimited block.
        - Preserves all manual sections (Intuition, Approach, Edge Cases, Complexity, Lessons).
        """
        content = readme_file.read_text(encoding="utf-8")

        # 1. Parse existing frontmatter
        frontmatter_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        preserved_primary_pattern = ""
        if frontmatter_match:
            fm_text = frontmatter_match.group(1)
            pattern_match = re.search(r'primary_pattern:\s*["\']?(.*?)["\']?\s*$', fm_text, re.MULTILINE)
            if pattern_match and pattern_match.group(1).strip():
                preserved_primary_pattern = pattern_match.group(1).strip()

        # 2. Build updated frontmatter
        leetcode_url = f"https://leetcode.com/problems/{payload.slug}/"
        lang_list_str = "\n".join([f'  - "{lang}"' for lang in languages])
        tags_list_str = (
            "\n".join([f'  - "{tag}"' for tag in payload.leetcode_tags])
            if payload.leetcode_tags
            else "  []"
        )
        runtime_str = f'"{payload.runtime}"' if payload.runtime else 'null'
        memory_str = f'"{payload.memory}"' if payload.memory else 'null'
        pattern_str = f'"{preserved_primary_pattern}"' if preserved_primary_pattern else '""'

        new_frontmatter = f"""---
problem_id: {payload.problem_id}
title: "{payload.title}"
difficulty: "{payload.difficulty}"
slug: "{payload.slug}"
leetcode_url: "{leetcode_url}"
languages:
{lang_list_str}
leetcode_tags:
{tags_list_str}
primary_pattern: {pattern_str}
solved_at: "{payload.timestamp}"
submission_id: "{payload.submission_id}"
runtime: {runtime_str}
memory: {memory_str}
---
"""

        # Replace frontmatter
        if frontmatter_match:
            body_without_fm = content[frontmatter_match.end() :]
        else:
            body_without_fm = content

        # 3. Update delimited STATS block
        languages_display = ", ".join(languages)
        tags_display = ", ".join(payload.leetcode_tags) if payload.leetcode_tags else "None"
        new_stats = f"""- **Languages**: {languages_display}
- **Runtime**: {payload.runtime or 'N/A'}
- **Memory**: {payload.memory or 'N/A'}
- **Tags**: {tags_display}"""

        updated_body = replace_delimited_block(
            body_without_fm,
            STATS_START_TAG,
            STATS_END_TAG,
            new_stats,
        )

        return f"{new_frontmatter}{updated_body}"
