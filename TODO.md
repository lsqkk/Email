# Email Sender 重构待办清单

> 定位：**其他 AGENT 可调用的 SMTP CLI 工具**
> 状态：✅ 已完成 Phase 1-3 + Phase 4 大部分 + Phase 5

---

## Phase 1 — 架构重构 ✅

- [x] **1.1 拆分为多模块包**
  - `email_sender/` 包：`config.py`, `contacts.py`, `templates.py`, `smtp_client.py`, `imap_client.py`, `log.py`, `types.py`, `utils.py`
  - `send_email.py` 降为薄 CLI 入口

- [x] **1.2 添加完整类型注解**
  - 所有函数参数和返回值加 type hints
  - 定义 `SendRequest`、`SendResult`、`EmailConfig` 等 dataclass

- [x] **1.3 用 `logging` 替换 `print()`**
  - 引入标准 `logging` 模块
  - 支持 `--quiet` / `--verbose` 控制输出级别
  - JSON 模式下日志走 stderr，结果走 stdout

- [x] **1.4 配置启动时校验**
  - `validate_config()` 在 send 前检查必填字段

- [x] **1.5 CSV 日志轮转**
  - 超过 1000 行自动轮转，保留 3 个备份

- [x] **1.6 联系人操作加文件锁**
  - lock-file 模式（`contacts.json.lock`），跨平台兼容

- [x] **1.7 添加单元测试**
  - `tests/` 目录，pytest 框架，38 个测试
  - 覆盖：联系人 CRUD、模板渲染、邮箱验证、配置解析、CSV 日志

---

## Phase 2 — CLI 设计改进 ✅

- [x] **2.1 JSON 输出模式**
  - `--json` 参数，结构化 JSON 输出

- [x] **2.2 Dry-Run 模式**
  - `--dry-run` 预览，不实际发送

- [x] **2.3 联系人精确匹配**
  - 优先精确匹配，多模糊匹配时告警
  - 支持 `--contact-exact` 强制精确

- [x] **2.4 规范化退出码**
  - 0=成功，1=发送失败，2=配置/参数错误

---

## Phase 3 — 核心功能增强 ✅

- [x] **3.1 HTML + 纯文本双渲染**
  - `multipart/alternative` 同时包含 text/plain 和 text/html
  - HTML 自动降级为纯文本 fallback

- [x] **3.2 批量发送（邮件合并）**
  - `--to-list file.txt` 批量发信
  - `--subject-template` / `--body-template` 支持 `{name}`, `{email}` 占位符
  - `--throttle` 控制发送间隔

- [x] **3.3 模板系统升级**
  - 缺失参数检测并报告（不再静默忽略）

- [x] **3.4 IMAP 收件箱读取**
  - `--read-inbox [N]` 读取最近 N 封邮件
  - 输出发件人、主题、日期、正文预览

- [x] **3.5 邮件回复支持**
  - `--reply message-id` 设置 `In-Reply-To` 和 `References` 头

---

## Phase 4 — 安全与可靠性

- [x] **4.1 附件大小校验**
  - 默认 25MB 上限，`--max-attach-size` 可配置

- [x] **4.2 SMTP 重试机制**
  - 网络错误自动重试 2 次，1s/3s 退避

- [x] **4.3 发送频率控制**
  - `--throttle` 参数，批量模式默认间隔 0.5s

- [ ] **4.4 密码管理（待办）**
  - 调研 Python keyring 库集成
  - 支持系统密钥链存储

---

## Phase 5 — 文档 ✅

- [x] **5.1 README.md 重写**
  - 对外展示风格：徽章、表格、丰富示例、功能亮点

- [x] **5.2 CLAUDE.md 重写**
  - AGENT 入职文档：项目结构、编码约束、API 速查

---

## 实施总结

```
Phase 1 架构 ✅  →  1186行单文件 → 9模块包 + 类型注解 + 日志 + 测试
Phase 2 CLI  ✅  →  JSON/Dry-Run/退出码/联系人匹配
Phase 3 功能 ✅  →  HTML双渲染/批量发送/IMAP收件/回复
Phase 4 安全 ✅  →  附件校验/重试/频率控制  (密码管理待办)
Phase 5 文档 ✅  →  README对外展示 / CLAUDE入职指南
```
