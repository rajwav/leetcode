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

        alt_file_to_write = None
        alt_filename = None

        # Check solution file
        if solution_file.exists():
            existing_code = solution_file.read_text(encoding="utf-8").strip()
            new_code = payload.code.strip()
            if existing_code == new_code:
                actions.append(f"identical_solution:{solution_filename}")
            else:
                # We have a different solution. Preserve the old one in alternatives/
                old_sub_id = "unknown"
                if readme_file.exists():
                    fm_match = re.search(r'^submission_id:\s*["\']?(.*?)["\']?\s*$', readme_file.read_text(encoding="utf-8"), re.MULTILINE)
                    if fm_match:
                        old_sub_id = fm_match.group(1).strip()
                
                safe_old_id = "".join(c for c in old_sub_id if c.isalnum()) or "unknown"
                alt_dir = target_dir / "alternatives"
                
                # Collision handling
                base_alt_name = f"solution_{safe_old_id}"
                alt_filename = f"{base_alt_name}.{payload.extension}"
                alt_file = alt_dir / alt_filename
                
                counter = 1
                while alt_file.exists():
                    if alt_file.read_text(encoding="utf-8").strip() == existing_code:
                        break # It's exactly the same old code already backed up
                    alt_filename = f"{base_alt_name}_{counter}.{payload.extension}"
                    alt_file = alt_dir / alt_filename
                    counter += 1
                    
                alt_file_to_write = alt_file
                
                actions.append(f"preserve_alternative:{alt_filename}")
                actions.append(f"update_solution:{solution_filename}")
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

        # Apply Phase 2 Analyzer if README has empty placeholders
        try:
            from .analyzer import CodeAnalyzer
            analyzer = CodeAnalyzer(payload.code, payload.leetcode_tags)
            analysis = analyzer.analyze()
            updated_readme_content = self._fill_placeholders(updated_readme_content, analysis)
        except Exception as e:
            import logging
            logging.warning(f"Phase 2 Analyzer failed, skipping automated content: {e}")

        # Apply disk changes transactionally if not dry_run
        if not dry_run:
            orig_readme = readme_file.read_bytes() if readme_file.exists() else None
            orig_solution = solution_file.read_bytes() if solution_file.exists() else None
            
            created_dirs = []
            created_files = []
            
            try:
                if not target_dir.exists():
                    target_dir.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(target_dir)
                    
                # Step 1: Copy existing solution to alternatives if needed
                if alt_file_to_write:
                    if not alt_file_to_write.parent.exists():
                        alt_file_to_write.parent.mkdir(parents=True, exist_ok=True)
                        created_dirs.append(alt_file_to_write.parent)
                        
                    if not alt_file_to_write.exists():
                        created_files.append(alt_file_to_write)
                    import shutil
                    shutil.copy2(solution_file, alt_file_to_write)
                    
                # Step 2: Write new solution if not identical
                if "identical_solution:" not in "".join(actions):
                    if not solution_file.exists():
                        created_files.append(solution_file)
                    solution_file.write_text(payload.code.strip() + "\n", encoding="utf-8")
                    
                # Step 3: Update README
                if not readme_file.exists():
                    created_files.append(readme_file)
                readme_file.write_text(updated_readme_content, encoding="utf-8")
                
            except Exception as e:
                # Rollback
                for f in reversed(created_files):
                    if f.exists():
                        f.unlink()
                if orig_readme is not None:
                    readme_file.write_bytes(orig_readme)
                if orig_solution is not None:
                    solution_file.write_bytes(orig_solution)
                for d in reversed(created_dirs):
                    if d.exists() and not any(d.iterdir()):
                        d.rmdir()
                raise e # Re-raise to let the caller handle it (500)

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

    def _fill_placeholders(self, readme: str, analysis: dict) -> str:
        if analysis.get("intuition") and analysis.get("intuition") != "Analysis required":
            readme = re.sub(
                r'(## 💡 Engineering Intuition\n\n)<!-- Add personal intuition.*?-->',
                r'\1' + analysis.get("intuition", ""),
                readme,
                flags=re.DOTALL
            )
            
        if analysis.get("approach") and analysis.get("approach") != "Analysis required":
            readme = re.sub(
                r'(## ⚙️ Approach\n\n)<!-- Step-by-step.*?-->',
                r'\1' + analysis.get("approach", ""),
                readme,
                flags=re.DOTALL
            )
            
        if analysis.get("edge_cases") and analysis.get("edge_cases") != "Analysis required":
            readme = re.sub(
                r'(## 🧪 Edge Cases\n\n)- Empty / single-element collections\n- Boundary conditions & negative numbers\n- Duplicates & overflow constraints',
                r'\1' + analysis.get("edge_cases", ""),
                readme,
                flags=re.DOTALL
            )

        if analysis.get("lessons") and analysis.get("lessons") != "Analysis required":
            readme = re.sub(
                r'(## 📝 Lessons Learned\n\n)<!-- Personal retrospectives.*?-->',
                r'\1' + analysis.get("lessons", ""),
                readme,
                flags=re.DOTALL
            )

        if analysis.get("time_complexity") and analysis.get("time_complexity") != "Analysis required":
            readme = re.sub(
                r'- \*\*Time Complexity\*\*: \$O\(\\dots\)\$',
                f"- **Time Complexity**: {analysis['time_complexity']}",
                readme
            )
            
        if analysis.get("space_complexity") and analysis.get("space_complexity") != "Analysis required":
            readme = re.sub(
                r'- \*\*Space Complexity\*\*: \$O\(\\dots\)\$',
                f"- **Space Complexity**: {analysis['space_complexity']}",
                readme
            )
            
        return readme

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
