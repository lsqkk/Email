"""Contact management — CRUD, search, file-locked I/O."""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from email_sender.config import BASE_DIR
from email_sender.utils import is_valid_email

logger = logging.getLogger(__name__)

CONTACTS_FILE = BASE_DIR / "contacts.json"
_LOCK_FILE = BASE_DIR / "contacts.json.lock"
_LOCK_TIMEOUT = 5.0  # seconds
_LOCK_RETRY_INTERVAL = 0.05  # 50ms


@contextmanager
def _file_lock() -> Iterator[None]:
    """Cross-platform file lock using lock-file pattern.

    Uses os.open with O_CREAT | O_EXCL for atomic creation.
    Compatible with Windows, Linux, and macOS.
    """
    lock_path = str(_LOCK_FILE)
    start = time.time()
    acquired = False
    try:
        while time.time() - start < _LOCK_TIMEOUT:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.close(fd)
                acquired = True
                break
            except FileExistsError:
                time.sleep(_LOCK_RETRY_INTERVAL)

        if not acquired:
            logger.warning("Could not acquire lock for %s after %.1fs", CONTACTS_FILE, _LOCK_TIMEOUT)

        yield
    finally:
        if acquired:
            try:
                os.unlink(lock_path)
            except OSError:
                pass


def load_contacts() -> dict[str, str]:
    """Load contacts from JSON file with file locking.

    Returns dict of {name: email}; empty dict if file missing or corrupted.
    """
    if not CONTACTS_FILE.exists():
        return {}
    with _file_lock():
        try:
            data = json.loads(CONTACTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            return {}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read contacts: %s", e)
            return {}


def save_contacts(contacts: dict[str, str]) -> None:
    """Save contacts dict to JSON file with file locking."""
    with _file_lock():
        try:
            CONTACTS_FILE.write_text(
                json.dumps(contacts, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("Failed to write contacts: %s", e)
            raise


def add_contact(name: str, email: str) -> tuple[bool, str]:
    """Add or update a contact. Returns (success, message)."""
    if not is_valid_email(email):
        return False, f"Invalid email: {email}"
    contacts = load_contacts()
    existed = name in contacts
    contacts[name] = email
    save_contacts(contacts)
    action = "Updated" if existed else "Saved"
    return True, f"{action} contact: {name} <{email}>"


def delete_contact(name: str) -> tuple[bool, str]:
    """Delete a contact. Returns (success, message)."""
    contacts = load_contacts()
    if name not in contacts:
        return False, f"Contact not found: {name}"
    email = contacts.pop(name)
    save_contacts(contacts)
    return True, f"Deleted contact: {name} <{email}>"


def list_contacts() -> str:
    """Return formatted contact list string."""
    contacts = load_contacts()
    if not contacts:
        return "No contacts saved."
    lines: list[str] = [f"{'Name':<20} Email", "-" * 50]
    for name in sorted(contacts):
        lines.append(f"{name:<20} {contacts[name]}")
    return "\n".join(lines)


def find_contact(query: str) -> tuple[Optional[str], Optional[str]]:
    """Find a contact by name.

    Returns (email, warning_message).
      - email is None if not found.
      - warning_message is set when multiple fuzzy matches exist.
    """
    contacts = load_contacts()
    if not contacts:
        return None, None

    # 1. Exact match
    if query in contacts:
        return contacts[query], None

    # 2. Case-insensitive partial match
    query_lower = query.lower()
    matches: list[tuple[str, str]] = []
    for name, email in contacts.items():
        if query_lower in name.lower():
            matches.append((name, email))

    if len(matches) == 0:
        return None, None

    if len(matches) == 1:
        return matches[0][1], None

    # Multiple matches: warn but return the first
    names = [m[0] for m in matches]
    warning = (
        f"Multiple contacts matched '{query}': {', '.join(names)}. "
        f"Using '{matches[0][0]}'. Use exact name to avoid ambiguity."
    )
    return matches[0][1], warning


def auto_save_contact(name: str, email: str) -> None:
    """Auto-save a contact without overwriting existing alias with a different email."""
    contacts = load_contacts()
    if name in contacts:
        existing = contacts[name]
        if existing != email:
            logger.info("Contact '%s' already exists as <%s>, not overwriting.", name, existing)
            return
    contacts[name] = email
    save_contacts(contacts)
    logger.info("Auto-saved contact: %s <%s>", name, email)
