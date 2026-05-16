#!/usr/bin/env python3
"""
Email Sender — Multi-provider SMTP CLI tool for AGENT use.

Usage:
  python send_email.py --to friend@example.com -s "Subject" -b "Body"
  python send_email.py --contact 张三 -s "你好" -b "好久不见"
  python send_email.py --template meeting -p topic=周会 -p time="下午2点"
  python send_email.py --to-list recipients.txt -s "批量通知" -b "正文"
  python send_email.py --read-inbox 5
  python send_email.py --json --to user@example.com -s "Hi" -b "Hello"

See --help for full reference.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from email_sender import (
    PROVIDERS, TEMPLATES,
    load_config, validate_config, get_account_config,
    resolve_smtp_settings, resolve_imap_settings, resolve_pop3_settings,
    list_accounts, list_providers, list_templates,
    add_contact, delete_contact, list_contacts, find_contact, auto_save_contact,
    apply_template,
    send_email, send_batch,
    sync_contacts_from_sent, read_inbox, read_inbox_pop3,
    append_send_log, show_send_log,
    is_valid_email, validate_attachment, get_password,
)

# =============================================================================
# Logging setup
# =============================================================================

_LOG_FORMAT = "%(levelname).1s %(message)s"


def _setup_logging(quiet: bool = False, verbose: bool = False) -> None:
    """Configure logging based on verbosity flags.

    quiet=True  → only WARNING and above
    verbose=True → DEBUG and above (implies not quiet)
    default     → INFO and above
    """
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(format=_LOG_FORMAT, level=level, stream=sys.stderr)


def _json_exit(data: dict, exit_code: int = 0) -> None:
    """Print JSON output and exit."""
    import json
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


# =============================================================================
# Argument parser
# =============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Multi-provider SMTP email sender — CLI tool for AGENT use",
        epilog="Examples:\n"
               "  %(prog)s --to user@example.com -s 'Hello' -b 'Body'\n"
               "  %(prog)s --contact 张三 -s '你好' -b '好久不见'\n"
               "  %(prog)s --template meeting -p topic=周会 -p time='下午2点'\n"
               "  %(prog)s --to-list users.txt -s '批量通知' --html '<h1>Hi</h1>'\n"
               "  %(prog)s --read-inbox 5 --json\n"
               "  %(prog)s --json --dry-run --to test@test.com -s 'Test' -b 'Body'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ── Output options ──────────────────────────────────────────────────
    output = parser.add_argument_group("Output")
    output.add_argument("--json", action="store_true",
                        help="Output results as JSON (machine-parseable)")
    output.add_argument("--dry-run", action="store_true",
                        help="Validate but do not send")
    output.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress informational output")
    output.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose debug output")

    # ── Recipient ────────────────────────────────────────────────────────
    recip = parser.add_argument_group("Recipient")
    recip.add_argument("recipient", nargs="?", help="Recipient email address (positional)")
    recip.add_argument("--to", help="Recipient email address (alternative)")
    recip.add_argument("--to-list", help="File with recipient emails (one per line) for batch send")
    recip.add_argument("--contact", help="Send to a saved contact by name")
    recip.add_argument("--contact-exact", action="store_true",
                       help="Require exact contact name match")
    recip.add_argument("--cc", action="append", help="Carbon copy (can be used multiple times)")
    recip.add_argument("--bcc", action="append", help="Blind carbon copy (can be used multiple times)")

    # ── Email content ────────────────────────────────────────────────────
    content = parser.add_argument_group("Email Content")
    content.add_argument("--subject", "-s", help="Email subject")
    content.add_argument("--body", "-b", help="Email body content (plain text)")
    content.add_argument("--html", help="Email body content (HTML)")
    content.add_argument("--body-file", "-f", help="Read body from file")
    content.add_argument("--template", choices=list(TEMPLATES.keys()),
                         help="Use a predefined email template")
    content.add_argument("--param", "-p", action="append", dest="template_params",
                         help="Template parameter in key=value format")

    # ── Threading ────────────────────────────────────────────────────────
    thread = parser.add_argument_group("Threading")
    thread.add_argument("--reply", help="Message-ID to reply to (sets In-Reply-To header)")

    # ── Sender options ───────────────────────────────────────────────────
    sender_grp = parser.add_argument_group("Sender Options")
    sender_grp.add_argument("--from", dest="sender", help="Sender email (override config)")
    sender_grp.add_argument("--account", help="Account name from .env (see --list-accounts)")
    sender_grp.add_argument("--provider", choices=list(PROVIDERS.keys()),
                            help="Email provider preset (overrides config)")

    # ── Attachments ──────────────────────────────────────────────────────
    attach = parser.add_argument_group("Attachments")
    attach.add_argument("--attach", "-a", action="append", dest="attachments",
                        help="Attach file(s) (can be used multiple times)")
    attach.add_argument("--max-attach-size", type=int, default=25,
                        help="Max attachment size in MB (default: 25)")

    # ── Batch ────────────────────────────────────────────────────────────
    batch = parser.add_argument_group("Batch Send")
    batch.add_argument("--throttle", type=float, default=0.5,
                       help="Seconds between batch sends (default: 0.5)")
    batch.add_argument("--subject-template",
                       help="Subject template for batch send ({name}, {email})")
    batch.add_argument("--body-template",
                       help="Body template for batch send ({name}, {email})")

    # ── Contact management ───────────────────────────────────────────────
    contact_cmds = parser.add_argument_group("Contact Management")
    contact_cmds.add_argument("--save-contact", nargs=2, metavar=("NAME", "EMAIL"),
                              help="Save a contact")
    contact_cmds.add_argument("--delete-contact", metavar="NAME", help="Delete a contact")
    contact_cmds.add_argument("--list-contacts", action="store_true",
                              help="List all saved contacts")
    contact_cmds.add_argument("--auto-save-contact", nargs=2, metavar=("NAME", "EMAIL"),
                              help="Automatically save contact (without overwrite warning)")

    # ── IMAP/POP3 operations ──────────────────────────────────────────────
    imap = parser.add_argument_group("IMAP/POP3 Operations")
    imap.add_argument("--sync-contacts", action="store_true",
                      help="Scan IMAP sent folder to build contacts (experimental)")
    imap.add_argument("--read-inbox", nargs="?", type=int, const=10, default=None,
                      help="Read recent emails from inbox (optionally specify count)")
    imap.add_argument("--protocol", choices=["imap", "pop3"], default=None,
                      help="Protocol for inbox reading (default: imap, fallback to pop3 if imap fails)")

    # ── Info commands ────────────────────────────────────────────────────
    info = parser.add_argument_group("Information")
    info.add_argument("--list-accounts", action="store_true",
                      help="List all configured email accounts from .env")
    info.add_argument("--list-providers", action="store_true",
                      help="List all supported email providers")
    info.add_argument("--list-templates", action="store_true",
                      help="List all predefined email templates")
    info.add_argument("--send-log", action="store_true", help="Show recent send history")
    info.add_argument("--send-log-lines", type=int, default=20,
                      help="Number of log entries to show (default: 20)")
    info.add_argument("--interactive", "-i", action="store_true",
                      help="Interactive setup mode")

    return parser


# =============================================================================
# Main dispatch
# =============================================================================

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Setup logging first
    _setup_logging(quiet=args.quiet, verbose=args.verbose)

    logger = logging.getLogger(__name__)

    # ── Information-only commands ──────────────────────────────────────────
    if args.list_accounts:
        result = list_accounts()
        if args.json:
            _json_exit({"accounts": result})
        print(result)
        return

    if args.list_providers:
        result = list_providers()
        if args.json:
            _json_exit({"providers": result})
        print(result)
        return

    if args.list_templates:
        result = list_templates()
        if args.json:
            _json_exit({"templates": result})
        print(result)
        return

    if args.list_contacts:
        result = list_contacts()
        if args.json:
            _json_exit({"contacts": result})
        print(result)
        return

    if args.send_log:
        result = show_send_log(args.send_log_lines)
        if args.json:
            _json_exit({"send_log": result})
        print(result)
        return

    # ── Contact management commands ────────────────────────────────────────
    if args.save_contact:
        name, email = args.save_contact
        ok, msg = add_contact(name, email)
        if args.json:
            _json_exit({"success": ok, "message": msg}, 0 if ok else 1)
        print(f"[{'OK' if ok else '!'}] {msg}")
        return

    if args.delete_contact:
        ok, msg = delete_contact(args.delete_contact)
        if args.json:
            _json_exit({"success": ok, "message": msg}, 0 if ok else 1)
        print(f"[{'OK' if ok else '!'}] {msg}")
        return

    if args.auto_save_contact:
        name, email = args.auto_save_contact
        auto_save_contact(name, email)
        if args.json:
            _json_exit({"success": True, "message": f"Auto-saved contact: {name}"})
        return

    # ── IMAP Contact Sync ────────────────────────────────────────────────
    if args.sync_contacts:
        config = load_config()
        account = get_account_config(config, args.account)
        sender = args.sender or account.get("EMAIL_ADDRESS")
        password = account.get("EMAIL_PASSWORD")
        provider_override = args.provider or account.get("EMAIL_PROVIDER")
        if not sender or not password:
            msg = "Credentials required for IMAP sync. Configure .env first."
            if args.json:
                _json_exit({"success": False, "message": msg}, 1)
            print(f"[!] {msg}")
            sys.exit(1)
        logger.info("Scanning sent folder for %s...", sender)
        count, msg = sync_contacts_from_sent(sender, password, provider_override)
        if args.json:
            _json_exit({"success": count > 0, "added": count, "message": msg})
        print(f"[{'OK' if count else 'i'}] {msg}")
        return

    # ── Read Inbox ──────────────────────────────────────────────────────
    if args.read_inbox is not None:
        config = load_config()
        account = get_account_config(config, args.account)
        sender = args.sender or account.get("EMAIL_ADDRESS")
        password = account.get("EMAIL_PASSWORD")
        provider_override = args.provider or account.get("EMAIL_PROVIDER")
        if not sender or not password:
            msg = "Credentials required for inbox read. Configure .env first."
            if args.json:
                _json_exit({"success": False, "message": msg}, 1)
            print(f"[!] {msg}")
            sys.exit(1)

        # Determine protocol: explicit flag, or auto (try imap first, fallback pop3)
        use_imap = True  # default
        if args.protocol == "pop3":
            use_imap = False

        if use_imap:
            logger.info("Reading inbox for %s (IMAP, last %d emails)...", sender, args.read_inbox)
            emails = read_inbox(
                sender, password,
                max_emails=args.read_inbox,
                provider_key=provider_override,
            )
            # IMAP failed AND no explicit protocol was set → auto-fallback to POP3
            if not emails and args.protocol is None:
                logger.info("IMAP returned no results, falling back to POP3...")
                emails = read_inbox_pop3(
                    sender, password,
                    max_emails=args.read_inbox,
                    provider_key=provider_override,
                )
        else:
            logger.info("Reading inbox for %s (POP3, last %d emails)...", sender, args.read_inbox)
            emails = read_inbox_pop3(
                sender, password,
                max_emails=args.read_inbox,
                provider_key=provider_override,
            )

        if args.json:
            _json_exit({"success": True, "emails": emails})
        if not emails:
            print("No emails found.")
        else:
            for i, em in enumerate(emails, 1):
                print(f"{i:>3}. {em['date']}  {em['from']}")
                print(f"     Subject: {em['subject']}")
                preview = str(em['body_preview'])[:120]
                if preview:
                    print(f"     {preview}")
                if em.get('attachments'):
                    print(f"     Attachments: {', '.join(em['attachments'])}")
                print()
        return

    # ── Interactive mode ─────────────────────────────────────────────────
    if args.interactive or (len(sys.argv) == 1):
        interactive_mode(args)
        return

    # ── Send email ────────────────────────────────────────────────────────
    config = load_config()

    # Validate config before proceeding
    config_errors = validate_config(config)
    if config_errors:
        for err in config_errors:
            logger.error("Config error: %s", err)
        if args.json:
            _json_exit({"success": False, "errors": config_errors}, 2)
        sys.exit(2)

    # Resolve account → sender credentials
    account = get_account_config(config, args.account)
    sender = args.sender or account.get("EMAIL_ADDRESS") or os.environ.get("EMAIL_ADDRESS")
    env_password = account.get("EMAIL_PASSWORD") or os.environ.get("EMAIL_PASSWORD")
    password = get_password(sender, env_password) if sender else env_password

    if not sender or not password:
        msg = "No credentials configured. Run with --interactive to set up."
        if args.json:
            _json_exit({"success": False, "message": msg}, 1)
        logger.error(msg)
        sys.exit(1)

    smtp = resolve_smtp_settings(account, args.provider or account.get("EMAIL_PROVIDER"))

    # ── Resolve subject and body ──────────────────────────────────────────
    subject = args.subject
    body = args.body
    body_html = args.html

    # Read body from file if specified
    if args.body_file:
        try:
            body = Path(args.body_file).read_text(encoding="utf-8")
        except Exception as e:
            if args.json:
                _json_exit({"success": False, "message": f"Failed to read body file: {e}"}, 2)
            logger.error("Failed to read body file: %s", e)
            sys.exit(2)

    # Apply template if specified
    if args.template:
        params: dict[str, str] = {}
        if args.template_params:
            for p in args.template_params:
                if "=" in p:
                    k, _, v = p.partition("=")
                    params[k.strip()] = v.strip()
        params.setdefault("sender", sender)

        t_subject, t_body, t_errors = apply_template(args.template, params)
        if t_errors:
            for err in t_errors:
                logger.warning(err)
        if t_subject is not None:
            subject = subject or t_subject
        if t_body is not None:
            body = body or t_body

    if not subject:
        subject = "(No subject)"
    if not body:
        body = ""

    # ── Resolve recipient(s) ──────────────────────────────────────────────
    # Check for batch send (--to-list)
    batch_recipients: Optional[list[str]] = None
    if args.to_list:
        try:
            text = Path(args.to_list).read_text(encoding="utf-8")
            batch_recipients = [
                line.strip() for line in text.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            if not batch_recipients:
                msg = f"No valid recipients found in {args.to_list}"
                if args.json:
                    _json_exit({"success": False, "message": msg}, 2)
                logger.error(msg)
                sys.exit(2)
        except Exception as e:
            msg = f"Failed to read recipient list: {e}"
            if args.json:
                _json_exit({"success": False, "message": msg}, 2)
            logger.error(msg)
            sys.exit(2)

    # Resolve single recipient
    single_recipient: Optional[str] = None
    if args.contact:
        email_result, warning = find_contact(args.contact)
        if not email_result:
            msg = f"Contact '{args.contact}' not found."
            if args.json:
                _json_exit({"success": False, "message": msg}, 1)
            logger.error(msg)
            sys.exit(1)
        if warning:
            logger.warning(warning)
        single_recipient = email_result
    else:
        single_recipient = args.recipient or args.to

    if not batch_recipients and not single_recipient:
        msg = "Recipient is required. Use --to EMAIL, --contact NAME, --to-list FILE, or pass positional."
        if args.json:
            _json_exit({"success": False, "message": msg}, 2)
        logger.error(msg)
        sys.exit(2)

    # ── CC/BCC ────────────────────────────────────────────────────────────
    cc_list = args.cc or None
    bcc_list = args.bcc or None

    # ── Dry Run ───────────────────────────────────────────────────────────
    if args.dry_run:
        recipients = batch_recipients or [single_recipient]
        dry_info = {
            "dry_run": True,
            "sender": sender,
            "recipients": recipients,
            "subject": subject,
            "has_body": bool(body),
            "has_html": bool(body_html),
            "cc": cc_list,
            "bcc": bcc_list,
            "attachments": args.attachments,
            "smtp": smtp.smtp_server + ":" + str(smtp.smtp_port),
        }
        if args.attachments:
            attach_ok, attach_errors = validate_attachments_multi(
                args.attachments, args.max_attach_size * 1024 * 1024
            )
            dry_info["attachment_validation"] = {
                "ok": attach_ok,
                "errors": attach_errors,
            }

        if args.json:
            _json_exit(dry_info, 0)
        # Human-readable
        print("=== DRY RUN (no email will be sent) ===")
        print(f"  From:    {sender}")
        for r in recipients:
            print(f"  To:      {r}")
        print(f"  Subject: {subject}")
        if cc_list:
            print(f"  CC:      {', '.join(cc_list)}")
        if bcc_list:
            print(f"  BCC:     {', '.join(bcc_list)}")
        if args.attachments:
            print(f"  Attachments: {', '.join(args.attachments)}")
        print(f"  SMTP:    {smtp.smtp_server}:{smtp.smtp_port} ({smtp.provider_name})")
        print("=== END DRY RUN ===")
        return

    # ── Execute send ──────────────────────────────────────────────────────

    # Batch send
    if batch_recipients:
        result = send_batch(
            sender=sender,
            password=password,
            recipients=batch_recipients,
            subject=subject,
            body=body,
            body_html=body_html,
            subject_template=args.subject_template,
            body_template=args.body_template,
            cc=cc_list,
            bcc=bcc_list,
            attachments=args.attachments,
            smtp_server=smtp.smtp_server,
            smtp_port=smtp.smtp_port,
            use_ssl=smtp.use_ssl,
            max_attachment_mb=args.max_attach_size,
            throttle=args.throttle,
        )

        # Log
        for r in result.results:
            append_send_log({
                "timestamp": __import__("datetime").datetime.now().isoformat(),
                "sender": sender,
                "recipient": r.recipient or "?",
                "subject": subject,
                "cc": ", ".join(cc_list) if cc_list else "",
                "bcc": ", ".join(bcc_list) if bcc_list else "",
                "attachments": str(len(args.attachments)) if args.attachments else "",
                "status": "OK" if r.success else "FAIL",
            })

        if args.json:
            _json_exit(result.to_dict(), 0 if result.all_succeeded else 1)

        logger.info(
            "Batch complete: %d/%d succeeded, %d failed",
            result.succeeded, result.total, result.failed,
        )
        sys.exit(0 if result.all_succeeded else 1)

    # Single send
    assert single_recipient is not None
    result = send_email(
        sender=sender,
        password=password,
        recipient=single_recipient,
        subject=subject,
        body=body,
        body_html=body_html,
        attachments=args.attachments,
        cc=cc_list,
        bcc=bcc_list,
        smtp_server=smtp.smtp_server,
        smtp_port=smtp.smtp_port,
        use_ssl=smtp.use_ssl,
        in_reply_to=args.reply,
        references=[args.reply] if args.reply else None,
        max_attachment_mb=args.max_attach_size,
    )

    # Log
    append_send_log({
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "sender": sender,
        "recipient": single_recipient,
        "subject": subject,
        "cc": ", ".join(cc_list) if cc_list else "",
        "bcc": ", ".join(bcc_list) if bcc_list else "",
        "attachments": str(len(args.attachments)) if args.attachments else "",
        "status": "OK" if result.success else "FAIL",
    })

    if args.json:
        _json_exit(result.to_dict(), 0 if result.success else 1)

    logger.log(
        logging.INFO if result.success else logging.ERROR,
        "%s", result.message,
    )
    if not result.success and result.detail:
        logger.debug("Detail: %s", result.detail)

    sys.exit(0 if result.success else 1)


def validate_attachments_multi(
    filepaths: Optional[list[str]],
    max_bytes: int,
) -> tuple[bool, list[str]]:
    """Validate multiple attachments. Returns (all_valid, error_messages)."""
    if not filepaths:
        return True, []
    errors: list[str] = []
    for fp in filepaths:
        ok, msg = validate_attachment(fp, max_bytes)
        if not ok:
            errors.append(msg)
    return len(errors) == 0, errors


# =============================================================================
# Interactive mode (adapted from original)
# =============================================================================

def interactive_mode(args: argparse.Namespace) -> None:
    """Interactive setup and send mode."""
    import getpass
    from datetime import datetime

    from email_sender import PROVIDERS, load_config, get_account_config, resolve_smtp_settings

    config = load_config()
    logger = logging.getLogger(__name__)

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

    provider_key = account.get("EMAIL_PROVIDER", "163")
    provider = PROVIDERS.get(provider_key, PROVIDERS["163"])
    print(f"Provider: {provider.name} ({provider.smtp_server}:{provider.smtp_port})")
    switch = input("Switch provider? (Enter to keep, or type key like 'qq'/'gmail'): ").strip()
    if switch and switch in PROVIDERS:
        provider_key = switch
        provider = PROVIDERS[switch]
        print(f"  Switched to {provider.name}")

    recipient = input("Recipient email: ").strip()
    subject = input("Subject: ").strip()
    print("Body (end with Ctrl+Z on Windows / Ctrl+D on Mac/Linux, or empty line with '.'):")
    body_lines: list[str] = []
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
            CONFIG_FILE = Path(__file__).parent / ".env"
            CONFIG_FILE.write_text("\n".join(lines), encoding="utf-8")
        else:
            from email_sender.config import BASE_DIR
            content = f"""# Email Sender Configuration
EMAIL_ADDRESS={sender}
EMAIL_PASSWORD={password}
EMAIL_PROVIDER={provider_key}
SMTP_SERVER={smtp.smtp_server}
SMTP_PORT={smtp.smtp_port}
"""
            (BASE_DIR / ".env").write_text(content, encoding="utf-8")
        logger.info("Config saved to .env")

    # Auto-save contact
    from email_sender.contacts import load_contacts as lc, add_contact as ac
    contacts = lc()
    if recipient not in contacts.values():
        save_contact = input(f"Save '{recipient}' as a contact? (y/N): ").strip().lower()
        if save_contact == "y":
            name = input("Contact name: ").strip()
            if name:
                ac(name, recipient)

    print()
    smtp = resolve_smtp_settings(account, provider_key)
    result = send_email(sender, password, recipient, subject, body,
                        attachments=attachments, cc=cc_list,
                        smtp_server=smtp.smtp_server,
                        smtp_port=smtp.smtp_port,
                        use_ssl=smtp.use_ssl)

    append_send_log({
        "timestamp": datetime.now().isoformat(),
        "sender": sender,
        "recipient": recipient,
        "subject": subject,
        "cc": ", ".join(cc_list) if cc_list else "",
        "bcc": "",
        "attachments": str(len(attachments)) if attachments else "",
        "status": "OK" if result.success else "FAIL",
    })

    if result.success:
        logger.info(result.message)
    else:
        logger.error(result.message)
        if result.detail:
            logger.debug("Detail: %s", result.detail)


if __name__ == "__main__":
    main()
