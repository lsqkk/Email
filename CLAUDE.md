# Email Sender — Auto Email Tool

A Python-based email sending tool via SMTP. Supports 17+ email providers, contacts system,
CC/BCC, email templates, and send history log. Zero third-party dependencies.

## Project Overview

| Item | Value |
|------|-------|
| Location | `D:/git/lsqkk/Email/` |
| Script | `send_email.py` (pure Python, no third-party deps) |
| Default Sender | jsxzznz@163.com |
| Default Provider | 163.com |
| Credentials | `.env` file (gitignored) |
| Contacts | `contacts.json` file (gitignored) |

## How to Use in Claude

### Basic Send

```bash
python D:/git/lsqkk/Email/send_email.py --to <recipient> -s "<subject>" -b "<body>"
```

### With Contact Name

```bash
# First save the contact
python D:/git/lsqkk/Email/send_email.py --save-contact "张三" "zhangsan@qq.com"

# Then send by name
python D:/git/lsqkk/Email/send_email.py --contact 张三 -s "你好" -b "好久不见"
```

### With Attachments

```bash
python D:/git/lsqkk/Email/send_email.py --to <recipient> -s "<subject>" -b "<body>" -a <file1> -a <file2>
```

### With CC/BCC

```bash
python D:/git/lsqkk/Email/send_email.py --to user@example.com --cc manager@example.com -s "Report" -b "Content"
```

### Using Email Templates

```bash
# Available: greeting, meeting, report, notice, thankyou
python D:/git/lsqkk/Email/send_email.py --template meeting -p topic=周会 -p time="下午2点" -p location=会议室A
```

### With a Different Provider

```bash
python D:/git/lsqkk/Email/send_email.py --to user@qq.com -s "Hi" -b "Body" --provider qq
```

### Send History

```bash
python D:/git/lsqkk/Email/send_email.py --send-log
```

### Interactive Mode

```bash
python D:/git/lsqkk/Email/send_email.py -i
```

## ⚠️ MUST READ: Contacts System

**Before sending emails using this tool, you MUST read `CONTACTS.md`** for details on:
- Saving contacts
- Sending by contact name
- Auto-saving contacts when users provide names and emails
- Managing contacts

The `CONTACTS.md` file is located at: `D:/git/lsqkk/Email/CONTACTS.md`

## Supported Providers (17 total)

| Provider | Key | SMTP | Port |
|----------|-----|------|------|
| 163邮箱 (DEFAULT) | `163` | smtp.163.com | 465 |
| QQ邮箱 | `qq` | smtp.qq.com | 465 |
| QQ企业邮箱 | `qq_ex` | smtp.exmail.qq.com | 465 |
| 126邮箱 | `126` | smtp.126.com | 465 |
| Gmail | `gmail` | smtp.gmail.com | 587 |
| Outlook/Hotmail | `outlook` | smtp.office365.com | 587 |
| Yahoo邮箱 | `yahoo` | smtp.mail.yahoo.com | 465 |
| 新浪邮箱 | `sina` | smtp.sina.com.cn | 465 |
| 阿里企业邮箱 | `aliyun` | smtp.qiye.aliyun.com | 465 |
| Foxmail | `foxmail` | smtp.foxmail.com | 465 |
| 搜狐邮箱 | `sohu` | smtp.sohu.com | 465 |
| Yeah.net | `yeah` | smtp.yeah.net | 465 |
| 139邮箱 | `139` | smtp.139.com | 465 |
| 189邮箱 | `189` | smtp.189.cn | 465 |
| Zoho | `zoho` | smtp.zoho.com | 587 |
| AOL | `aol` | smtp.aol.com | 587 |
| Yandex | `yandex` | smtp.yandex.com | 465 |

List all: `python send_email.py --list-providers`

## Natural Language Triggers

| User says | Action |
|-----------|--------|
| "帮我发邮件给 xxx" | Send email via SMTP |
| "给 xxx 发封邮件，主题是..." | Full email with subject and body |
| "发邮件带附件" | Use `-a` flag for attachments |
| "发邮件抄送给 xxx" | Use `--cc` flag |
| "用模板发个会议通知" | Use `--template meeting` |
| "给张三发邮件" | Resolve from contacts via `--contact` |
| "保存张三的邮箱" | Use `--save-contact` |
| "测试发邮件" | Send a test to jsxzznz@163.com |
| "查发送记录" | Use `--send-log` |

## Command Reference

```text
Usage: send_email.py [recipient] [options]

Recipient:
  --to EMAIL           Recipient email address
  --contact NAME       Send to a saved contact by name
  --cc EMAIL           Carbon copy (can be used multiple times)
  --bcc EMAIL          Blind carbon copy (can be used multiple times)

Email Content:
  -s, --subject TEXT   Email subject
  -b, --body TEXT      Email body (plain text)
  --html TEXT          Email body (HTML)
  -f, --body-file FILE Read body from file
  --template NAME      Use predefined template
  -p, --param K=V      Template parameter (can be used multiple times)

Sender Options:
  --from EMAIL         Override sender email
  --provider KEY       Email provider preset

Contact Management:
  --save-contact NAME EMAIL    Save a contact
  --delete-contact NAME        Delete a contact
  --list-contacts              List all contacts
  --auto-save-contact N E      Auto-save contact (no overwrite)
  --sync-contacts              Scan IMAP sent folder (experimental)

Attachments:
  -a, --attach FILE    Attach file (can be used multiple times)

Other:
  -i, --interactive    Interactive setup mode
  --list-providers     List all supported providers
  --list-templates     List all predefined templates
  --send-log           Show recent send history
  --save-config        Save credentials to .env
```

## Migration for Other Users

1. Copy `.env.example` to `.env`
2. Set `EMAIL_PROVIDER` to your provider (see list above)
3. Fill in your email and SMTP authorization code
4. Run: `python send_email.py --to yourself@example.com -s "Test" -b "Hello"`
5. Update paths in this file if the project moves
