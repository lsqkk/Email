"""Configuration loading and provider presets."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

from email_sender.types import ProviderInfo, SmtpSettings, ImapSettings, EmailConfig

# =============================================================================
# File Paths
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / ".env"

# =============================================================================
# Email Provider Presets
# =============================================================================
PROVIDERS: dict[str, ProviderInfo] = {
    "163": ProviderInfo(
        name="163邮箱", smtp_server="smtp.163.com", smtp_port=465, use_ssl=True,
        imap_server="imap.163.com", imap_port=993,
        auth_note="需要SMTP授权码（登录 webmail → 设置 → POP3/SMTP/IMAP → 开启SMTP服务生成）",
    ),
    "qq": ProviderInfo(
        name="QQ邮箱", smtp_server="smtp.qq.com", smtp_port=465, use_ssl=True,
        imap_server="imap.qq.com", imap_port=993,
        auth_note="需要SMTP授权码（设置 → 账户 → POP3/SMTP服务 → 生成授权码）",
    ),
    "qq_ex": ProviderInfo(
        name="QQ企业邮箱", smtp_server="smtp.exmail.qq.com", smtp_port=465, use_ssl=True,
        imap_server="imap.exmail.qq.com", imap_port=993,
        auth_note="需要SMTP授权码",
    ),
    "gmail": ProviderInfo(
        name="Gmail", smtp_server="smtp.gmail.com", smtp_port=587, use_ssl=False,
        imap_server="imap.gmail.com", imap_port=993,
        auth_note="需要Google App Password（开启两步验证后在Google账号安全设置中生成）",
    ),
    "outlook": ProviderInfo(
        name="Outlook / Hotmail", smtp_server="smtp.office365.com", smtp_port=587, use_ssl=False,
        imap_server="outlook.office365.com", imap_port=993,
        auth_note="需要应用密码或OAuth2认证",
    ),
    "yahoo": ProviderInfo(
        name="Yahoo邮箱", smtp_server="smtp.mail.yahoo.com", smtp_port=465, use_ssl=True,
        imap_server="imap.mail.yahoo.com", imap_port=993,
        auth_note="需要App Password",
    ),
    "126": ProviderInfo(
        name="126邮箱", smtp_server="smtp.126.com", smtp_port=465, use_ssl=True,
        imap_server="imap.126.com", imap_port=993,
        auth_note="需要SMTP授权码",
    ),
    "sina": ProviderInfo(
        name="新浪邮箱", smtp_server="smtp.sina.com.cn", smtp_port=465, use_ssl=True,
        imap_server="imap.sina.com.cn", imap_port=993,
        auth_note="需要SMTP授权码",
    ),
    "aliyun": ProviderInfo(
        name="阿里企业邮箱", smtp_server="smtp.qiye.aliyun.com", smtp_port=465, use_ssl=True,
        imap_server="imap.qiye.aliyun.com", imap_port=993,
        auth_note="需要SMTP密码",
    ),
    "foxmail": ProviderInfo(
        name="Foxmail邮箱", smtp_server="smtp.foxmail.com", smtp_port=465, use_ssl=True,
        imap_server="imap.foxmail.com", imap_port=993,
        auth_note="需要SMTP授权码",
    ),
    "sohu": ProviderInfo(
        name="搜狐邮箱", smtp_server="smtp.sohu.com", smtp_port=465, use_ssl=True,
        imap_server=None, imap_port=993,
        auth_note="需要SMTP授权码",
    ),
    "yeah": ProviderInfo(
        name="Yeah.net邮箱", smtp_server="smtp.yeah.net", smtp_port=465, use_ssl=True,
        imap_server="imap.yeah.net", imap_port=993,
        auth_note="需要SMTP授权码",
    ),
    "zoho": ProviderInfo(
        name="Zoho邮箱", smtp_server="smtp.zoho.com", smtp_port=587, use_ssl=False,
        imap_server=None, imap_port=993,
        auth_note="需要App Password",
    ),
    "aol": ProviderInfo(
        name="AOL邮箱", smtp_server="smtp.aol.com", smtp_port=587, use_ssl=False,
        imap_server=None, imap_port=993,
        auth_note="需要App Password",
    ),
    "yandex": ProviderInfo(
        name="Yandex邮箱", smtp_server="smtp.yandex.com", smtp_port=465, use_ssl=True,
        imap_server="imap.yandex.com", imap_port=993,
        auth_note="需要App Password",
    ),
    "139": ProviderInfo(
        name="139邮箱（移动）", smtp_server="smtp.139.com", smtp_port=465, use_ssl=True,
        imap_server=None, imap_port=993,
        auth_note="需要SMTP密码",
    ),
    "189": ProviderInfo(
        name="189邮箱（电信）", smtp_server="smtp.189.cn", smtp_port=465, use_ssl=True,
        imap_server=None, imap_port=993,
        auth_note="需要SMTP密码",
    ),
}

DEFAULT_PROVIDER = "163"


# =============================================================================
# Config Loading
# =============================================================================

def load_config() -> dict[str, Any]:
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

    Returns:
        Simple format → flat dict
        Multi-account → dict with "_format", "_accounts", "_default_account" keys
    """
    config: dict[str, Any] = {}
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
    current_account: Optional[str] = None
    accounts: dict[str, dict[str, str]] = {}
    default_account: Optional[str] = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^\[account:(\w+)\]$', line)
        if m:
            current_account = m.group(1)
            accounts[current_account] = {}
            continue
        if line.startswith("DEFAULT_ACCOUNT="):
            default_account = line.partition("=")[2].strip().strip("\"'")
            continue
        if current_account and "=" in line:
            key, _, val = line.partition("=")
            accounts[current_account][key.strip()] = val.strip().strip("\"'")

    config["_format"] = "multi"
    config["_accounts"] = accounts
    config["_default_account"] = default_account or (next(iter(accounts)) if accounts else None)
    return config


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate config has required fields. Returns list of error messages (empty = valid)."""
    errors: list[str] = []

    # Handle multi-account format: try to get a representative account
    if config.get("_format") == "multi":
        accounts = config.get("_accounts", {})
        default = config.get("_default_account")
        if not accounts:
            errors.append("No accounts configured in .env")
        elif default and default not in accounts:
            errors.append(f"Default account '{default}' not found in configured accounts")
        # No need to check per-account fields here; get_account_config does that
        return errors

    # Simple format
    if not config:
        errors.append(f"Configuration file not found or empty: {CONFIG_FILE}")
        return errors

    if "EMAIL_ADDRESS" not in config:
        errors.append("EMAIL_ADDRESS is not set in .env")
    if "EMAIL_PASSWORD" not in config:
        errors.append("EMAIL_PASSWORD is not set in .env")

    return errors


def resolve_smtp_settings(
    config: dict[str, Any],
    provider_override: Optional[str] = None,
) -> SmtpSettings:
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

    if "SMTP_SERVER" in config:
        return SmtpSettings(
            smtp_server=config["SMTP_SERVER"],
            smtp_port=int(config.get("SMTP_PORT", 465)),
            use_ssl=config.get("SMTP_USE_SSL", "true").lower() == "true",
            provider_name=provider_key,
        )

    provider = PROVIDERS.get(provider_key)
    if not provider:
        provider = PROVIDERS[DEFAULT_PROVIDER]

    return SmtpSettings(
        smtp_server=provider.smtp_server,
        smtp_port=provider.smtp_port,
        use_ssl=provider.use_ssl,
        provider_name=provider.name,
    )


def resolve_imap_settings(
    config: dict[str, Any],
    provider_override: Optional[str] = None,
) -> Optional[ImapSettings]:
    """Resolve IMAP server/port from provider presets."""
    provider_key = (
        provider_override
        or config.get("EMAIL_PROVIDER")
        or DEFAULT_PROVIDER
    )

    if "IMAP_SERVER" in config:
        return ImapSettings(
            imap_server=config["IMAP_SERVER"],
            imap_port=int(config.get("IMAP_PORT", 993)),
        )

    provider = PROVIDERS.get(provider_key)
    if not provider:
        return None

    if not provider.imap_server:
        return None

    return ImapSettings(imap_server=provider.imap_server, imap_port=provider.imap_port)


def get_account_config(
    config: dict[str, Any],
    account_name: Optional[str] = None,
) -> dict[str, Any]:
    """Get config dict for a specific account, or the default account.

    For simple-format configs, returns the config as-is.
    For multi-account configs, resolves the named (or default) account.
    """
    if config.get("_format") != "multi":
        return config

    accounts = config.get("_accounts", {})
    if not account_name:
        account_name = config.get("_default_account")

    account = accounts.get(account_name) if account_name else None
    if not account:
        available = ", ".join(accounts.keys()) if accounts else "(none)"
        msg = f"Account '{account_name}' not found. Available accounts: {available}"
        msg += f"\n    Use --account NAME to select, or see --list-accounts"
        print(f"[!] {msg}")
        sys.exit(1)

    return account


def list_accounts() -> str:
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

    lines: list[str] = []
    for name in sorted(accounts):
        a = accounts[name]
        addr = a.get("EMAIL_ADDRESS", "?")
        prov = a.get("EMAIL_PROVIDER", "?")
        marker = " ← DEFAULT" if name == default else ""
        lines.append(f"  {name:<12} {addr:<35} {prov}{marker}")
    return "\n".join(lines)


def list_providers() -> str:
    """Return formatted provider list."""
    lines: list[str] = [
        f"{'Key':<12} {'Name':<20} {'SMTP Server':<30} {'Port':<8} {'IMAP':<30}",
        "-" * 110,
    ]
    for key in sorted(PROVIDERS):
        p = PROVIDERS[key]
        imap = p.imap_server or "-"
        lines.append(
            f"{key:<12} {p.name:<20} {p.smtp_server:<30} {p.smtp_port:<8} {imap:<30}"
        )
    return "\n".join(lines)
