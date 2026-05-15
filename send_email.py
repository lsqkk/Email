"""
Email Sender - Send emails via 163.com SMTP
Usage: python send_email.py <recipient> <subject> <body>
       python send_email.py --to <recipient> --subject <subject> --body <body>
       python send_email.py --interactive
"""
import os
import sys
import base64
import mimetypes
import smtplib
import argparse
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email import encoders
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / ".env"


def load_config():
    """Load email config from .env file."""
    config = {}
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text(encoding="utf-8").strip().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                config[key.strip()] = val.strip().strip("\"'")
    return config


def save_config(sender_email, sender_password):
    """Save email config to .env file."""
    content = f"""# Email Sender Configuration
EMAIL_ADDRESS={sender_email}
EMAIL_PASSWORD={sender_password}
SMTP_SERVER=smtp.163.com
SMTP_PORT=465
"""
    CONFIG_FILE.write_text(content, encoding="utf-8")
    print(f"[OK] Config saved to {CONFIG_FILE}")


def send_email(sender, password, recipient, subject, body,
               attachments=None,
               smtp_server="smtp.163.com", smtp_port=465):
    """
    Send email via SMTP.

    Args:
        sender: Sender email address
        password: Sender email password or SMTP authorization code
        recipient: Recipient email address
        subject: Email subject
        body: Email body text
        attachments: Optional list of file paths to attach
        smtp_server: SMTP server address
        smtp_port: SMTP server port

    Returns:
        dict with success status and message
    """
    try:
        has_attachments = attachments and any(
            Path(f).exists() for f in attachments
        )
        # If there are attachments, use mixed (multipart/alternative inside)
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
        msg["Subject"] = Header(subject, "utf-8")

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

                filename = path.name
                # RFC 2231 encoding for non-ASCII filenames
                part_filename = Header(filename, "utf-8").encode()
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=filename,
                )
                part.add_header("Content-Description", filename)
                msg.attach(part)
                print(f"  [+] Attached: {path.name} ({path.stat().st_size:,} bytes)")

        print(f"[*] Connecting to {smtp_server}:{smtp_port}...")
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
            server.login(sender, password)
            server.send_message(msg)

        file_info = f" with {len(attachments)} attachment(s)" if attachments else ""
        return {"success": True, "message": f"Email sent to {recipient}{file_info}"}

    except smtplib.SMTPAuthenticationError as e:
        return {
            "success": False,
            "message": (
                "SMTP authentication failed. 163.com requires an SMTP "
                "authorization code (授权码), not your login password.\n\n"
                "To get one:\n"
                "1. Log in to mail.163.com in a browser\n"
                "2. Go to Settings (设置) > POP3/SMTP/IMAP\n"
                "3. Enable SMTP service and generate an authorization code\n"
                "4. Use that code as the password here"
            ),
            "detail": str(e),
        }
    except smtplib.SMTPRecipientsRefused as e:
        return {"success": False, "message": f"Recipient {recipient} was refused", "detail": str(e)}
    except smtplib.SMTPSenderRefused as e:
        return {"success": False, "message": f"Sender {sender} was refused", "detail": str(e)}
    except smtplib.SMTPException as e:
        return {"success": False, "message": "SMTP error occurred", "detail": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {type(e).__name__}", "detail": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Send email via 163.com SMTP",
        epilog="Examples:\n"
               "  %(prog)s recipient@example.com\n"
               "  %(prog)s --to user@example.com -s 'Hello' -b 'Body text'\n"
               "  %(prog)s -i",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("recipient", nargs="?", help="Recipient email address (positional)")
    parser.add_argument("--to", help="Recipient email address (alternative)")
    parser.add_argument("--subject", "-s", help="Email subject")
    parser.add_argument("--body", "-b", help="Email body content")
    parser.add_argument("--body-file", "-f", help="Read body from file")
    parser.add_argument("--attach", "-a", action="append", dest="attachments",
                        help="Attach file(s) to the email (can be used multiple times)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive setup mode")
    parser.add_argument("--save-config", action="store_true", help="Save credentials to .env")
    parser.add_argument("--from", dest="sender", help="Sender email (override config)")

    args = parser.parse_args()

    # Interactive mode
    if args.interactive or (len(sys.argv) == 1):
        interactive_mode()
        return

    # Load config
    config = load_config()
    sender = args.sender or config.get("EMAIL_ADDRESS") or os.environ.get("EMAIL_ADDRESS")
    password = config.get("EMAIL_PASSWORD") or os.environ.get("EMAIL_PASSWORD")

    if not sender or not password:
        print("[!] No credentials configured. Run with --interactive to set up.")
        sys.exit(1)

    # Get recipient from positional or --to
    recipient = args.recipient or args.to
    if not recipient:
        print("[!] Recipient email is required")
        sys.exit(1)

    subject = args.subject or "(No subject)"
    body = args.body or ""
    if args.body_file:
        try:
            body = Path(args.body_file).read_text(encoding="utf-8")
        except Exception as e:
            print(f"[!] Failed to read body file: {e}")
            sys.exit(1)

    result = send_email(sender, password, recipient, subject, body,
                        attachments=args.attachments)
    print(f"[{'OK' if result['success'] else 'FAIL'}] {result['message']}")
    if not result["success"] and "detail" in result:
        print(f"  Detail: {result['detail']}")
    sys.exit(0 if result["success"] else 1)


def interactive_mode():
    """Interactive setup and send mode."""
    config = load_config()
    sender = config.get("EMAIL_ADDRESS") or ""
    password = config.get("EMAIL_PASSWORD") or ""

    print("=== Email Sender Interactive Setup ===")
    print()

    if not sender:
        sender = input("Your email address (e.g., jsxzznz@163.com): ").strip()
    else:
        print(f"Sender: {sender}")

    if not password:
        import getpass
        password = getpass.getpass("SMTP password/authorization code: ").strip()
    else:
        print("Password: [already configured]")

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

    save = input("\nSave credentials for future use? (y/N): ").strip().lower()
    if save == "y":
        save_config(sender, password)

    print()
    result = send_email(sender, password, recipient, subject, body)
    print(f"[{'OK' if result['success'] else 'FAIL'}] {result['message']}")
    if not result["success"] and "detail" in result:
        print(f"  Detail: {result['detail']}")


if __name__ == "__main__":
    main()
