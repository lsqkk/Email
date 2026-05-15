# Email Sender — Python SMTP 自动发邮件工具

通过 SMTP 协议自动发送邮件的 Python 命令行工具。开箱即用、零第三方依赖、支持附件。

## 功能特点

- **零外部依赖** — 仅使用 Python 标准库（`smtplib` + `email`）
- **支持附件** — 单次发送可附带多个文件
- **SMTP 授权码** — 安全配置，不暴露登录密码
- **三种使用模式** — CLI 参数、交互模式、Python API
- **跨平台** — Windows / macOS / Linux 均可用

## 快速开始

### 1. 获取 SMTP 授权码

163 邮箱的 SMTP 服务需要**授权码**，而不是登录密码：

1. 登录 [mail.163.com](https://mail.163.com/)
2. 进入 **设置 → POP3/SMTP/IMAP**
3. 开启 **SMTP 服务**，生成授权码
4. 将授权码填入 `.env` 文件

### 2. 配置

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env，填入你的信息
# EMAIL_ADDRESS=your_email@163.com
# EMAIL_PASSWORD=你的授权码
```

### 3. 发送邮件

```bash
# 简单文本邮件
python send_email.py --to friend@example.com -s "Hello" -b "这是一封自动发送的邮件。"

# 带附件
python send_email.py --to friend@example.com -s "报告" -b "详情见附件。" -a report.pdf -a photo.jpg

# 发送给自己测试
python send_email.py --to your_email@163.com -s "测试" -b "配置成功！"

# 交互模式（无参数运行）
python send_email.py
```

## 命令行参考

```text
用法: send_email.py [收件人] [选项]

位置参数:
  recipient             收件人邮箱

选项:
  --to TO               收件人邮箱
  -s, --subject TEXT    邮件主题
  -b, --body TEXT       邮件正文
  -f, --body-file FILE  从文件读取正文
  -a, --attach FILE     附件文件（可多次使用）
  -i, --interactive     交互模式
  --save-config         保存凭据到 .env
  --from SENDER         覆盖发件人地址
  --help                显示帮助

示例:
  send_email.py friend@qq.com
  send_email.py --to user@example.com -s "Hi" -b "Hello!"
  send_email.py -i
```

## Python API 调用

```python
from send_email import send_email, load_config

config = load_config()
result = send_email(
    sender=config["EMAIL_ADDRESS"],
    password=config["EMAIL_PASSWORD"],
    recipient="friend@example.com",
    subject="来自 Python 的邮件",
    body="正文内容",
    attachments=["report.pdf"],  # 可选
)

if result["success"]:
    print("✓", result["message"])
else:
    print("✗", result["message"])
```

## 迁移到其他邮箱

| 邮箱 | SMTP 服务器 | 端口 | 备注 |
|------|------------|------|------|
| 163.com | smtp.163.com | 465 (SSL) | 需要授权码 |
| QQ邮箱 | smtp.qq.com | 465 (SSL) | 需要授权码 |
| Gmail | smtp.gmail.com | 587 (TLS) | 需要 App Password |
| Outlook | smtp.office365.com | 587 (TLS) | 需要应用密码 |

修改 `.env` 文件中的 `SMTP_SERVER` 和 `SMTP_PORT` 即可切换。

## 项目结构

```
Email/
├── send_email.py       # 主程序（零依赖）
├── .env                # 凭据配置（已加入 .gitignore）
├── .env.example        # 配置模板
├── .gitignore
├── CLAUDE.md           # Claude Code 项目指令
└── README.md
```

## 安全说明

- 凭据存储在 `.env` 文件，已加入 `.gitignore`，不会提交到 Git
- 使用 SMTP 授权码而非登录密码，降低泄露风险
- 如需公开分享此项目，请删除 `.env` 并参考 `.env.example` 重新配置
