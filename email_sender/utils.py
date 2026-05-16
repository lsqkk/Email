"""Utility functions — validation, formatting, helpers."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional


# Default attachment size limit: 25 MB (most providers)
DEFAULT_MAX_ATTACHMENT_MB = 25
DEFAULT_MAX_ATTACHMENT_BYTES = DEFAULT_MAX_ATTACHMENT_MB * 1024 * 1024


def is_valid_email(email_str: str) -> bool:
    """Validate email format (basic sanity check)."""
    if not email_str or not email_str.strip():
        return False
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email_str.strip()))


def validate_attachment(
    filepath: str,
    max_bytes: int = DEFAULT_MAX_ATTACHMENT_BYTES,
) -> tuple[bool, str]:
    """Validate an attachment file exists and is within size limits.

    Returns (is_valid, message).
    """
    path = Path(filepath)
    if not path.exists():
        return False, f"Attachment not found: {filepath}"
    if not path.is_file():
        return False, f"Not a file: {filepath}"
    size = path.stat().st_size
    if size > max_bytes:
        mb = max_bytes / (1024 * 1024)
        actual_mb = size / (1024 * 1024)
        return False, (
            f"Attachment too large: {filepath} ({actual_mb:.1f} MB, "
            f"limit: {mb:.0f} MB)"
        )
    return True, ""


def validate_attachments(
    filepaths: Optional[list[str]],
    max_bytes: int = DEFAULT_MAX_ATTACHMENT_BYTES,
) -> tuple[bool, list[str]]:
    """Validate multiple attachments.

    Returns (all_valid, error_messages).
    """
    if not filepaths:
        return True, []
    errors: list[str] = []
    for fp in filepaths:
        ok, msg = validate_attachment(fp, max_bytes)
        if not ok:
            errors.append(msg)
    return len(errors) == 0, errors


def format_result_json(data: Any) -> str:
    """Format data as JSON for --json output mode.

    Uses ensure_ascii=False for CJK character support.
    """
    return json.dumps(data, ensure_ascii=False, indent=2)


def html_to_plain_text(html: str) -> str:
    """Crude HTML-to-text conversion for fallback plain text.

    This is a best-effort conversion using regex. It handles common cases
    but is not a full HTML parser.
    """
    text = html
    # Remove <style> blocks
    text = re.sub(r'(?is)<style[^>]*>.*?</style>', '', text)
    # Remove <script> blocks
    text = re.sub(r'(?is)<script[^>]*>.*?</script>', '', text)
    # Replace <br> and <p> with newlines
    text = re.sub(r'(?is)<br\s*/?>', '\n', text)
    text = re.sub(r'(?is)</p>', '\n\n', text)
    text = re.sub(r'(?is)</div>', '\n', text)
    text = re.sub(r'(?is)</tr>', '\n', text)
    text = re.sub(r'(?is)</li>', '\n', text)
    # Replace <td>/<th> with spaces/tabs
    text = re.sub(r'(?is)</t[dh]>', ' ', text)
    # Strip all remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Trim leading/trailing whitespace per line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines).strip()
    return text


def resolve_name_from_email(email: str) -> str:
    """Extract a display name hint from an email address."""
    return email.split('@')[0]


def format_bytes(size_bytes: int) -> str:
    """Format byte count to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
