"""
Email Sender — Multi-provider SMTP email tool with contacts, CC/BCC, templates, send log.

Usage:
  python send_email.py --to friend@example.com -s "Subject" -b "Body"
  python send_email.py --contact 张三 -s "你好" -b "好久不见"
  python send_email.py --save-contact "张三" zhangsan@qq.com
  python send_email.py --list-contacts
  python send_email.py --list-providers
  python send_email.py --to user@example.com --cc manager@example.com -s "Report" -b "Content"
  python send_email.py --template meeting -p topic=周会 -p time="下午2点"
  python send_email.py --send-log
  python send_email.py -i
"""
import os
import sys
import json
import getpass
import csv
import re
import smtplib
import argparse
import imaplib
import email as email_lib
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email import encoders
from pathlib import Path

# =============================================================================
# Email Provider Presets
# =============================================================================
PROVIDERS = {
    "163": {
        "name": "163邮箱",
        "smtp_server": "smtp.163.com",
        "smtp_port": 465,
        "use_ssl": True,
        "imap_server": "imap.163.com",
        "imap_port": 993,
        "auth_note": "需要SMTP授权码（登录 webmail → 设置 → POP3/SMTP/IMAP → 开启SMTP服务生成）",
    },
    "qq": {
        "name": "QQ邮箱",
        "smtp_server": "smtp.qq.com",
        "smtp_port": 465,
        "use_ssl": True,
        "imap_server": "imap.qq.com",
        "imap_port": 993,
        "auth_note": "需要SMTP授权码（设置 → 账户 → POP3/SMTP服务 → 生成授权码）",
    },
    "qq_ex": {
        "name": "QQ企业邮箱",
        "smtp_server": "smtp.exmail.qq.com",
        "smtp_port": 465,
        "use_ssl": True,
        "imap_server": "imap.exmail.qq.com",
        "imap_port": 993,
        "auth_note": "需要SMTP授权码",
    },
    "gmail": {
        "name": "Gmail",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "use_ssl": False,
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "auth_note": "需要Google App Password（开启两步验证后在Google账号安全设置中生成）",
    },
    "outlook": {
        "name": "Outlook / Hotmail",
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
        "use_ssl": False,
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "auth_note": "需要应用密码或OAuth2认证",
    },
    "yahoo": {
        "name": "Yahoo邮箱",
        "smtp_server": "smtp.mail.yahoo.com",
        "smtp_port": 465,
        "use_ssl": True,
        "imap_server": "imap.mail.yahoo.com",
        "imap_port": 993,
        "auth_note": "需要App Password",
    },
    "126": {
        "name": "126邮箱",
        "smtp_server": "smtp.126.com",
        "smtp_port": 465,
        "use_ssl": True,
        "imap_server": "imap.126.com",
        "imap_port": 993,
        "auth_note": "需要SMTP授权码",
    },
    "sina": {
        "name": "新浪邮箱",
        "smtp_server": "smtp.sina.com.cn",
        "smtp_port": 465,
        "use_ssl": True,
        "imap_server": "imap.sina.com.cn",
        "imap_port": 993,
        "auth_note": "需要SMTP授权码",
    },
    "aliyun": {
        "name": "阿里企业邮箱",
        "smtp_server": "smtp.qiye.aliyun.com",
        "smtp_port": 465,
        "use_ssl": True,
        "imap_server": "imap.qiye.aliyun.com",
        "imap_port": 993,
        "auth_note": "需要SMTP密码",
    },
    "foxmail": {
        "name": "Foxmail邮箱",
        "smtp_server": "smtp.foxmail.com",
        "smtp_port": 465,
        "use_ssl": True,
        "imap_server": "imap.foxmail.com",
        "imap_port": 993,
        "auth_note": "需要SMTP授权码",
    },
    "sohu": {
        "name": "搜狐邮箱",
        "smtp_server": "smtp.sohu.com",
        "smtp_port": 465,
        "use_ssl": True,
        "auth_note": "需要SMTP授权码",
    },
    "yeah": {
        "name": "Yeah.net邮箱",
        "smtp_server": "smtp.yeah.net",
        "smtp_port": 465,
        "use_ssl": True,
        "imap_server": "imap.yeah.net",
        "imap_port": 993,
        "auth_note": "需要SMTP授权码",
    },
    "zoho": {
        "name": "Zoho邮箱",
        "smtp_server": "smtp.zoho.com",
        "smtp_port": 587,
        "use_ssl": False,
        "auth_note": "需要App Password",
    },
    "aol": {
        "name": "AOL邮箱",
        "smtp_server": "smtp.aol.com",
        "smtp_port": 587,
        "use_ssl": False,
        "auth_note": "需要App Password",
    },
    "yandex": {
        "name": "Yandex邮箱",
        "smtp_server": "smtp.yandex.com",
        "smtp_port": 465,
        "use_ssl": True,
        "imap_server": "imap.yandex.com",
        "imap_port": 993,
        "auth_note": "需要App Password",
    },
    "139": {
        "name": "139邮箱（移动）",
        "smtp_server": "smtp.139.com",
        "smtp_port": 465,
        "use_ssl": True,
        "auth_note": "需要SMTP密码",
    },
    "189": {
        "name": "189邮箱（电信）",
        "smtp_server": "smtp.189.cn",
        "smtp_port": 465,
        "use_ssl": True,
        "auth_note": "需要SMTP密码",
    },
}

DEFAULT_PROVIDER = "163"

# =============================================================================
# Email Templates
# =============================================================================
TEMPLATES = {
    "greeting": {
        "description": "日常问候",
        "subject": "你好，{name}",
        "body_text": "{name}，你好！\n\n{message}\n\n祝好，\n{sender}",
        "params": {"name": "对方称呼", "message": "问候内容"},
    },
    "meeting": {
        "description": "会议通知",
        "subject": "会议邀请：{topic}",
        "body_text": "你好，\n\n主题：{topic}\n时间：{time}\n地点：{location}\n\n请准时参加。\n\n{sender}",
        "params": {"topic": "会议主题", "time": "会议时间", "location": "会议地点"},
    },
    "report": {
        "description": "报告提交",
        "subject": "{type}报告 - {date}",
        "body_text": "您好，\n\n这是{date}的{type}报告，请查收附件。\n\n{sender}",
        "params": {"type": "报告类型（周报/月报等）", "date": "日期"},
    },
    "notice": {
        "description": "正式通知",
        "subject": "通知：{title}",
        "body_text": "各位好，\n\n{message}\n\n{sender}",
        "params": {"title": "通知标题", "message": "通知内容"},
    },
    "thankyou": {
        "description": "感谢信",
        "subject": "感谢：{reason}",
        "body_text": "{name}，你好！\n\n非常感谢你的{reason}！\n\n{message}\n\n此致\n{sender}",
        "params": {"name": "对方称呼", "reason": "感谢事由", "message": "补充内容"},
    },
}

# =============================================================================
# File Paths
# =============================================================================
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / ".env"
CONTACTS_FILE = BASE_DIR / "contacts.json"
SEND_LOG_FILE = BASE_DIR / "send_log.csv"


# =============================================================================
# Config Helpers
# =============================================================================
def load_config():
    """Load email config from .env file.

    Supports two formats:

    1. Simple (backward compatible):
       EMAIL_ADDRESS=xxx
       EMAIL_PASSWORD=xxx

    2. Multi-account:
       DEFAULT_ACCOUNT=163

       [account:163]
       EMAIL_ADDRESS=xxx@163.com
       EMAIL_PASSWORD=xxx
       EMAIL_PROVIDER=163

       [account:qq]
       EMAIL_ADDRESS=xxx@qq.com
       EMAIL_PASSWORD=xxx
       EMAIL_PROVIDER=qq

    Returns:
        Simple format → flat dict  e.g. {"EMAIL_ADDRESS": "..."}
        Multi-account → dict with "_format", "_accounts", "_default_account" keys
    """
    config = {}
    if not CONFIG_FILE.exists():
        return config

    lines = CONFIG_FILE.read_text(encoding="utf-8").strip().splitlines()

    # Detect format: look for [account:xxx] headers
    has_sections = any(line.strip().startswith("[account:") for line in lines)

    if not has_sections:
        # Simple format (backward compatible)
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                config[key.strip()] = val.strip().strip("\"'")
        return config

    # Multi-account format
    current_account = None
    accounts = {}
    default_account = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Section header: [account:name]
        m = re.match(r'^\[account:(\w+)\]$', line)
        if m:
            current_account = m.group(1)
            accounts[current_account] = {}
            continue
        # Default account indicator
        if line.startswith("DEFAULT_ACCOUNT="):
            default_account = line.partition("=")[2].strip().strip("\"'")
            continue
        # key=value within a section
        if current_account and "=" in line:
            key, _, val = line.partition("=")
            accounts[current_account][key.strip()] = val.strip().strip("\"'")

    config["_format"] = "multi"
    config["_accounts"] = accounts
    config["_default_account"] = default_account or (next(iter(accounts)) if accounts else None)
    return config


def resolve_smtp_settings(config, provider_override=None):
    """Resolve SMTP server/port from config + provider presets.

    Priority:
      1. Explicit SMTP_SERVER / SMTP_PORT in .env → use directly
      2. --provider flag → load from preset
      3. EMAIL_PROVIDER in .env → load from preset
      4. Default provider
    """
    provider_key = (
        provider_override
        or config.get("EMAIL_PROVIDER")
        or DEFAULT_PROVIDER
    )
    # If SMTP_SERVER is explicitly in config, use raw values
    if "SMTP_SERVER" in config:
        return {
            "smtp_server": config["SMTP_SERVER"],
            "smtp_port": int(config.get("SMTP_PORT", 465)),
            "use_ssl": config.get("SMTP_USE_SSL", "true").lower() == "true",
            "provider_name": provider_key,
        }

    # Load from provider preset
    provider = PROVIDERS.get(provider_key)
    if not provider:
        print(f"[!] Unknown provider '{provider_key}', falling back to {DEFAULT_PROVIDER}")
        provider = PROVIDERS[DEFAULT_PROVIDER]

    return {
        "smtp_server": provider["smtp_server"],
        "smtp_port": provider["smtp_port"],
        "use_ssl": provider["use_ssl"],
        "provider_name": provider["name"],
    }


def resolve_imap_settings(config, provider_override=None):
    """Resolve IMAP server/port from provider presets."""
    provider_key = (
        provider_override
        or config.get("EMAIL_PROVIDER")
        or DEFAULT_PROVIDER
    )
    # Allow explicit IMAP override
    if "IMAP_SERVER" in config:
        return {
            "imap_server": config["IMAP_SERVER"],
            "imap_port": int(config.get("IMAP_PORT", 993)),
        }

    provider = PROVIDERS.get(provider_key)
    if not provider:
        return None

    imap_server = provider.get("imap_server")
    if not imap_server:
        return None
    return {"imap_server": imap_server, "imap_port": provider.get("imap_port", 993)}


def get_account_config(config, account_name=None):
    """Get config dict for a specific account, or the default account.

    For simple-format configs, returns the config as-is.
    For multi-account configs, resolves the named (or default) account.
    """
    if config.get("_format") != "multi":
        return config  # simple format

    accounts = config.get("_accounts", {})
    if not account_name:
        account_name = config.get("_default_account")

    account = accounts.get(account_name)
    if not account:
        available = ", ".join(accounts.keys()) if accounts else "(none)"
        print(f"[!] Account '{account_name}' not found. Available accounts: {available}")
        print(f"    Use --account NAME to select, or see --list-accounts")
        sys.exit(1)

    return account


def list_accounts():
    """Return formatted list of accounts from config."""
    config = load_config()
    if config.get("_format") != "multi":
        addr = config.get("EMAIL_ADDRESS", "(not configured)")
        prov = config.get("EMAIL_PROVIDER", "?")
        return f"Default: {addr} ({prov})  [single-account mode]"

    accounts = config.get("_accounts", {})
    default = config.get("_default_account")
    if not accounts:
        return "No accounts configured."

    lines = []
    for name in sorted(accounts):
        a = accounts[name]
        addr = a.get("EMAIL_ADDRESS", "?")
        prov = a.get("EMAIL_PROVIDER", "?")
        marker = " ← DEFAULT" if name == default else ""
        lines.append(f"  {name:<12} {addr:<35} {prov}{marker}")
    return "\n".join(lines)


# =============================================================================
# Contacts Helpers
# =============================================================================
def load_contacts():
    """Load contacts from JSON file. Returns dict of {name: email}."""
    if not CONTACTS_FILE.exists():
        return {}
    try:
        data = json.loads(CONTACTS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return {}
    except (json.JSONDecodeError, ValueError):
        return {}


def save_contacts(contacts):
    """Save contacts dict to JSON file."""
    CONTACTS_FILE.write_text(
        json.dumps(contacts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_contact(name, email):
    """Add or update a contact. Returns (success, message)."""
    if not is_valid_email(email):
        return False, f"Invalid email: {email}"
    contacts = load_contacts()
    existed = name in contacts
    contacts[name] = email
    save_contacts(contacts)
    action = "Updated" if existed else "Saved"
    return True, f"{action} contact: {name} <{email}>"


def delete_contact(name):
    """Delete a contact. Returns (success, message)."""
    contacts = load_contacts()
    if name not in contacts:
        return False, f"Contact not found: {name}"
    email = contacts.pop(name)
    save_contacts(contacts)
    return True, f"Deleted contact: {name} <{email}>"


def list_contacts():
    """Return formatted contact list string."""
    contacts = load_contacts()
    if not contacts:
        return "No contacts saved."
    lines = [f"{'Name':<20} Email", "-" * 50]
    for name in sorted(contacts):
        lines.append(f"{name:<20} {contacts[name]}")
    return "\n".join(lines)


def find_contact(query):
    """Find a contact by name (exact or partial match). Returns email or None."""
    contacts = load_contacts()
    if query in contacts:
        return contacts[query]
    # Case-insensitive partial match
    query_lower = query.lower()
    for name, email in contacts.items():
        if query_lower in name.lower():
            return email
    return None


def is_valid_email(email_str):
    """Basic email format validation."""
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email_str.strip()))


def auto_save_contact(name, email):
    """Auto-save a contact without overwriting existing alias with a different email."""
    contacts = load_contacts()
    if name in contacts:
        existing = contacts[name]
        if existing != email:
            print(f"  [i] Contact '{name}' already exists as <{existing}>, not overwriting.")
            return
    contacts[name] = email
    save_contacts(contacts)
    print(f"  [+] Auto-saved contact: {name} <{email}>")


# =============================================================================
# Send Log
# =============================================================================
def append_send_log(entry):
    """Append a send entry to CSV log."""
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
    except OSError:
        pass  # Silently skip if file is locked


def show_send_log(lines=20):
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
        result = [f"{'Time':<22} {'To':<30} {'Subject':<40} {'Status':<8}"]
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


# =============================================================================
# Provider / Template info
# =============================================================================
def list_providers():
    """Return formatted provider list."""
    lines = [f"{'Key':<12} {'Name':<20} {'SMTP Server':<30} {'Port':<8} {'IMAP':<30}", "-" * 110]
    for key in sorted(PROVIDERS):
        p = PROVIDERS[key]
        imap = p.get("imap_server", "-")
        lines.append(
            f"{key:<12} {p['name']:<20} {p['smtp_server']:<30} {p['smtp_port']:<8} {imap:<30}"
        )
    return "\n".join(lines)


def list_templates():
    """Return formatted template list."""
    lines = [f"{'Name':<15} {'Description':<20} {'Parameters':<40}", "-" * 75]
    for key in sorted(TEMPLATES):
        t = TEMPLATES[key]
        params = ", ".join(f"{k}={v}" for k, v in t["params"].items())
        lines.append(f"{key:<15} {t['description']:<20} {params:<40}")
    lines.append("")
    lines.append("Usage: --template NAME -p key=value -p key=value ...")
    return "\n".join(lines)


def apply_template(template_name, params):
    """Apply a template with given params to produce (subject, body_text)."""
    t = TEMPLATES.get(template_name)
    if not t:
        return None, None
    subject = t["subject"]
    body = t["body_text"]
    for k, v in params.items():
        placeholder = "{" + k + "}"
        subject = subject.replace(placeholder, v)
        body = body.replace(placeholder, v)
    return subject, body


# =============================================================================
# IMAP Contact Sync
# =============================================================================
IMAP_SENT_FOLDERS = {
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


def sync_contacts_from_sent(email_address, password, provider_key=None):
    """Scan IMAP sent folder for recipient addresses and add to contacts.

    Returns (success_count, message).
    """
    config = load_config()
    imap_settings = resolve_imap_settings(config, provider_key)
    if not imap_settings:
        return 0, "IMAP not available for this provider"

    # Determine sent folder name
    provider_key = provider_key or config.get("EMAIL_PROVIDER") or DEFAULT_PROVIDER
    sent_folder = IMAP_SENT_FOLDERS.get(provider_key, "已发送")

    try:
        mail = imaplib.IMAP4_SSL(
            imap_settings["imap_server"],
            imap_settings["imap_port"],
            timeout=30,
        )
        mail.login(email_address, password)

        # Try common sent folder names
        folder_candidates = [sent_folder, "Sent", "Sent Items", "[Gmail]/Sent Mail"]
        selected = None
        for folder in folder_candidates:
            try:
                status, _ = mail.select(folder)
                if status == "OK":
                    selected = folder
                    break
            except imaplib.IMAP4.error:
                continue

        if not selected:
            mail.logout()
            return 0, f"Could not find sent folder on server (tried: {', '.join(folder_candidates)})"

        # Search for emails in the last 90 days
        status, message_ids = mail.search(None, "SINCE",
            (datetime.now().replace(day=1).strftime("%d-%b-%Y")))
        if status != "OK" or not message_ids[0]:
            mail.logout()
            return 0, "No sent emails found"

        ids = message_ids[0].split()
        # Limit to last 50 to avoid timeout
        ids = ids[-50:]

        addresses = {}
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

        # Save as contacts
        contacts = load_contacts()
        added = 0
        for addr_email, name in addresses.items():
            if addr_email not in contacts.values():
                # Generate a unique name
                base_name = name
                counter = 1
                while base_name in contacts:
                    base_name = f"{name}_{counter}"
                    counter += 1
                contacts[base_name] = addr_email
                added += 1

        if added:
            save_contacts(contacts)

        return added, f"Found {len(addresses)} recipients, added {added} new contacts"

    except imaplib.IMAP4.error as e:
        return 0, f"IMAP error: {e}"
    except Exception as e:
        return 0, f"Error: {e}"


# =============================================================================
# Core Send Function
# =============================================================================
def send_email(sender, password, recipient, subject, body,
               attachments=None, cc=None, bcc=None,
               smtp_server="smtp.163.com", smtp_port=465, use_ssl=True):
    """
    Send email via SMTP.

    Args:
        sender: Sender email address
        password: SMTP password or authorization code
        recipient: Recipient email address
        subject: Email subject
        body: Email body text (can be plain text or HTML)
        attachments: Optional list of file paths
        cc: Optional list of CC recipient addresses
        bcc: Optional list of BCC recipient addresses
        smtp_server: SMTP server address
        smtp_port: SMTP server port
        use_ssl: True for SSL (port 465), False for STARTTLS (port 587)

    Returns:
        dict with success status and message
    """
    try:
        has_attachments = attachments and any(Path(f).exists() for f in attachments)
        has_cc = cc and len(cc) > 0
        has_bcc = bcc and len(bcc) > 0

        # Build the message
        if has_attachments:
            msg = MIMEMultipart("mixed")
            msg_body = MIMEMultipart("alternative")
            msg_body.attach(MIMEText(body, "plain", "utf-8"))
            msg.attach(msg_body)
        else:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "plain", "utf-8"))

        msg["From"] = sender
        msg["To"] = recipient
        if has_cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = Header(subject, "utf-8")

        # Collect all recipients for SMTP send
        all_recipients = [recipient]
        if has_cc:
            all_recipients.extend(cc)
        if has_bcc:
            all_recipients.extend(bcc)

        # Attach files
        if attachments:
            for filepath in attachments:
                path = Path(filepath)
                if not path.exists():
                    print(f"  [!] Attachment not found: {filepath}, skipping")
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
                print(f"  [+] Attached: {path.name} ({path.stat().st_size:,} bytes)")

        # Connect and send
        print(f"[*] Connecting to {smtp_server}:{smtp_port}...")
        if use_ssl:
            with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
                server.login(sender, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                server.starttls()
                server.login(sender, password)
                server.send_message(msg)

        parts = []
        if has_cc:
            parts.append(f"CC: {', '.join(cc)}")
        if attachments:
            parts.append(f"{len([a for a in attachments if Path(a).exists()])} attachment(s)")
        extra = f" ({', '.join(parts)})" if parts else ""

        return {"success": True, "message": f"Email sent to {recipient}{extra}"}

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": (
                "SMTP authentication failed. You need an authorization code (授权码), "
                "not your login password.\n\n"
                "For 163: Settings → POP3/SMTP/IMAP → Enable SMTP → Generate code\n"
                "For QQ: Settings → Account → POP3/SMTP → Generate code\n"
                "For Gmail: Enable 2FA → Generate App Password\n"
                "For others: Check the provider's SMTP documentation"
            ),
        }
    except smtplib.SMTPRecipientsRefused as e:
        return {"success": False, "message": f"Recipient refused: {recipient}", "detail": str(e)}
    except smtplib.SMTPSenderRefused as e:
        return {"success": False, "message": f"Sender refused: {sender}", "detail": str(e)}
    except smtplib.SMTPException as e:
        return {"success": False, "message": "SMTP error occurred", "detail": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {type(e).__name__}", "detail": str(e)}


# =============================================================================
# Interactive Mode
# =============================================================================
def interactive_mode():
    """Interactive setup and send mode."""
    config = load_config()

    # ── Account selection ────────────────────────────────────────────────
    if config.get("_format") == "multi":
        accounts = config.get("_accounts", {})
        default = config.get("_default_account")
        print("=== Email Sender Interactive Setup ===")
        print()
        print("Configured accounts:")
        for name in sorted(accounts):
            a = accounts[name]
            marker = " ← DEFAULT" if name == default else ""
            print(f"  {name:<12} {a.get('EMAIL_ADDRESS', '?'):<35}{marker}")
        print()
        sel = input(f"Select account [{default}]: ").strip()
        account_name = sel or default
        account = get_account_config(config, account_name)
        print(f"  Using: {account_name} → {account.get('EMAIL_ADDRESS')}")
    else:
        account = config
        account_name = "default"
        print("=== Email Sender Interactive Setup ===")
        print()

    sender = account.get("EMAIL_ADDRESS") or ""
    password = account.get("EMAIL_PASSWORD") or ""

    if not sender:
        sender = input("Your email address (e.g., jsxzznz@163.com): ").strip()
    else:
        print(f"Sender: {sender}")

    if not password:
        password = getpass.getpass("SMTP password/authorization code: ").strip()
    else:
        print("Password: [already configured]")

    # Provider selection
    provider_key = account.get("EMAIL_PROVIDER", DEFAULT_PROVIDER)
    provider = PROVIDERS.get(provider_key, PROVIDERS[DEFAULT_PROVIDER])
    print(f"Provider: {provider['name']} ({provider['smtp_server']}:{provider['smtp_port']})")
    switch = input(f"Switch provider? (Enter to keep, or type provider key like 'qq'/'gmail'): ").strip()
    if switch and switch in PROVIDERS:
        provider_key = switch
        provider = PROVIDERS[switch]
        print(f"  Switched to {provider['name']}")

    recipient = input("Recipient email: ").strip()
    subject = input("Subject: ").strip()
    print("Body (end with Ctrl+Z on Windows / Ctrl+D on Mac/Linux, or empty line with '.'):")
    body_lines = []
    while True:
        try:
            line = input()
            if line == ".":
                break
            body_lines.append(line)
        except EOFError:
            break
    body = "\n".join(body_lines)

    cc_input = input("CC (comma-separated, or Enter to skip): ").strip()
    cc_list = [a.strip() for a in cc_input.split(",") if a.strip()] if cc_input else None

    attach_input = input("Attachments (comma-separated paths, or Enter to skip): ").strip()
    attachments = [a.strip() for a in attach_input.split(",") if a.strip()] if attach_input else None

    save = input("\nSave credentials for future use? (y/N): ").strip().lower()
    if save == "y":
        smtp = resolve_smtp_settings(account, provider_key)
        if config.get("_format") == "multi":
            # Update the account in-place and re-save
            accounts = config["_accounts"]
            accounts[account_name] = {
                "EMAIL_ADDRESS": sender,
                "EMAIL_PASSWORD": password,
                "EMAIL_PROVIDER": provider_key,
            }
            lines = [f"DEFAULT_ACCOUNT={config['_default_account']}", ""]
            for name, acct in accounts.items():
                lines.append(f"[account:{name}]")
                for k, v in acct.items():
                    lines.append(f"{k}={v}")
                lines.append("")
            CONFIG_FILE.write_text("\n".join(lines), encoding="utf-8")
        else:
            content = f"""# Email Sender Configuration
EMAIL_ADDRESS={sender}
EMAIL_PASSWORD={password}
EMAIL_PROVIDER={provider_key}
SMTP_SERVER={smtp["smtp_server"]}
SMTP_PORT={smtp["smtp_port"]}
"""
            CONFIG_FILE.write_text(content, encoding="utf-8")
        print(f"[OK] Config saved to {CONFIG_FILE}")

    # Auto-save contact
    contacts = load_contacts()
    if recipient not in contacts.values():
        save_contact = input(f"Save '{recipient}' as a contact? (y/N): ").strip().lower()
        if save_contact == "y":
            name = input("Contact name: ").strip()
            if name:
                add_contact(name, recipient)

    print()
    smtp = resolve_smtp_settings(account, provider_key)
    result = send_email(sender, password, recipient, subject, body,
                        attachments=attachments, cc=cc_list,
                        smtp_server=smtp["smtp_server"],
                        smtp_port=smtp["smtp_port"],
                        use_ssl=smtp["use_ssl"])

    # Log
    append_send_log({
        "timestamp": datetime.now().isoformat(),
        "sender": sender,
        "recipient": recipient,
        "subject": subject,
        "cc": ", ".join(cc_list) if cc_list else "",
        "bcc": "",
        "attachments": str(len(attachments)) if attachments else "",
        "status": "OK" if result["success"] else "FAIL",
    })

    print(f"[{'OK' if result['success'] else 'FAIL'}] {result['message']}")
    if not result["success"] and "detail" in result:
        print(f"  Detail: {result['detail']}")


# =============================================================================
# CLI Entry Point
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Multi-provider SMTP email sender with contacts, templates, CC/BCC",
        epilog="Examples:\n"
               "  %(prog)s --to user@example.com -s 'Hello' -b 'Body'\n"
               "  %(prog)s --contact 张三 -s '你好' -b '好久不见'\n"
               "  %(prog)s --template meeting -p topic=周会 -p time='下午2点'\n"
               "  %(prog)s --to user@qq.com --cc manager@163.com -s '报告' -b '内容'\n"
               "  %(prog)s --save-contact '张三' zhangsan@qq.com\n"
               "  %(prog)s --list-contacts\n"
               "  %(prog)s --list-providers\n"
               "  %(prog)s -i",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Recipient
    parser.add_argument("recipient", nargs="?", help="Recipient email address (positional)")
    parser.add_argument("--to", help="Recipient email address (alternative)")
    parser.add_argument("--contact", help="Send to a saved contact by name")
    parser.add_argument("--cc", action="append", help="Carbon copy recipient (can be used multiple times)")
    parser.add_argument("--bcc", action="append", help="Blind carbon copy recipient (can be used multiple times)")

    # Email content
    parser.add_argument("--subject", "-s", help="Email subject")
    parser.add_argument("--body", "-b", help="Email body content (plain text)")
    parser.add_argument("--html", help="Email body content (HTML)")
    parser.add_argument("--body-file", "-f", help="Read body from file")
    parser.add_argument("--template", choices=list(TEMPLATES.keys()),
                        help="Use a predefined email template")
    parser.add_argument("--param", "-p", action="append", dest="template_params",
                        help="Template parameter in key=value format (can be used multiple times)")

    # Sender options
    parser.add_argument("--from", dest="sender", help="Sender email (override config)")
    parser.add_argument("--account", help="Account name from .env to use (see --list-accounts)")
    parser.add_argument("--provider", choices=list(PROVIDERS.keys()),
                        help="Email provider preset (overrides config)")

    # Contact management
    parser.add_argument("--save-contact", nargs=2, metavar=("NAME", "EMAIL"),
                        help="Save a contact")
    parser.add_argument("--delete-contact", metavar="NAME", help="Delete a contact")
    parser.add_argument("--list-contacts", action="store_true", help="List all saved contacts")
    parser.add_argument("--auto-save-contact", nargs=2, metavar=("NAME", "EMAIL"),
                        help="Automatically save contact (without overwrite warning)")

    # Contact sync
    parser.add_argument("--sync-contacts", action="store_true",
                        help="Scan IMAP sent folder to build contacts (experimental)")

    # Attachments
    parser.add_argument("--attach", "-a", action="append", dest="attachments",
                        help="Attach file(s) to the email (can be used multiple times)")

    # Other
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive setup mode")
    parser.add_argument("--save-config", action="store_true", help="Save credentials to .env")

    parser.add_argument("--list-accounts", action="store_true",
                        help="List all configured email accounts from .env")
    parser.add_argument("--list-providers", action="store_true",
                        help="List all supported email providers")
    parser.add_argument("--list-templates", action="store_true",
                        help="List all predefined email templates")
    parser.add_argument("--send-log", action="store_true", help="Show recent send history")
    parser.add_argument("--send-log-lines", type=int, default=20,
                        help="Number of log entries to show (default: 20)")

    args = parser.parse_args()

    # ── Information-only commands ──────────────────────────────────────────
    if args.list_accounts:
        print(list_accounts())
        return
    if args.list_providers:
        print(list_providers())
        return
    if args.list_templates:
        print(list_templates())
        return
    if args.list_contacts:
        print(list_contacts())
        return
    if args.send_log:
        print(show_send_log(args.send_log_lines))
        return

    # ── Contact management commands ────────────────────────────────────────
    if args.save_contact:
        name, email = args.save_contact
        ok, msg = add_contact(name, email)
        print(f"[{'OK' if ok else '!'}] {msg}")
        return

    if args.delete_contact:
        ok, msg = delete_contact(args.delete_contact)
        print(f"[{'OK' if ok else '!'}] {msg}")
        return

    if args.auto_save_contact:
        name, email = args.auto_save_contact
        auto_save_contact(name, email)
        return

    # ── IMAP Contact Sync ────────────────────────────────────────────────
    if args.sync_contacts:
        config = load_config()
        account = get_account_config(config, args.account)
        sender = args.sender or account.get("EMAIL_ADDRESS")
        password = account.get("EMAIL_PASSWORD")
        provider_override = args.provider or account.get("EMAIL_PROVIDER")
        if not sender or not password:
            print("[!] Credentials required for IMAP sync. Configure .env first.")
            sys.exit(1)
        print(f"[*] Scanning sent folder for {sender}...")
        count, msg = sync_contacts_from_sent(sender, password, provider_override)
        print(f"[{'OK' if count else 'i'}] {msg}")
        return

    # ── Interactive mode ─────────────────────────────────────────────────
    if args.interactive or (len(sys.argv) == 1):
        interactive_mode()
        return

    # ── Send email ────────────────────────────────────────────────────────
    config = load_config()

    # Resolve account → sender credentials
    account = get_account_config(config, args.account)
    sender = args.sender or account.get("EMAIL_ADDRESS") or os.environ.get("EMAIL_ADDRESS")
    password = account.get("EMAIL_PASSWORD") or os.environ.get("EMAIL_PASSWORD")
    provider_override = args.provider or account.get("EMAIL_PROVIDER")

    if not sender or not password:
        print("[!] No credentials configured. Run with --interactive to set up.")
        sys.exit(1)

    # Resolve SMTP settings
    smtp = resolve_smtp_settings(account, provider_override)

    # Resolve recipient
    if args.contact:
        email = find_contact(args.contact)
        if not email:
            print(f"[!] Contact '{args.contact}' not found. Use --list-contacts to see saved contacts.")
            print(f"    Add with: --save-contact \"{args.contact}\" their@email.com")
            sys.exit(1)
        recipient = email
    else:
        recipient = args.recipient or args.to

    if not recipient:
        print("[!] Recipient is required. Use --to EMAIL, --contact NAME, or pass positional.")
        sys.exit(1)

    # Resolve subject and body (with template support)
    subject = args.subject
    body = args.body

    # Apply template if specified
    if args.template:
        params = {}
        if args.template_params:
            for p in args.template_params:
                if "=" in p:
                    k, _, v = p.partition("=")
                    params[k.strip()] = v.strip()
        # Add sender as available param
        params.setdefault("sender", sender)
        t_subject, t_body = apply_template(args.template, params)
        if t_subject is None:
            print(f"[!] Unknown template: {args.template}")
            sys.exit(1)
        subject = subject or t_subject
        body = body or t_body

    if not subject:
        subject = "(No subject)"

    # Use HTML body if provided
    if args.html:
        body = args.html

    # Read body from file if specified
    if args.body_file:
        try:
            body = Path(args.body_file).read_text(encoding="utf-8")
        except Exception as e:
            print(f"[!] Failed to read body file: {e}")
            sys.exit(1)

    if not body:
        body = ""

    # CC/BCC
    cc_list = args.cc or None
    bcc_list = args.bcc or None

    # Send
    result = send_email(
        sender, password, recipient, subject, body,
        attachments=args.attachments,
        cc=cc_list,
        bcc=bcc_list,
        smtp_server=smtp["smtp_server"],
        smtp_port=smtp["smtp_port"],
        use_ssl=smtp["use_ssl"],
    )

    # Log
    append_send_log({
        "timestamp": datetime.now().isoformat(),
        "sender": sender,
        "recipient": recipient,
        "subject": subject,
        "cc": ", ".join(cc_list) if cc_list else "",
        "bcc": ", ".join(bcc_list) if bcc_list else "",
        "attachments": str(len(args.attachments)) if args.attachments else "",
        "status": "OK" if result["success"] else "FAIL",
    })

    # Auto-save contact (if enabled via env var)
    if os.environ.get("EMAIL_AUTO_SAVE_CONTACT", "").lower() in ("1", "true", "yes"):
        if is_valid_email(recipient):
            name_hint = recipient.split("@")[0]
            auto_save_contact(name_hint, recipient)

    print(f"[{'OK' if result['success'] else 'FAIL'}] {result['message']}")
    if not result["success"] and "detail" in result:
        print(f"  Detail: {result['detail']}")
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
