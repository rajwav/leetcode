"""
LeetCode Lab Engine package.
Provides schema validation, problem storage, ledger updates, indexing, and Git management.
"""

from .validator import SubmissionPayload, ValidationError, validate_submission
from .ledger_updater import DelimiterError, extract_delimited_block, replace_delimited_block, update_file_delimited_block
from .problem_manager import ImportResult, ProblemManager, SolutionConflictError
from .index_linker import IndexLinker
from .statistics import (
    ProblemMetadata,
    RepositoryStats,
    RepositoryScanner,
    DashboardRenderer,
    DashboardUpdater,
)
from .git_manager import GitManager, GitSafetyError

__all__ = [
    "SubmissionPayload",
    "ValidationError",
    "validate_submission",
    "DelimiterError",
    "extract_delimited_block",
    "replace_delimited_block",
    "update_file_delimited_block",
    "ImportResult",
    "ProblemManager",
    "SolutionConflictError",
    "IndexLinker",
    "ProblemMetadata",
    "RepositoryStats",
    "RepositoryScanner",
    "DashboardRenderer",
    "DashboardUpdater",
    "GitManager",
    "GitSafetyError",
]
