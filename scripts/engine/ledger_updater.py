"""
Ledger and Markdown Delimiter Updater.
Safely replaces content strictly bounded by explicit automation comments.
Guarantees non-destructive updates and aborts on missing/malformed delimiters.
"""

import re
from pathlib import Path
from typing import Optional, Tuple


class DelimiterError(Exception):
    """Raised when an automation delimiter block is missing, duplicated, or malformed."""
    pass


def extract_delimited_block(content: str, start_tag: str, end_tag: str) -> str:
    """
    Extracts the content between start_tag and end_tag.
    Raises DelimiterError if start_tag or end_tag is missing or malformed.
    """
    start_count = content.count(start_tag)
    end_count = content.count(end_tag)

    if start_count == 0:
        raise DelimiterError(f"Missing start delimiter: '{start_tag}'")
    if end_count == 0:
        raise DelimiterError(f"Missing end delimiter: '{end_tag}'")
    if start_count > 1:
        raise DelimiterError(f"Duplicate start delimiter detected ({start_count} occurrences): '{start_tag}'")
    if end_count > 1:
        raise DelimiterError(f"Duplicate end delimiter detected ({end_count} occurrences): '{end_tag}'")

    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag)

    if start_idx >= end_idx:
        raise DelimiterError(f"Malformed delimiters: start tag '{start_tag}' appears after end tag '{end_tag}'")

    inner_content = content[start_idx + len(start_tag) : end_idx]
    return inner_content


def replace_delimited_block(
    content: str,
    start_tag: str,
    end_tag: str,
    new_inner_content: str,
) -> str:
    """
    Replaces the content between start_tag and end_tag while preserving everything outside.
    Preserves tags exactly.
    """
    # Verify delimiter integrity first
    extract_delimited_block(content, start_tag, end_tag)

    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag)

    prefix = content[: start_idx + len(start_tag)]
    suffix = content[end_idx:]

    # Ensure clean spacing around inner content
    formatted_inner = new_inner_content
    if not formatted_inner.startswith("\n"):
        formatted_inner = "\n" + formatted_inner
    if not formatted_inner.endswith("\n"):
        formatted_inner = formatted_inner + "\n"

    return f"{prefix}{formatted_inner}{suffix}"


def update_file_delimited_block(
    file_path: Path,
    start_tag: str,
    end_tag: str,
    new_inner_content: str,
) -> bool:
    """
    Reads file_path, safely replaces the delimited block, and writes it back.
    Returns True if content changed, False if content was already identical.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Target file does not exist: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        original = f.read()

    updated = replace_delimited_block(original, start_tag, end_tag, new_inner_content)

    if original == updated:
        return False

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated)

    return True
