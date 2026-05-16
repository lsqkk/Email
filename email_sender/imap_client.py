"""IMAP client — inbox reading and contact syncing."""

from __future__ import annotations

import email as email_lib
import imaplib
import logging
import poplib
from datetime import datetime, timedelta
from typing import Optional

from email_sender.config import (
    load_config,
    resolve_imap_settings,
    resolve_pop3_settings,
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

        # Send IMAP ID command (RFC 2971) — required by some providers
        # (e.g. 163.com) to whitelist the client before folder access.
        try:
            imaplib.Commands['ID'] = ('AUTH',)
            mail._simple_command(
                'ID',
                '("name" "ClaudeMail" "version" "1.0.0" '
                '"vendor" "Python" "support-email" "' + email_address + '")'
            )
        except Exception:
            pass

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


def read_inbox_pop3(
    email_address: str,
    password: str,
    max_emails: int = 10,
    provider_key: Optional[str] = None,
) -> list[dict[str, object]]:
    """Read recent emails from the POP3 inbox.

    POP3 is simpler than IMAP — it lists all messages sequentially.
    This function reads the last N messages from the server.

    Args:
        email_address: POP3 login email
        password: POP3 password
        max_emails: Maximum number of emails to return (from newest)
        provider_key: Provider key (auto-detected from config if None)

    Returns:
        List of dicts with keys: message_id, subject, from_, date, body_preview
    """
    config = load_config()
    provider_key = provider_key or config.get("EMAIL_PROVIDER") or DEFAULT_PROVIDER
    settings = resolve_pop3_settings(config, provider_key)
    if not settings:
        logger.error("POP3 not available for provider '%s'", provider_key)
        return []

    try:
        pop = poplib.POP3_SSL(settings.pop3_server, settings.pop3_port, timeout=IMAP_TIMEOUT)
        pop.user(email_address)
        pop.pass_(password)
    except Exception as e:
        logger.error("POP3 connection failed: %s", e)
        return []

    try:
        count, size = pop.stat()
        if count == 0:
            return []

        # POP3 indexes are 1-based; we want the last N messages
        start = max(1, count - max_emails + 1)
        emails: list[dict[str, object]] = []

        for i in range(start, count + 1):
            try:
                resp, lines, octets = pop.retr(i)
                raw = b"\n".join(lines)
                msg = email_lib.message_from_bytes(raw)

                subject = msg.get("Subject", "(No Subject)")
                from_ = msg.get("From", "")
                date = msg.get("Date", "")
                message_id = msg.get("Message-ID", f"pop3-{i}@{email_address}")

                # Decode subject
                from email.header import decode_header
                try:
                    subj_parts = decode_header(subject)
                    subject = "".join(
                        (part.decode(charset or "utf-8") if isinstance(part, bytes) else part)
                        for part, charset in subj_parts
                    )
                except Exception:
                    pass

                # Extract body preview
                body_preview = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        ct = part.get_content_type()
                        payload = part.get_payload(decode=True)
                        if payload and ct == "text/plain":
                            cs = part.get_content_charset() or "utf-8"
                            try:
                                body_preview = payload.decode(cs, errors="replace")[:500]
                            except Exception:
                                body_preview = payload.decode("utf-8", errors="replace")[:500]
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        cs = msg.get_content_charset() or "utf-8"
                        try:
                            body_preview = payload.decode(cs, errors="replace")[:500]
                        except Exception:
                            body_preview = payload.decode("utf-8", errors="replace")[:500]

                # Check for attachments
                attachments: list[str] = []
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_disposition() == "attachment":
                            fn = part.get_filename()
                            if fn:
                                try:
                                    fn_parts = email_lib.header.decode_header(fn)
                                    fn = "".join(
                                        (p.decode(c or "utf-8") if isinstance(p, bytes) else p)
                                        for p, c in fn_parts
                                    )
                                except Exception:
                                    pass
                                attachments.append(fn)
                            elif part.get_content_type() != "text/plain" and part.get_content_type() != "text/html":
                                # Inline parts with names
                                fn = part.get_param("name")
                                if fn:
                                    attachments.append(fn)

                emails.append({
                    "message_id": message_id,
                    "subject": subject,
                    "from": from_,
                    "date": date,
                    "body_preview": body_preview[:200] if body_preview else "",
                    "attachments": attachments,
                })
            except Exception:
                continue

        return emails

    except Exception as e:
        logger.error("Failed to read POP3 inbox: %s", e)
        return []
    finally:
        try:
            pop.quit()
        except Exception:
            pass
