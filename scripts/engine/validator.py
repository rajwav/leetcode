"""
Validator and schema normalization for LeetCode Lab submissions.
Enforces strict security boundaries, path traversal prevention, and typed data integrity.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Set

# Allowed difficulties
VALID_DIFFICULTIES: Set[str] = {"Easy", "Medium", "Hard"}

# Canonical language normalization mapping
LANGUAGE_MAP: Dict[str, str] = {
    "cpp": "cpp",
    "c++": "cpp",
    "g++": "cpp",
    "python": "python3",
    "python3": "python3",
    "py": "python3",
    "java": "java",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "c": "c",
    "go": "go",
    "golang": "go",
    "rust": "rust",
    "rs": "rust",
}

# File extensions for supported canonical languages
LANGUAGE_EXTENSIONS: Dict[str, str] = {
    "cpp": "cpp",
    "python3": "py",
    "java": "java",
    "javascript": "js",
    "typescript": "ts",
    "c": "c",
    "go": "go",
    "rust": "rs",
}

# Regex for safe slug: alphanumeric lowercase with hyphens, no leading/trailing hyphen
SLUG_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Max code size (500 KB)
MAX_CODE_SIZE_BYTES = 500 * 1024


class ValidationError(Exception):
    """Raised when a submission payload fails schema or security validation."""
    pass


@dataclass
class SubmissionPayload:
    submission_id: str
    problem_id: int
    slug: str
    title: str
    difficulty: str
    language: str
    extension: str
    code: str
    status: str
    runtime: Optional[str] = None
    memory: Optional[str] = None
    timestamp: Optional[str] = None
    leetcode_tags: List[str] = field(default_factory=list)

    @property
    def canonical_dir_name(self) -> str:
        """Returns 4-digit zero-padded problem directory name, e.g. '0001-two-sum'."""
        return f"{self.problem_id:04d}-{self.slug}"

    @property
    def canonical_relative_path(self) -> str:
        """Returns relative path within repo, e.g. 'problems/easy/0001-two-sum/'."""
        return f"problems/{self.difficulty.lower()}/{self.canonical_dir_name}/"


def validate_submission(raw: Any) -> SubmissionPayload:
    """
    Validates and normalizes an incoming raw submission payload.
    Raises ValidationError if any field is invalid or security checks fail.
    """
    if not isinstance(raw, dict):
        raise ValidationError(f"Payload must be a JSON object / dict, got {type(raw).__name__}")

    # 1. Validate status (Accepted only)
    raw_status = raw.get("status") or raw.get("status_msg")
    if not raw_status or str(raw_status).strip().lower() not in {"accepted", "success", "10"}:
        raise ValidationError(
            f"Only 'Accepted' submissions are processed. Received status: '{raw_status}'"
        )
    status = "Accepted"

    # 2. Validate problem_id
    raw_id = raw.get("problem_id") or raw.get("question_id") or raw.get("questionFrontendId")
    if raw_id is None:
        raise ValidationError("Missing required field: 'problem_id' (or 'questionFrontendId')")
    try:
        problem_id = int(raw_id)
        if problem_id <= 0 or problem_id > 100000:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValidationError(f"'problem_id' must be a positive integer between 1 and 100000, got: {raw_id}")

    # 3. Validate slug
    raw_slug = raw.get("slug") or raw.get("titleSlug")
    if not raw_slug or not isinstance(raw_slug, str):
        raise ValidationError("Missing or invalid required field: 'slug'")
    slug = raw_slug.strip().lower()
    
    # Path traversal and injection checks
    if ".." in slug or "/" in slug or "\\" in slug or "\x00" in slug:
        raise ValidationError(f"Malicious slug detected (path traversal characters): '{slug}'")
    if not SLUG_REGEX.match(slug):
        raise ValidationError(
            f"Slug must contain only lowercase alphanumeric characters and hyphens: '{slug}'"
        )

    # 4. Validate title
    raw_title = raw.get("title")
    if not raw_title or not isinstance(raw_title, str) or not raw_title.strip():
        raise ValidationError("Missing or invalid required field: 'title'")
    title = raw_title.strip()
    if len(title) > 200:
        raise ValidationError("Title exceeds maximum length of 200 characters")

    # 5. Validate difficulty
    raw_diff = raw.get("difficulty")
    if not raw_diff or not isinstance(raw_diff, str):
        raise ValidationError("Missing or invalid required field: 'difficulty'")
    diff_normalized = raw_diff.strip().capitalize()
    if diff_normalized not in VALID_DIFFICULTIES:
        raise ValidationError(
            f"Invalid difficulty '{raw_diff}'. Must be one of: {sorted(list(VALID_DIFFICULTIES))}"
        )
    difficulty = diff_normalized

    # 6. Validate language
    raw_lang = raw.get("language") or raw.get("lang")
    if not raw_lang or not isinstance(raw_lang, str):
        raise ValidationError("Missing or invalid required field: 'language'")
    lang_clean = raw_lang.strip().lower()
    if lang_clean not in LANGUAGE_MAP:
        raise ValidationError(
            f"Unsupported language '{raw_lang}'. Supported: {sorted(list(set(LANGUAGE_MAP.keys())))}"
        )
    canonical_lang = LANGUAGE_MAP[lang_clean]
    extension = LANGUAGE_EXTENSIONS[canonical_lang]

    # 7. Validate code
    raw_code = raw.get("code") or raw.get("typed_code")
    if not raw_code or not isinstance(raw_code, str) or not raw_code.strip():
        raise ValidationError("Missing or empty required field: 'code'")
    code = raw_code.strip()
    if len(code.encode("utf-8")) > MAX_CODE_SIZE_BYTES:
        raise ValidationError(
            f"Source code exceeds maximum allowed size ({MAX_CODE_SIZE_BYTES} bytes)"
        )

    # 8. Validate submission_id
    raw_sub_id = raw.get("submission_id") or raw.get("id")
    if raw_sub_id is None:
        raise ValidationError("Missing required field: 'submission_id'")
    submission_id = str(raw_sub_id).strip()
    if not submission_id or len(submission_id) > 100 or ".." in submission_id:
        raise ValidationError(f"Invalid 'submission_id': '{submission_id}'")

    # 9. Optional fields
    runtime = raw.get("runtime") or raw.get("status_runtime")
    if runtime and isinstance(runtime, str):
        runtime = runtime.strip()
    else:
        runtime = None

    memory = raw.get("memory") or raw.get("status_memory")
    if memory and isinstance(memory, str):
        memory = memory.strip()
    else:
        memory = None

    timestamp = raw.get("timestamp") or raw.get("date_solved")
    if timestamp and isinstance(timestamp, str):
        timestamp = timestamp.strip()
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    raw_tags = raw.get("leetcode_tags") or raw.get("topicTags") or []
    leetcode_tags: List[str] = []
    if isinstance(raw_tags, list):
        for tag in raw_tags:
            if isinstance(tag, str) and tag.strip():
                leetcode_tags.append(tag.strip())
            elif isinstance(tag, dict) and "name" in tag and isinstance(tag["name"], str):
                leetcode_tags.append(tag["name"].strip())

    return SubmissionPayload(
        submission_id=submission_id,
        problem_id=problem_id,
        slug=slug,
        title=title,
        difficulty=difficulty,
        language=canonical_lang,
        extension=extension,
        code=code,
        status=status,
        runtime=runtime,
        memory=memory,
        timestamp=timestamp,
        leetcode_tags=leetcode_tags,
    )
