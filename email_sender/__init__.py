"""Email Sender — Multi-provider SMTP CLI tool for AGENT use."""

from email_sender.types import SendRequest, SendResult, EmailConfig, ProviderInfo
from email_sender.config import (
    load_config,
    resolve_smtp_settings,
    resolve_imap_settings,
    resolve_pop3_settings,
    get_account_config,
    list_accounts,
    list_providers,
    validate_config,
    get_password,
    set_password,
    HAS_KEYRING,
    PROVIDERS,
)
from email_sender.contacts import (
    load_contacts,
    save_contacts,
    add_contact,
    delete_contact,
    list_contacts,
    find_contact,
    auto_save_contact,
)
from email_sender.templates import TEMPLATES, apply_template, list_templates
from email_sender.smtp_client import send_email, send_batch
from email_sender.imap_client import sync_contacts_from_sent, read_inbox, read_inbox_pop3, download_attachments
from email_sender.log import append_send_log, show_send_log
from email_sender.utils import is_valid_email, validate_attachment

__all__ = [
    "SendRequest", "SendResult", "EmailConfig", "ProviderInfo",
    "load_config", "resolve_smtp_settings", "resolve_imap_settings", "resolve_pop3_settings",
    "get_account_config", "list_accounts", "list_providers", "validate_config",
    "get_password", "set_password", "HAS_KEYRING", "PROVIDERS",
    "load_contacts", "save_contacts", "add_contact", "delete_contact",
    "list_contacts", "find_contact", "auto_save_contact",
    "TEMPLATES", "apply_template", "list_templates",
    "send_email", "send_batch",
    "sync_contacts_from_sent", "read_inbox", "read_inbox_pop3", "download_attachments",
    "append_send_log", "show_send_log",
    "is_valid_email", "validate_attachment",
]
