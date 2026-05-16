"""Send log management — CSV with rotation."""

from __future__ import annotations

import csv
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from email_sender.config import BASE_DIR

logger = logging.getLogger(__name__)

SEND_LOG_FILE = BASE_DIR / "send_log.csv"
MAX_LOG_ROWS = 1000
MAX_LOG_BACKUPS = 3


def _rotate_log() -> None:
    """Rotate send_log.csv when it exceeds MAX_LOG_ROWS."""
    if not SEND_LOG_FILE.exists():
        return

    try:
        with open(SEND_LOG_FILE, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    except (csv.Error, OSError) as e:
        logger.warning("Failed to read send log for rotation: %s", e)
        return

    if len(rows) < MAX_LOG_ROWS:
        return

    # Rotate: shift backups
    for i in range(MAX_LOG_BACKUPS - 1, 0, -1):
        src = SEND_LOG_FILE.with_suffix(f".{i}.csv")
        dst = SEND_LOG_FILE.with_suffix(f".{i + 1}.csv")
        if src.exists():
            try:
                os.replace(src, dst)
            except OSError as e:
                logger.warning("Log rotation failed (backup %d): %s", i, e)

    # Move current to .1
    backup_path = SEND_LOG_FILE.with_suffix(".1.csv")
    try:
        os.replace(SEND_LOG_FILE, backup_path)
    except OSError as e:
        logger.warning("Log rotation failed (move to .1): %s", e)


def append_send_log(entry: dict[str, str]) -> None:
    """Append a send entry to CSV log with auto-rotation."""
    # Check rotation before writing
    if SEND_LOG_FILE.exists():
        try:
            with open(SEND_LOG_FILE, "r", encoding="utf-8", newline="") as f:
                row_count = sum(1 for _ in f)
            if row_count > MAX_LOG_ROWS:
                _rotate_log()
        except (csv.Error, OSError):
            pass

    is_new = not SEND_LOG_FILE.exists()
    try:
        with open(SEND_LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp", "sender", "recipient", "subject",
                "cc", "bcc", "attachments", "status",
            ])
            if is_new:
                writer.writeheader()
            writer.writerow(entry)
    except OSError as e:
        logger.warning("Failed to write send log: %s", e)


def show_send_log(lines: int = 20) -> str:
    """Show recent send log entries."""
    if not SEND_LOG_FILE.exists():
        return "No send history yet."
    try:
        with open(SEND_LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return "No send history yet."
        recent = rows[-lines:]
        result: list[str] = [
            f"{'Time':<22} {'To':<30} {'Subject':<40} {'Status':<8}"
        ]
        result.append("-" * 110)
        for r in recent:
            ts = r.get("timestamp", "")[-19:]
            to = r.get("recipient", "")[:30]
            subj = r.get("subject", "")[:40]
            status = r.get("status", "")
            result.append(f"{ts:<22} {to:<30} {subj:<40} {status:<8}")
        return "\n".join(result)
    except (csv.Error, OSError) as e:
        return f"Error reading send log: {e}"
