"""Type definitions for the email sender package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProviderInfo:
    """SMTP/IMAP/POP3 provider preset."""
    name: str
    smtp_server: str
    smtp_port: int
    use_ssl: bool
    imap_server: Optional[str] = None
    imap_port: int = 993
    pop3_server: Optional[str] = None
    pop3_port: int = 995
    auth_note: str = ""


@dataclass
class SmtpSettings:
    """Resolved SMTP connection settings."""
    smtp_server: str
    smtp_port: int
    use_ssl: bool
    provider_name: str


@dataclass
class ImapSettings:
    """Resolved IMAP connection settings."""
    imap_server: str
    imap_port: int


@dataclass
class Pop3Settings:
    """Resolved POP3 connection settings."""
    pop3_server: str
    pop3_port: int


@dataclass
class EmailConfig:
    """Validated email configuration."""
    email_address: str
    email_password: str
    email_provider: str = "163"
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_use_ssl: Optional[bool] = None
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None


@dataclass
class SendRequest:
    """Request payload for sending an email."""
    sender: str
    password: str
    recipient: str
    subject: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    attachments: Optional[list[str]] = None
    cc: Optional[list[str]] = None
    bcc: Optional[list[str]] = None
    smtp_server: str = "smtp.163.com"
    smtp_port: int = 465
    use_ssl: bool = True
    in_reply_to: Optional[str] = None
    references: Optional[list[str]] = None


@dataclass
class SendResult:
    """Result of a send attempt."""
    success: bool
    message: str
    detail: Optional[str] = None
    recipient: Optional[str] = None
    message_id: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {"success": self.success, "message": self.message}
        if self.detail:
            d["detail"] = self.detail
        if self.recipient:
            d["recipient"] = self.recipient
        if self.message_id:
            d["message_id"] = self.message_id
        return d


@dataclass
class BatchResult:
    """Result of a batch send operation."""
    results: list[SendResult] = field(default_factory=list)
    total: int = 0
    succeeded: int = 0
    failed: int = 0

    @property
    def all_succeeded(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict:
        return {
            "success": self.all_succeeded,
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
        }
