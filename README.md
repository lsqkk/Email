# Email Sender — Python SMTP 自动发邮件工具

通过 SMTP 协议自动发送邮件的 Python 命令行工具。开箱即用、零第三方依赖、支持附件，
内置 17+ 邮箱提供商配置、联系人系统、邮件模板、CC/BCC、发送记录查询。

## 功能特点

- **零外部依赖** — 仅使用 Python 标准库（`smtplib` + `email` + `imaplib`）
- **17+ 邮箱支持** — 163、QQ、Gmail、Outlook、Yahoo、126 等主流邮箱预设，一键切换
- **联系人系统** — 按名称发送，自动保存，实验性 IMAP 同步
- **支持附件** — 单次发送可附带多个文件
- **CC/BCC** — 抄送和密送支持
- **邮件模板** — 内置会议、报告、问候等模板，参数化填充
- **发送记录** — CSV 格式历史记录，可查询最近发送
- **SMTP 授权码** — 安全配置，不暴露登录密码
- **三种使用模式** — CLI 参数、交互模式、Python API
- **跨平台** — Windows / macOS / Linux 均可用

## 快速开始

### 1. 配置

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env，填写你的邮箱信息和提供商
```

### 2. 发送邮件

```bash
# 简单文本邮件
python send_email.py --to friend@example.com -s "Hello" -b "这是一封自动发送的邮件。"

# 带附件
python send_email.py --to friend@example.com -s "报告" -b "详情见附件。" -a report.pdf -a photo.jpg

# 抄送
python send_email.py --to user@qq.com --cc manager@163.com -s "周报" -b "这是本周工作内容。"

# 按联系人名称发送
python send_email.py --contact 张三 -s "你好" -b "好久不见"

# 使用模板
python send_email.py --template meeting -p topic=周会 -p time="下午2点" -p location=会议室A

# 使用其他邮箱提供商
python send_email.py --to user@gmail.com -s "Hi" -b "Hello" --provider gmail

# 查看发送记录
python send_email.py --send-log

# 交互模式（无参数运行）
python send_email.py
```

## 联系人系统

详见 `CONTACTS.md`。

```bash
# 保存联系人
python send_email.py --save-contact "张三" "zhangsan@qq.com"

# 按名称发送
python send_email.py --contact 张三 -s "你好" -b "好久不见"

# 列出联系人
python send_email.py --list-contacts

# 删除联系人
python send_email.py --delete-contact "张三"

# IMAP 同步联系人（实验性）
python send_email.py --sync-contacts
```

## 邮件模板

| 模板 | 描述 | 参数 |
|------|------|------|
| greeting | 日常问候 | name, message |
| meeting | 会议通知 | topic, time, location |
| report | 报告提交 | type, date |
| notice | 正式通知 | title, message |
| thankyou | 感谢信 | name, reason, message |

```bash
python send_email.py --template meeting -p topic=周会 -p time="下午2点" -p location=会议室A
```

## 支持的邮箱提供商

通过 `--provider` 参数切换：

```bash
python send_email.py --to user@qq.com -s "Hi" -b "Hello" --provider qq
```

完整列表见 `python send_email.py --list-providers`。

## 命令行参考

```text
用法: send_email.py [收件人] [选项]

收件人:
  --to EMAIL          收件人邮箱
  --contact NAME      按联系人名称发送
  --cc EMAIL          抄送（可多次使用）
  --bcc EMAIL         密送（可多次使用）

邮件内容:
  -s, --subject TEXT  邮件主题
  -b, --body TEXT     邮件正文（纯文本）
  --html TEXT         邮件正文（HTML）
  -f, --body-file     从文件读取正文
  --template NAME     使用预定义模板
  -p, --param K=V     模板参数（可多次使用）

发件人选项:
  --from EMAIL        覆盖发件人地址
  --account NAME      使用 .env 中的指定账户
  --provider KEY      邮箱提供商预设

联系人管理:
  --save-contact NAME EMAIL    保存联系人
  --delete-contact NAME        删除联系人
  --list-contacts              列出所有联系人
  --auto-save-contact N E      自动保存联系人
  --sync-contacts              从 IMAP 同步（实验性）

附件:
  -a, --attach FILE   附件文件（可多次使用）

其他:
  -i, --interactive   交互模式
  --list-accounts     查看 .env 中配置的账户
  --list-providers    查看支持的邮箱
  --list-templates    查看邮件模板
  --send-log          查看发送记录
  --save-config       保存凭据到 .env
```

## Python API 调用

```python
from send_email import send_email, load_config, add_contact

config = load_config()
result = send_email(
    sender=config["EMAIL_ADDRESS"],
    password=config["EMAIL_PASSWORD"],
    recipient="friend@example.com",
    subject="来自 Python 的邮件",
    body="正文内容",
    attachments=["report.pdf"],  # 可选
    cc=["manager@example.com"],  # 可选
)

if result["success"]:
    print("✓", result["message"])
else:
    print("✗", result["message"])
```

## 项目结构

```
Email/
├── send_email.py           # 主程序（零依赖）
├── .env                    # 凭据配置（已加入 .gitignore）
├── .env.example            # 配置模板（含完整提供商列表）
├── contacts.json           # 联系人文件（已加入 .gitignore，自动生成）
├── contacts.json.example   # 联系人模板
├── send_log.csv            # 发送记录（已加入 .gitignore，自动生成）
├── CONTACTS.md             # 联系人系统说明
├── CLAUDE.md               # Claude Code 项目指令
├── .gitignore
└── README.md
```

## 安全说明

- 凭据存储在 `.env` 文件，已加入 `.gitignore`，不会提交到 Git
- 联系人存储在 `contacts.json`，已加入 `.gitignore`
- 发送记录存储在 `send_log.csv`，已加入 `.gitignore`
- 使用 SMTP 授权码而非登录密码，降低泄露风险
- 如需公开分享此项目，请删除 `.env`、`contacts.json`、`send_log.csv`
