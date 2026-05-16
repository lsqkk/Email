<div align="center">

# ✉️ Email Sender

**零依赖 · 多邮箱 · 批量发信 · IMAP收件 · AGENT友好**

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/providers-17-orange" alt="17 Providers">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

**纯 Python 标准库实现，开箱即用的 SMTP 命令行邮件工具。**  
支持 17 个主流邮箱提供商、联系人系统、HTML+纯文本双渲染、批量邮件合并，以及 IMAP/POP3 收件箱读取。

---

</div>

## ✨ 功能亮点

| 功能 | 说明 |
|------|------|
| 🚀 **零外部依赖** | 仅用 Python 标准库，`pip install` 都不需要 |
| 📬 **17 个邮箱** | 163、QQ、Gmail、Outlook、Yahoo 等一键切换 |
| 📎 **附件支持** | 多文件附件，自动大小校验（默认 25MB 上限） |
| 👥 **联系人系统** | 按名称发送、模糊查找、文件锁并发安全 |
| 📨 **HTML + 纯文本** | `multipart/alternative` 双渲染，客户端兼容性最佳 |
| 📋 **批量发送** | 从文件读取收件人列表，支持 `{name}` 个性化模板 |
| 🗂️ **IMAP/POP3 收件** | 读取收件箱邮件，预览正文摘要，自动协议降级 |
| 🔄 **自动重试** | 网络波动自动重试 2 次，指数退避 |
| 📊 **发送日志** | CSV 格式历史记录，自动轮转不撑爆 |
| 🤖 **AGENT 友好** | 完整 `--json` 输出模式，规范退出码，Dry-Run 预览 |

## 🚀 快速开始

### 1. 配置

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env，填写你的邮箱信息和 SMTP 授权码
# 支持多账户：163、QQ、Gmail 等
```

> 🔐 使用 **SMTP 授权码**而非登录密码。  
> 163邮箱：设置 → POP3/SMTP/IMAP → 开启SMTP服务 → 生成授权码  
> QQ邮箱：设置 → 账户 → POP3/SMTP服务 → 生成授权码  

### 2. 发一封邮件

```bash
# 简单文本邮件
python send_email.py --to friend@example.com -s "Hello" -b "这是一封自动发送的邮件。"

# 带 HTML
python send_email.py --to friend@qq.com -s "通知" --html "<h1>标题</h1><p>正文内容</p>"

# 带附件和抄送
python send_email.py --to user@qq.com --cc manager@163.com -s "报告" -b "详情见附件" -a report.pdf

# 按联系人名称发送
python send_email.py --save-contact "张三" "zhangsan@qq.com"
python send_email.py --contact 张三 -s "你好" -b "好久不见"
```

### 3. 批量发送

```bash
# 准备收件人列表文件 recipients.txt：
# lilei@qq.com
# hanmeimei@163.com
# wangwu@gmail.com

# 批量发送，每人收到独立的邮件
python send_email.py --to-list recipients.txt -s "会议通知" \
  --subject-template "会议通知 - {name}" \
  --body-template "{name}，请于本周五下午2点参加周会。"

# 控制发送间隔（防封）
python send_email.py --to-list recipients.txt -s "通知" -b "正文" --throttle 1.0
```

### 4. 读取收件箱

```bash
# 读取最近的 5 封邮件（自动 IMAP，失败则降级 POP3）
python send_email.py --read-inbox 5

# 强制指定协议
python send_email.py --read-inbox 5 --protocol imap
python send_email.py --read-inbox 5 --protocol pop3

# JSON 格式输出（AGENT 解析用）
python send_email.py --read-inbox 5 --json
```

## 🤖 AGENT 调用模式

本工具为 **AGENT 调用**场景专门设计：

```bash
# JSON 输出，AGENT 直接解析
python send_email.py --json --to user@test.com -s "Hi" -b "Hello"
# → {"success": true, "message": "Email sent to user@test.com", "recipient": "user@test.com", "message_id": "<...>"}

# Dry-Run 预览，不实际发送
python send_email.py --dry-run --to user@test.com -s "测试" -b "正文"

# 静默模式，仅输出关键信息
python send_email.py --quiet --to user@test.com -s "Hi" -b "Body"

# Python API 调用
python -c "
from email_sender import send_email
r = send_email('me@163.com', 'pass', 'you@qq.com', 'Hi', 'Hello')
print(r.success, r.message)
"
```

### 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 发送成功 |
| `1` | 发送失败（SMTP 拒绝、认证失败等） |
| `2` | 参数/配置错误 |
| `3` | 校验失败（附件超限等） |

## 📋 常用命令速查

```bash
# ── 发送 ──────────────────────────────────────────
python send_email.py --to user@163.com -s "主题" -b "正文"
python send_email.py --contact 张三 -s "你好" -b "好久不见"
python send_email.py --template meeting -p topic=周会 -p time="下午2点"
python send_email.py --reply "<prev-msg-id@domain>" --to user@163.com -s "Re: 讨论"

# ── 批量 ──────────────────────────────────────────
python send_email.py --to-list users.txt -s "通知"
python send_email.py --to-list users.txt --subject-template "Hi {name}" --body-template "Hello {name}"

# ── 收件 ──────────────────────────────────────────
python send_email.py --read-inbox
python send_email.py --read-inbox 20
python send_email.py --read-inbox 5 --protocol pop3
python send_email.py --read-inbox 5 --protocol imap

# ── 联系人 ────────────────────────────────────────
python send_email.py --save-contact "张三" "zhangsan@qq.com"
python send_email.py --list-contacts
python send_email.py --sync-contacts

# ── 信息 ──────────────────────────────────────────
python send_email.py --list-providers
python send_email.py --list-accounts
python send_email.py --list-templates
python send_email.py --send-log

# ── 高级 ──────────────────────────────────────────
python send_email.py --html "<h1>标题</h1>" --to user@163.com -s "富文本"
python send_email.py --dry-run --to user@test.com -s "测试"  # 不发送
python send_email.py --json --to user@test.com -s "Hi" -b "Hello"  # JSON输出
python send_email.py --account qq --to friend@qq.com -s "用QQ发"
python send_email.py --provider gmail --to user@gmail.com -s "Via Gmail"
```

## 🎨 模板系统

内置 5 种邮件模板，参数化填充：

```bash
# 会议通知
python send_email.py --template meeting \
  -p topic="周会" \
  -p time="2026-05-18 14:00" \
  -p location="会议室A"

# 感谢信
python send_email.py --template thankyou \
  -p name="李总" \
  -p reason="项目支持" \
  -p message="您的建议非常有价值"
```

| 模板 | 用途 | 参数 |
|------|------|------|
| `greeting` | 日常问候 | name, message |
| `meeting` | 会议通知 | topic, time, location |
| `report` | 报告提交 | type, date |
| `notice` | 正式通知 | title, message |
| `thankyou` | 感谢信 | name, reason, message |

## 🔧 支持的邮箱提供商

共 **17 个**，通过 `--provider` 一键切换：

```
163        QQ        126       新浪       Foxmail
Yeah.net   Gmail     Outlook    Yahoo     阿里企业
搜狐       Zoho      AOL       Yandex     139邮箱
189邮箱
```

```bash
# 查看完整列表
python send_email.py --list-providers

# 切换到 Gmail
python send_email.py --provider gmail --to user@gmail.com -s "Hi" -b "Hello"
```

## ⚙️ Python API

```python
from email_sender import send_email, send_batch, read_inbox, read_inbox_pop3

# 单发
result = send_email(
    sender="me@163.com",
    password="auth_code",
    recipient="friend@qq.com",
    subject="来自 Python 的邮件",
    body="正文",
    body_html="<h1>正文</h1>",      # 可选 HTML
    attachments=["report.pdf"],
    cc=["manager@163.com"],
)
print(f"{'✓' if result.success else '✗'} {result.message}")

# 批量
result = send_batch(
    sender="me@163.com",
    password="auth_code",
    recipients=["a@qq.com", "b@163.com"],
    subject="批量通知",
    body="正文",
    throttle=0.5,  # 间隔 0.5 秒
)
print(f"成功: {result.succeeded}/{result.total}")

# 读取收件箱（IMAP，自动 ID 命令适配）
emails = read_inbox("me@163.com", "auth_code", max_emails=5)
for mail in emails:
    print(f"{mail['date']}  {mail['from']}  {mail['subject']}")

# 读取收件箱（POP3）
emails = read_inbox_pop3("me@163.com", "auth_code", max_emails=5)
```

## 🏗️ 项目结构

```
Email/
├── send_email.py            # CLI 入口
├── email_sender/            # 核心包
│   ├── config.py            # 配置 + 17个邮箱提供商预设
│   ├── contacts.py          # 联系人管理（并发安全）
│   ├── templates.py         # 邮件模板
│   ├── smtp_client.py       # SMTP 发信核心
│   ├── imap_client.py       # IMAP/POP3 收件 + 联系人同步
│   ├── log.py               # 发送记录
│   ├── utils.py             # 校验 / 工具函数
│   └── types.py             # 类型定义
├── tests/                   # 测试
└── .env.example             # 配置模板
```

## 📄 许可证

MIT License. 自由使用、修改、分发。

---

<div align="center">

**Made with Python standard library. No dependencies, no bloat, just email.**

</div>
