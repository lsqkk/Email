# Email Sender — Auto Email Tool

A Python-based email sending tool via SMTP, pre-configured for 163.com.

## Project Overview

| Item | Value |
|------|-------|
| Location | `D:/git/lsqkk/Email/` |
| Script | `send_email.py` (pure Python, no third-party deps) |
| Sender | jsxzznz@163.com |
| SMTP Server | smtp.163.com:465 (SSL) |
| Credentials | `.env` file (gitignored) |

## How to Use in Claude

When the user asks to send an email, run:

```bash
python D:/git/lsqkk/Email/send_email.py --to <recipient> -s "<subject>" -b "<body>"
```

With attachments:
```bash
python D:/git/lsqkk/Email/send_email.py --to <recipient> -s "<subject>" -b "<body>" -a <file1> -a <file2>
```

Examples:
```
python send_email.py --to 1378395929@qq.com -s "Hello" -b "This is an automated email."
python send_email.py --to jsxzznz@163.com -s "Report" -b "See attached." -a report.pdf
```

## Natural Language Triggers

| User says | Action |
|-----------|--------|
| "帮我发邮件给 xxx" | Send email via SMTP |
| "给 xxx 发封邮件，主题是..." | Full email with subject and body |
| "发邮件带附件" | Use `-a` flag for attachments |
| "测试发邮件" | Send a test to jsxzznz@163.com |

## Migration for Other Users

To use this tool with a different email:

1. Copy `.env.example` to `.env`
2. Fill in your email and SMTP authorization code
3. Run: `python send_email.py --to yourself@example.com -s "Test" -b "Hello"`
4. Update paths in this file if the project moves

Other email providers (QQ, Gmail, Outlook):
- QQ: smtp.qq.com:465
- Gmail: smtp.gmail.com:587 (TLS)
- Outlook: smtp.office365.com:587 (TLS)
