"""SMTP email client — send, batch, HTML+text dual rendering, retry, attachment validation."""

from __future__ import annotations

import logging
import smtplib
import time
import uuid
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from email_sender.types import SendResult, BatchResult, SendRequest
from email_sender.utils import validate_attachments, html_to_plain_text, format_bytes

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_DELAYS = [1, 3]  # seconds between retries
DEFAULT_MAX_ATTACHMENT_MB = 25


def _build_message(
    request: SendRequest,
) -> tuple[MIMEMultipart, list[str]]:
    """Build a MIME message from a SendRequest.

    Returns (message, all_recipients_list).
    """
    has_attachments = bool(request.attachments and any(Path(f).exists() for f in request.attachments))
    has_cc = bool(request.cc)
    has_bcc = bool(request.bcc)

    body_text = request.body_text or ""
    body_html = request.body_html

    # Determine if we need multipart/alternative
    use_html = bool(body_html)
    use_dual = use_html and body_text

    # Build message structure
    if has_attachments:
        msg: MIMEMultipart = MIMEMultipart("mixed")
        if use_dual:
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(body_text, "plain", "utf-8"))
            alt.attach(MIMEText(body_html or "", "html", "utf-8"))
            msg.attach(alt)
        elif use_html:
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(html_to_plain_text(body_html), "plain", "utf-8"))
            alt.attach(MIMEText(body_html, "html", "utf-8"))
            msg.attach(alt)
        else:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
    else:
        if use_dual:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))
        elif use_html:
            msg = MIMEMultipart("alternative")
            plain = html_to_plain_text(body_html)
            msg.attach(MIMEText(plain, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))
        else:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body_text, "plain", "utf-8"))

    msg["From"] = request.sender
    msg["To"] = request.recipient
    if has_cc and request.cc:
        msg["Cc"] = ", ".join(request.cc)
    msg["Subject"] = Header(request.subject, "utf-8")

    # Message-ID for threading
    message_id = f"<{uuid.uuid4().hex}@{request.sender.split('@')[-1]}>"
    msg["Message-ID"] = message_id

    if request.in_reply_to:
        msg["In-Reply-To"] = request.in_reply_to
    if request.references:
        msg["References"] = " ".join(request.references)
    elif request.in_reply_to:
        msg["References"] = request.in_reply_to

    # Collect all recipients for SMTP send
    all_recipients = [request.recipient]
    if has_cc and request.cc:
        all_recipients.extend(request.cc)
    if has_bcc and request.bcc:
        all_recipients.extend(request.bcc)

    # Attach files
    if request.attachments:
        for filepath in request.attachments:
            path = Path(filepath)
            if not path.exists():
                logger.warning("Attachment not found: %s, skipping", filepath)
                continue
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=Header(path.name, "utf-8").encode(),
            )
            msg.attach(part)
            size_str = format_bytes(path.stat().st_size)
            logger.info("Attached: %s (%s)", path.name, size_str)

    return msg, all_recipients


def _send_with_retry(
    request: SendRequest,
    msg: MIMEMultipart,
    all_recipients: list[str],
) -> SendResult:
    """Send with retry logic. Returns SendResult."""
    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        if attempt > 0:
            delay = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
            logger.info("Retry %d/%d after %ds...", attempt, MAX_RETRIES, delay)
            time.sleep(delay)

        try:
            smtp_server = request.smtp_server
            smtp_port = request.smtp_port
            use_ssl = request.use_ssl

            logger.info(
                "Connecting to %s:%s (SSL=%s) attempt %d/%d",
                smtp_server, smtp_port, use_ssl, attempt + 1, MAX_RETRIES + 1,
            )

            if use_ssl:
                with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
                    server.login(request.sender, request.password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                    server.starttls()
                    server.login(request.sender, request.password)
                    server.send_message(msg)

            parts: list[str] = []
            if request.cc:
                parts.append(f"CC: {', '.join(request.cc)}")
            if request.attachments:
                valid_count = len([a for a in request.attachments if Path(a).exists()])
                if valid_count:
                    parts.append(f"{valid_count} attachment(s)")
            extra = f" ({', '.join(parts)})" if parts else ""

            return SendResult(
                success=True,
                message=f"Email sent to {request.recipient}{extra}",
                recipient=request.recipient,
                message_id=msg["Message-ID"],
            )

        except smtplib.SMTPAuthenticationError as e:
            return SendResult(
                success=False,
                message=(
                    "SMTP authentication failed. You need an authorization code (授权码), "
                    "not your login password.\n\n"
                    "For 163: Settings → POP3/SMTP/IMAP → Enable SMTP → Generate code\n"
                    "For QQ: Settings → Account → POP3/SMTP → Generate code\n"
                    "For Gmail: Enable 2FA → Generate App Password\n"
                    "For others: Check the provider's SMTP documentation"
                ),
                detail=str(e),
                recipient=request.recipient,
            )
        except smtplib.SMTPRecipientsRefused as e:
            return SendResult(
                success=False,
                message=f"Recipient refused: {request.recipient}",
                detail=str(e),
                recipient=request.recipient,
            )
        except smtplib.SMTPSenderRefused as e:
            return SendResult(
                success=False,
                message=f"Sender refused: {request.sender}",
                detail=str(e),
                recipient=request.recipient,
            )
        except (smtplib.SMTPException, TimeoutError, OSError) as e:
            last_error = e
            logger.warning("Attempt %d failed: %s", attempt + 1, e)
            continue

    # All retries exhausted
    return SendResult(
        success=False,
        message=f"Failed after {MAX_RETRIES + 1} attempts",
        detail=str(last_error) if last_error else None,
        recipient=request.recipient,
    )


def send_email(
    sender: str,
    password: str,
    recipient: str,
    subject: str,
    body: Optional[str] = None,
    attachments: Optional[list[str]] = None,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
    smtp_server: str = "smtp.163.com",
    smtp_port: int = 465,
    use_ssl: bool = True,
    body_html: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[list[str]] = None,
    max_attachment_mb: int = DEFAULT_MAX_ATTACHMENT_MB,
) -> SendResult:
    """Send an email via SMTP.

    This is the main public API. All parameters are also available via SendRequest.

    Supports:
    - Plain text and/or HTML body (dual rendering)
    - File attachments with size validation
    - CC/BCC
    - Reply/forward threading (In-Reply-To, References)
    - Automatic retry on transient failures
    - Message-ID generation
    """
    # Validate attachments before sending
    if attachments:
        max_bytes = max_attachment_mb * 1024 * 1024
        ok, errors = validate_attachments(attachments, max_bytes)
        if not ok:
            return SendResult(
                success=False,
                message="Attachment validation failed",
                detail="\n".join(errors),
                recipient=recipient,
            )

    request = SendRequest(
        sender=sender,
        password=password,
        recipient=recipient,
        subject=subject,
        body_text=body,
        body_html=body_html,
        attachments=attachments,
        cc=cc,
        bcc=bcc,
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        use_ssl=use_ssl,
        in_reply_to=in_reply_to,
        references=references,
    )

    msg, all_recipients = _build_message(request)
    return _send_with_retry(request, msg, all_recipients)


def send_batch(
    sender: str,
    password: str,
    recipients: list[str],
    subject: str,
    body: Optional[str] = None,
    body_html: Optional[str] = None,
    subject_template: Optional[str] = None,
    body_template: Optional[str] = None,
    personalizations: Optional[dict[str, dict[str, str]]] = None,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
    attachments: Optional[list[str]] = None,
    smtp_server: str = "smtp.163.com",
    smtp_port: int = 465,
    use_ssl: bool = True,
    max_attachment_mb: int = DEFAULT_MAX_ATTACHMENT_MB,
    throttle: float = 0.5,
) -> BatchResult:
    """Send an email to multiple recipients (batch/mail merge).

    Args:
        sender: Sender email address
        password: SMTP password/authorization code
        recipients: List of recipient email addresses
        subject: Default subject (used if subject_template is None)
        body: Default plain text body
        body_html: Default HTML body
        subject_template: Template string with {email} and {name} placeholders
        body_template: Body template string with {email} and {name} placeholders
        personalizations: Per-recipient overrides, keyed by email:
            {"user@example.com": {"name": "User", "subject": "Hello {name}", "body": "Hi {name}"}}
        cc: CC recipients for ALL emails
        bcc: BCC recipients for ALL emails
        attachments: Attachments for ALL emails
        smtp_server, smtp_port, use_ssl: SMTP connection settings
        max_attachment_mb: Max attachment size per file
        throttle: Seconds to wait between sends

    Returns BatchResult with per-recipient results.
    """
    result = BatchResult(total=len(recipients))

    for i, recipient_email in enumerate(recipients):
        # Resolve personalization
        recip_name = recipient_email.split("@")[0]
        personal = (personalizations or {}).get(recipient_email, {})

        # Resolve subject
        if subject_template:
            subj = subject_template.replace("{email}", recipient_email).replace("{name}", recip_name)
            if "subject" in personal:
                subj = personal["subject"].replace("{email}", recipient_email).replace("{name}", recip_name)
        else:
            subj = subject

        # Resolve body
        txt_body = body
        html_body = body_html
        if body_template:
            txt_body = body_template.replace("{email}", recipient_email).replace("{name}", recip_name)
            if "body" in personal:
                txt_body = personal["body"].replace("{email}", recipient_email).replace("{name}", recip_name)

        if "name" in personal:
            recip_name = personal["name"]

        # Override with per-recipient if provided
        final_subject = personal.get("subject", subj)
        final_body = personal.get("body", txt_body)
        final_html = personal.get("body_html", html_body)

        r = send_email(
            sender=sender,
            password=password,
            recipient=recipient_email,
            subject=final_subject,
            body=final_body,
            body_html=final_html,
            attachments=attachments,
            cc=cc,
            bcc=bcc,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            use_ssl=use_ssl,
            max_attachment_mb=max_attachment_mb,
        )
        result.results.append(r)
        if r.success:
            result.succeeded += 1
        else:
            result.failed += 1

        # Throttle between sends (except last)
        if throttle > 0 and i < len(recipients) - 1:
            time.sleep(throttle)

    return result
