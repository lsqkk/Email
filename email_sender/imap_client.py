"""IMAP client — inbox reading and contact syncing."""

from __future__ import annotations

import email as email_lib
import imaplib
import logging
from datetime import datetime, timedelta
from typing import Optional

from email_sender.config import (
    load_config,
    resolve_imap_settings,
    get_account_config,
    DEFAULT_PROVIDER,
)
from email_sender.contacts import load_contacts, save_contacts

logger = logging.getLogger(__name__)

# Maps provider key to sent folder name
IMAP_SENT_FOLDERS: dict[str, str] = {
    "163": "已发送",
    "qq": "已发送",
    "126": "已发送",
    "sina": "已发送",
    "foxmail": "已发送",
    "yeah": "已发送",
    "139": "已发送",
    "189": "已发送",
    "gmail": "[Gmail]/Sent Mail",
    "outlook": "Sent Items",
    "yahoo": "Sent",
    "yandex": "Sent",
    "zoho": "Sent",
}

# Timeout for IMAP connections
IMAP_TIMEOUT = 30


def _connect_imap(
    email_address: str,
    password: str,
    provider_key: Optional[str] = None,
) -> Optional[imaplib.IMAP4_SSL]:
    """Connect to IMAP server and return connection object."""
    config = load_config()
    settings = resolve_imap_settings(config, provider_key)
    if not settings:
        return None

    try:
        mail = imaplib.IMAP4_SSL(
            settings.imap_server,
            settings.imap_port,
            timeout=IMAP_TIMEOUT,
        )
        mail.login(email_address, password)
        return mail
    except imaplib.IMAP4.error as e:
        logger.error("IMAP connection failed: %s", e)
        return None


def _find_folder(mail: imaplib.IMAP4_SSL, candidates: list[str]) -> Optional[str]:
    """Try to find and select a mailbox folder from candidates."""
    for folder in candidates:
        try:
            status, _ = mail.select(folder)
            if status == "OK":
                return folder
        except imaplib.IMAP4.error:
            continue
    return None


def sync_contacts_from_sent(
    email_address: str,
    password: str,
    provider_key: Optional[str] = None,
) -> tuple[int, str]:
    """Scan IMAP sent folder for recipient addresses and add to contacts.

    Returns (success_count, message).
    """
    config = load_config()
    provider_key = provider_key or config.get("EMAIL_PROVIDER") or DEFAULT_PROVIDER
    sent_folder = IMAP_SENT_FOLDERS.get(provider_key, "已发送")

    mail = _connect_imap(email_address, password, provider_key)
    if not mail:
        return 0, "IMAP not available for this provider"

    try:
        folder_candidates = [sent_folder, "Sent", "Sent Items", "[Gmail]/Sent Mail"]
        selected = _find_folder(mail, folder_candidates)

        if not selected:
            mail.logout()
            return 0, (
                f"Could not find sent folder on server "
                f"(tried: {', '.join(folder_candidates)})"
            )

        # Search for emails since the beginning of the current month
        since_date = datetime.now().replace(day=1).strftime("%d-%b-%Y")
        status, message_ids = mail.search(None, "SINCE", since_date)
        if status != "OK" or not message_ids[0]:
            mail.logout()
            return 0, "No sent emails found"

        ids = message_ids[0].split()
        ids = ids[-50:]  # Limit to last 50 to avoid timeout

        addresses: dict[str, str] = {}
        for mid in ids:
            try:
                status, data = mail.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (TO CC)])")
                if status != "OK":
                    continue
                msg = email_lib.message_from_bytes(data[0][1])
                for header in ("TO", "CC"):
                    raw = msg.get(header, "")
                    for addr in email_lib.utils.getaddresses([str(raw)]):
                        name, addr_email = addr
                        if addr_email and addr_email != email_address:
                            name = name or addr_email.split("@")[0]
                            addresses[addr_email] = name
            except Exception:
                continue

        mail.logout()

        contacts = load_contacts()
        added = 0
        existing_emails = set(contacts.values())

        for addr_email, name in addresses.items():
            if addr_email not in existing_emails:
                base_name = name
                counter = 1
                while base_name in contacts:
                    counter += 1
                    base_name = f"{name}_{counter}"
                contacts[base_name] = addr_email
                added += 1

        if added:
            save_contacts(contacts)

        return added, f"Found {len(addresses)} recipients, added {added} new contacts"

    except imaplib.IMAP4.error as e:
        return 0, f"IMAP error: {e}"
    except Exception as e:
        return 0, f"Error: {e}"


def read_inbox(
    email_address: str,
    password: str,
    max_emails: int = 10,
    provider_key: Optional[str] = None,
    folder: str = "INBOX",
    days_back: int = 7,
) -> list[dict[str, object]]:
    """Read recent emails from the IMAP inbox.

    Args:
        email_address: IMAP login email
        password: IMAP password
        max_emails: Maximum number of emails to return
        provider_key: Provider key (auto-detected from config if None)
        folder: IMAP folder to read from (default: INBOX)
        days_back: How many days back to search

    Returns:
        List of dicts with keys: message_id, subject, from_, date, body_preview
    """
    mail = _connect_imap(email_address, password, provider_key)
    if not mail:
        return []

    try:
        status, _ = mail.select(folder)
        if status != "OK":
            logger.error("Could not select folder: %s", folder)
            return []

        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
        status, message_ids = mail.search(None, "SINCE", since_date)
        if status != "OK" or not message_ids[0]:
            return []

        ids = message_ids[0].split()
        ids = ids[-max_emails:]

        emails: list[dict[str, object]] = []
        for mid in ids:
            try:
                status, data = mail.fetch(mid, "(BODY.PEEK[])")
                if status != "OK":
                    continue

                msg = email_lib.message_from_bytes(data[0][1])

                subject = msg.get("Subject", "(No Subject)")
                from_ = msg.get("From", "")
                date = msg.get("Date", "")
                message_id = msg.get("Message-ID", "")

                # Extract body preview (prefer plain text)
                body_preview = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body_preview = payload.decode(
                                    part.get_content_charset() or "utf-8",
                                    errors="replace",
                                )[:200]
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body_preview = payload.decode(
                            msg.get_content_charset() or "utf-8",
                            errors="replace",
                        )[:200]

                emails.append({
                    "message_id": message_id,
                    "subject": subject,
                    "from": from_,
                    "date": date,
                    "body_preview": body_preview,
                })
            except Exception:
                continue

        return emails

    except Exception as e:
        logger.error("Failed to read inbox: %s", e)
        return []
    finally:
        try:
            mail.logout()
        except Exception:
            pass
