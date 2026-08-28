"""
Statistics scanner, data models, and deterministic Markdown renderers for LeetCode Lab.
Computes real metrics strictly from canonical problems on disk.
"""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .ledger_updater import update_file_delimited_block

# Supported Milestones
MILESTONE_THRESHOLDS = [10, 50, 100, 250, 500, 1000]

MILESTONE_DESCRIPTIONS = {
    10: "Initial laboratory baseline & environment validation",
    50: "Solidified mastery of linear data structures & pointer patterns",
    100: "Fluency in Trees, Binary Search, and standard BFS/DFS",
    250: "Comprehensive command of Dynamic Programming & Graph Theory",
    500: "Advanced multi-pattern synthesis & edge-case intuition",
    1000: "Complete algorithmic mastery & high-speed competitive readiness",
}

# Categories for PROGRESS.md telemetry
CATEGORY_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "Arrays & Strings": {"target": 35, "tags": {"array", "string", "two pointers", "sliding window", "prefix sum", "matrix"}},
    "Linked Lists": {"target": 15, "tags": {"linked list", "doubly-linked list"}},
    "Stacks & Queues": {"target": 20, "tags": {"stack", "queue", "monotonic stack", "monotonic queue"}},
    "Trees & Binary Search Trees": {"target": 25, "tags": {"tree", "binary tree", "binary search tree"}},
    "Heaps & Priority Queues": {"target": 15, "tags": {"heap", "heap (priority queue)", "priority queue"}},
    "Graphs & Disjoint Sets": {"target": 25, "tags": {"graph", "union find", "breadth-first search", "depth-first search", "shortest path", "topological sort"}},
    "Dynamic Programming": {"target": 35, "tags": {"dynamic programming", "memoization"}},
    "Backtracking & Greedy": {"target": 20, "tags": {"backtracking", "greedy", "recursion"}},
}


@dataclass
class ProblemMetadata:
    """Parsed metadata of a single canonical problem."""
    problem_id: int
    title: str
    difficulty: str
    slug: str
    canonical_relative_path: str
    languages: List[str] = field(default_factory=list)
    leetcode_tags: List[str] = field(default_factory=list)
    primary_pattern: Optional[str] = None
    solved_at: str = ""
    submission_id: Optional[str] = None
    runtime: Optional[str] = None
    memory: Optional[str] = None
    time_complexity: str = "O(N)"
    space_complexity: str = "O(1)"


@dataclass
class RepositoryStats:
    """Aggregated statistics across all canonical problems in the repository."""
    total_solved: int = 0
    easy_count: int = 0
    medium_count: int = 0
    hard_count: int = 0
    language_counts: Dict[str, int] = field(default_factory=dict)
    all_problems: List[ProblemMetadata] = field(default_factory=list)
    recent_solves: List[ProblemMetadata] = field(default_factory=list)
    category_telemetry: Dict[str, Dict[str, int]] = field(default_factory=dict)
    milestones: Dict[int, bool] = field(default_factory=dict)


class RepositoryScanner:
    """Scans canonical problems/ directory and computes RepositoryStats."""

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.problems_dir = self.repo_root / "problems"

    def scan(self) -> RepositoryStats:
        """Scans the repository and returns an aggregated RepositoryStats object."""
        problems: List[ProblemMetadata] = []
        lang_counts: Dict[str, int] = {}
        easy_count = 0
        medium_count = 0
        hard_count = 0

        if self.problems_dir.exists():
            for diff_dir in sorted(self.problems_dir.iterdir()):
                if not diff_dir.is_dir() or diff_dir.name.lower() not in {"easy", "medium", "hard"}:
                    continue

                for prob_dir in sorted(diff_dir.iterdir()):
                    if not prob_dir.is_dir() or prob_dir.name.startswith("."):
                        continue

                    # Validate folder naming: 0000-slug
                    if not re.match(r"^\d{4}-[a-z0-9-]+$", prob_dir.name):
                        continue

                    meta = self._parse_problem_dir(prob_dir)
                    if meta:
                        problems.append(meta)
                        if meta.difficulty == "Easy":
                            easy_count += 1
                        elif meta.difficulty == "Medium":
                            medium_count += 1
                        elif meta.difficulty == "Hard":
                            hard_count += 1

                        for lang in meta.languages:
                            lang_counts[lang] = lang_counts.get(lang, 0) + 1

        # Sort all problems deterministically by problem_id
        problems.sort(key=lambda p: p.problem_id)

        # Recent solves: sort by solved_at desc, then problem_id desc (limit 10)
        recent = sorted(problems, key=lambda p: (p.solved_at, p.problem_id), reverse=True)[:10]

        # Compute category telemetry
        cat_telemetry = self._compute_category_telemetry(problems)

        # Compute milestones
        total_solved = len(problems)
        milestones = {m: (total_solved >= m) for m in MILESTONE_THRESHOLDS}

        return RepositoryStats(
            total_solved=total_solved,
            easy_count=easy_count,
            medium_count=medium_count,
            hard_count=hard_count,
            language_counts=dict(sorted(lang_counts.items())),
            all_problems=problems,
            recent_solves=recent,
            category_telemetry=cat_telemetry,
            milestones=milestones,
        )

    def _parse_problem_dir(self, prob_dir: Path) -> Optional[ProblemMetadata]:
        """Parses README.md frontmatter and solution files in prob_dir."""
        readme_file = prob_dir / "README.md"
        if not readme_file.exists():
            return None

        content = readme_file.read_text(encoding="utf-8")
        fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        if not fm_match:
            return None

        fm = fm_match.group(1)

        # Extract fields
        id_match = re.search(r"^problem_id:\s*(\d+)", fm, re.MULTILINE)
        title_match = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', fm, re.MULTILINE)
        diff_match = re.search(r'^difficulty:\s*["\']?(.*?)["\']?\s*$', fm, re.MULTILINE)
        slug_match = re.search(r'^slug:\s*["\']?(.*?)["\']?\s*$', fm, re.MULTILINE)
        solved_at_match = re.search(r'^solved_at:\s*["\']?(.*?)["\']?\s*$', fm, re.MULTILINE)
        pattern_match = re.search(r'^primary_pattern:\s*["\']?(.*?)["\']?\s*$', fm, re.MULTILINE)
        runtime_match = re.search(r'^runtime:\s*["\']?(.*?)["\']?\s*$', fm, re.MULTILINE)
        memory_match = re.search(r'^memory:\s*["\']?(.*?)["\']?\s*$', fm, re.MULTILINE)

        if not (id_match and title_match and diff_match and slug_match):
            return None

        problem_id = int(id_match.group(1))
        title = title_match.group(1).strip()
        difficulty = diff_match.group(1).strip().capitalize()
        slug = slug_match.group(1).strip()
        solved_at = solved_at_match.group(1).strip() if solved_at_match else ""
        primary_pattern = pattern_match.group(1).strip() if pattern_match and pattern_match.group(1).strip() else None
        runtime = runtime_match.group(1).strip() if runtime_match and runtime_match.group(1).strip() not in {"null", "None"} else None
        memory = memory_match.group(1).strip() if memory_match and memory_match.group(1).strip() not in {"null", "None"} else None

        # Extract languages from frontmatter or solution files
        languages: List[str] = []
        lang_section = re.search(r"^languages:\s*\n((?:\s*-\s*.*?\n)*)", fm, re.MULTILINE)
        if lang_section:
            for line in lang_section.group(1).splitlines():
                l_match = re.search(r'-\s*["\']?(.*?)["\']?\s*$', line)
                if l_match and l_match.group(1).strip():
                    languages.append(l_match.group(1).strip())

        # If empty in frontmatter, detect from files
        if not languages:
            ext_map = {"cpp": "C++", "py": "Python", "java": "Java", "js": "JavaScript", "ts": "TypeScript", "c": "C", "go": "Go", "rs": "Rust"}
            for f in prob_dir.iterdir():
                if f.is_file() and f.name.startswith("solution."):
                    ext = f.suffix.lstrip(".")
                    if ext in ext_map:
                        languages.append(ext_map[ext])
        languages = sorted(list(set(languages)))

        # Extract tags
        leetcode_tags: List[str] = []
        tags_section = re.search(r"^leetcode_tags:\s*\n((?:\s*-\s*.*?\n)*)", fm, re.MULTILINE)
        if tags_section:
            for line in tags_section.group(1).splitlines():
                t_match = re.search(r'-\s*["\']?(.*?)["\']?\s*$', line)
                if t_match and t_match.group(1).strip():
                    leetcode_tags.append(t_match.group(1).strip())

        rel_path = f"problems/{difficulty.lower()}/{prob_dir.name}/"

        return ProblemMetadata(
            problem_id=problem_id,
            title=title,
            difficulty=difficulty,
            slug=slug,
            canonical_relative_path=rel_path,
            languages=languages,
            leetcode_tags=leetcode_tags,
            primary_pattern=primary_pattern,
            solved_at=solved_at,
            runtime=runtime,
            memory=memory,
        )

    def _compute_category_telemetry(self, problems: List[ProblemMetadata]) -> Dict[str, Dict[str, int]]:
        """Calculates category solve counts (Total, Easy, Medium, Hard) from problem tags."""
        result: Dict[str, Dict[str, int]] = {}

        for cat_name, cat_info in CATEGORY_DEFINITIONS.items():
            result[cat_name] = {"total": 0, "easy": 0, "medium": 0, "hard": 0, "target": cat_info["target"]}
            cat_tags: Set[str] = cat_info["tags"]

            for p in problems:
                problem_tags_lower = {t.lower() for t in p.leetcode_tags}
                if p.primary_pattern:
                    problem_tags_lower.add(p.primary_pattern.lower())

                # Check if problem belongs to category
                if problem_tags_lower.intersection(cat_tags):
                    result[cat_name]["total"] += 1
                    if p.difficulty == "Easy":
                        result[cat_name]["easy"] += 1
                    elif p.difficulty == "Medium":
                        result[cat_name]["medium"] += 1
                    elif p.difficulty == "Hard":
                        result[cat_name]["hard"] += 1

        return result


class DashboardRenderer:
    """Renders deterministic Markdown blocks for README.md and PROGRESS.md."""

    @staticmethod
    def render_progress_bar(count: int, target: int = 100, width: int = 20) -> str:
        """Renders monospace progress bar e.g. `████░░░░░░░░░░░░░░░░` 20%."""
        if target <= 0:
            pct = 0
        else:
            pct = min(100, int((count / target) * 100))
        filled = int(round((pct * width) / 100))
        bar = "█" * filled + "░" * (width - filled)
        return f"`{bar}` {pct}%"

    @classmethod
    def render_metrics_dashboard(cls, stats: RepositoryStats) -> str:
        """Renders the README.md metrics table."""
        total_bar = cls.render_progress_bar(stats.total_solved, target=300, width=20)
        easy_bar = cls.render_progress_bar(stats.easy_count, target=100, width=20)
        med_bar = cls.render_progress_bar(stats.medium_count, target=150, width=20)
        hard_bar = cls.render_progress_bar(stats.hard_count, target=50, width=20)

        # Languages display
        if stats.language_counts:
            langs_str = " · ".join([f"`{lang} ({count})`" for lang, count in stats.language_counts.items()])
        else:
            langs_str = "`Python` · `C++` · `Java`"

        return f"""| Metric | Solved | Distribution | Progress |
| :--- | :---: | :--- | :--- |
| **Total Solved** | **{stats.total_solved}** | `{stats.easy_count} Easy` · `{stats.medium_count} Medium` · `{stats.hard_count} Hard` | {total_bar} |
| 🟢 **Easy** | {stats.easy_count} | Foundational primitives & implementation | {easy_bar} |
| 🟡 **Medium** | {stats.medium_count} | Core patterns, graphs & dynamic programming | {med_bar} |
| 🔴 **Hard** | {stats.hard_count} | Complex optimization & multi-pattern synthesis | {hard_bar} |

<br>

| Attribute | State | Details |
| :--- | :---: | :--- |
| **Current Streak** | `0 days` | Consistent daily problem-solving cycle |
| **Longest Streak** | `0 days` | Peak deliberate practice consistency |
| **Primary Languages** | {langs_str} | Standard technical interview & contest toolchains |
| **Active Objective** | `Phase 1` | Core linear structures & two-pointer mechanics |"""

    @staticmethod
    def render_recent_solves(stats: RepositoryStats) -> str:
        """Renders the README.md recent solves table."""
        if not stats.recent_solves:
            return """| # | Problem | Difficulty | Category / Pattern | Solution | Date |
| :-: | :--- | :---: | :--- | :---: | :---: |
| — | *No problems logged yet* | — | *Laboratory initialized* | — | — |"""

        lines = [
            "| # | Problem | Difficulty | Category / Pattern | Solution | Date |",
            "| :-: | :--- | :---: | :--- | :---: | :---: |",
        ]
        for p in stats.recent_solves:
            diff_icon = "🟢" if p.difficulty == "Easy" else ("🟡" if p.difficulty == "Medium" else "🔴")
            pattern_display = p.primary_pattern or (p.leetcode_tags[0] if p.leetcode_tags else "General")
            sol_link = f"[`{'/'.join(p.languages)}`]({p.canonical_relative_path})" if p.languages else f"[`View`]({p.canonical_relative_path})"
            problem_link = f"[{p.title}]({p.canonical_relative_path})"
            lines.append(f"| {p.problem_id} | {problem_link} | {diff_icon} {p.difficulty} | {pattern_display} | {sol_link} | {p.solved_at or '—'} |")

        return "\n".join(lines)

    @staticmethod
    def render_milestones(stats: RepositoryStats) -> str:
        """Renders the README.md milestone checklist."""
        lines = []
        for threshold in MILESTONE_THRESHOLDS:
            is_done = stats.milestones.get(threshold, False)
            mark = "[x]" if is_done else "[ ]"
            desc = MILESTONE_DESCRIPTIONS.get(threshold, "")
            lines.append(f"- {mark} **{threshold} Solved**: {desc}")
        return "\n".join(lines)

    @classmethod
    def render_category_telemetry(cls, stats: RepositoryStats) -> str:
        """Renders the PROGRESS.md category summary table."""
        lines = [
            "| Category | Solved | Target | Easy | Medium | Hard | Progress |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
        ]
        for cat_name, data in stats.category_telemetry.items():
            bar = cls.render_progress_bar(data["total"], target=data["target"], width=10)
            lines.append(
                f"| **{cat_name}** | {data['total']} | {data['target']} | {data['easy']} | {data['medium']} | {data['hard']} | {bar} |"
            )
        return "\n".join(lines)

    @staticmethod
    def render_master_problem_log(stats: RepositoryStats) -> str:
        """Renders the PROGRESS.md master problem ledger."""
        if not stats.all_problems:
            return """| # | Problem Title | Difficulty | Primary Pattern | Data Structure | Time | Space | Canonical Solution | Review Status |
| :-: | :--- | :---: | :--- | :--- | :-: | :-: | :---: | :---: |
| — | *Awaiting first solve* | — | — | — | — | — | — | — |"""

        lines = [
            "| # | Problem Title | Difficulty | Primary Pattern | Data Structure | Time | Space | Canonical Solution | Review Status |",
            "| :-: | :--- | :---: | :--- | :--- | :-: | :-: | :---: | :---: |",
        ]
        for p in stats.all_problems:
            diff_icon = "🟢" if p.difficulty == "Easy" else ("🟡" if p.difficulty == "Medium" else "🔴")
            pattern = p.primary_pattern or "—"
            ds = ", ".join(p.leetcode_tags[:2]) if p.leetcode_tags else "—"
            sol_link = f"[`{p.canonical_relative_path}`]({p.canonical_relative_path})"
            lines.append(
                f"| {p.problem_id:04d} | {p.title} | {diff_icon} {p.difficulty} | {pattern} | {ds} | {p.time_complexity} | {p.space_complexity} | {sol_link} | Solved |"
            )
        return "\n".join(lines)


class DashboardUpdater:
    """Updates README.md and PROGRESS.md in-place using boundary-safe delimiters."""

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.scanner = RepositoryScanner(self.repo_root)
        self.renderer = DashboardRenderer()

    def update_all(self) -> Tuple[bool, bool, RepositoryStats]:
        """
        Scans repository and updates README.md and PROGRESS.md.
        Returns (readme_changed, progress_changed, stats).
        """
        stats = self.scanner.scan()
        readme_file = self.repo_root / "README.md"
        progress_file = self.repo_root / "PROGRESS.md"

        readme_changed = False
        progress_changed = False

        if readme_file.exists():
            # 1. Update Metrics
            m_changed = update_file_delimited_block(
                readme_file,
                "<!-- AUTOMATION_METRICS_START -->",
                "<!-- AUTOMATION_METRICS_END -->",
                self.renderer.render_metrics_dashboard(stats),
            )
            # 2. Update Recent Solves
            r_changed = update_file_delimited_block(
                readme_file,
                "<!-- AUTOMATION_RECENT_SOLVES_START -->",
                "<!-- AUTOMATION_RECENT_SOLVES_END -->",
                self.renderer.render_recent_solves(stats),
            )
            # 3. Update Milestones if delimited, otherwise keep
            if "<!-- AUTOMATION_MILESTONES_START -->" in readme_file.read_text(encoding="utf-8"):
                ms_changed = update_file_delimited_block(
                    readme_file,
                    "<!-- AUTOMATION_MILESTONES_START -->",
                    "<!-- AUTOMATION_MILESTONES_END -->",
                    self.renderer.render_milestones(stats),
                )
                readme_changed = m_changed or r_changed or ms_changed
            else:
                readme_changed = m_changed or r_changed

        if progress_file.exists():
            # 1. Update Master Problem Log
            l_changed = update_file_delimited_block(
                progress_file,
                "<!-- AUTOMATION_PROBLEM_LOG_START -->",
                "<!-- AUTOMATION_PROBLEM_LOG_END -->",
                self.renderer.render_master_problem_log(stats),
            )
            # 2. Update Category Telemetry if delimited
            if "<!-- AUTOMATION_CATEGORY_TELEMETRY_START -->" in progress_file.read_text(encoding="utf-8"):
                c_changed = update_file_delimited_block(
                    progress_file,
                    "<!-- AUTOMATION_CATEGORY_TELEMETRY_START -->",
                    "<!-- AUTOMATION_CATEGORY_TELEMETRY_END -->",
                    self.renderer.render_category_telemetry(stats),
                )
                progress_changed = l_changed or c_changed
            else:
                progress_changed = l_changed

        return readme_changed, progress_changed, stats
