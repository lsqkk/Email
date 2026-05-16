# Email Sender — CLAUDE Code 项目指南

> 此文件面向接管本项目的新 AGENT。阅读此文件后你应能理解项目结构、编码约束和工作流程。

## 项目定位

**SMTP CLI 工具**，专为其他 AGENT（包括 Claude Code）调用而设计。不是独立的邮件客户端，不是邮件服务器。

核心原则：
- **零第三方依赖** — 仅 Python 3.10+ 标准库
- **机器可解析输出** — 所有操作支持 `--json` 模式
- **失败可观测** — 规范化退出码，结构化错误信息

## 目录结构

```
Email/
├── send_email.py              # CLI 入口（薄层，仅参数解析+分发）
├── email_sender/              # 核心包
│   ├── __init__.py            # 公共 API 导出
│   ├── types.py               # 类型定义（SendRequest, SendResult 等 dataclass）
│   ├── config.py              # 配置加载 + 17个邮箱提供商预设
│   ├── contacts.py            # 联系人 CRUD + 文件锁并发安全
│   ├── templates.py           # 邮件模板（5个内置模板 + 缺失参数检测）
│   ├── smtp_client.py         # SMTP 核心（发信/批量/HTML双渲染/重试/附件校验）
│   ├── imap_client.py         # IMAP/POP3 操作（收件箱读取/联系人同步）
│   ├── log.py                 # 发送记录 CSV + 自动轮转
│   └── utils.py               # 校验/格式化/HTML转纯文本
├── tests/                     # pytest 测试
│   ├── test_config.py
│   ├── test_contacts.py
│   ├── test_templates.py
│   ├── test_log.py
│   └── test_utils.py
├── .env                       # 凭据（gitignored）
├── .env.example               # 配置模板
├── contacts.json              # 联系人（gitignored）
├── send_log.csv               # 发送记录（gitignored）
├── TODO.md                    # 重构待办
├── CLAUDE.md                  # 本文件
└── README.md                  # 对外展示文档
```

## 编码约束

### 类型注解

所有函数必须有完整类型注解。新增函数必须：
- 所有参数有 type hint
- 返回值有 type hint
- 复杂数据结构用 dataclass 而非裸 dict

```python
# ✅ 正确
def send_email(sender: str, password: str, recipient: str, ...) -> SendResult: ...

# ❌ 错误
def send_email(sender, password, recipient, ...):
```

### 日志

**禁止使用 `print()` 输出运行时信息。** 一律使用 `logging` 模块：
- `logging.info()` — 正常流程信息
- `logging.warning()` — 可恢复的问题
- `logging.error()` — 不可恢复的错误
- `logging.debug()` — 调试用详细输出

`print()` 仅在两种场景允许：
1. CLI 的 `--help` 输出（argparse 自动处理）
2. `--dry-run` 模式的人类可读输出

### 测试

- 新增功能必须有对应测试
- 测试使用 pytest，放在 `tests/` 目录
- 覆盖联系人 CRUD、模板渲染、校验逻辑
- SMTP 测试使用 mock，不连真实服务器

### 错误处理

- 校验类错误（参数缺失、附件超限）：退出码 **2**
- 发送类错误（SMTP 拒绝、认证失败）：退出码 **1**
- 所有错误应同时支持人类可读和 `--json` 两种输出

### 不可变性

- 函数参数不修改（no mutation）
- 联系人、配置等数据结构读写分离
- 文件操作使用上下文管理器

## 联系人系统

- 联系人存储在 `contacts.json`（已 gitignore）
- 读写使用文件锁（`contacts.json.lock`），并发安全
- `find_contact()` 优先精确匹配，再大小写不敏感模糊匹配
- 多个模糊匹配结果发出警告，不静默选择

## 关键 API 速查

```python
from email_sender import send_email, send_batch, read_inbox, read_inbox_pop3, load_config

# 单发
result = send_email(sender="a@163.com", password="xxx", recipient="b@qq.com",
                    subject="Hi", body="Hello", body_html="<h1>Hello</h1>")

# 批量
result = send_batch(sender="a@163.com", password="xxx",
                    recipients=["b@qq.com", "c@qq.com"],
                    subject="通知", body="正文", throttle=0.5)

# 读取收件箱（IMAP，自动 ID 命令适配）
emails = read_inbox("a@163.com", "xxx", max_emails=5)

# 读取收件箱（POP3）
emails = read_inbox_pop3("a@163.com", "xxx", max_emails=5)

# 结果解析
print(result.success, result.message, result.detail)
```

## 常见开发任务

```bash
# 运行测试
python -m pytest tests/ -v

# 运行测试+覆盖率
python -m pytest tests/ --cov=email_sender

# 测试发信
python send_email.py --dry-run --to test@test.com -s "测试" -b "正文"

# 真实发信
python send_email.py --to friend@example.com -s "你好" -b "好久不见"
```

## 相关文件

- `CONTACTS.md` — 联系人系统详细使用说明
- `TODO.md` — 当前重构和待办清单
- 全局规则见 `~/.claude/rules/` 下的 Python 和通用规则
