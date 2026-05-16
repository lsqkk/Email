# 联系人系统 — Contacts System

## 概述

联系人存储在 `contacts.json` 文件（已 gitignore），格式为 `{"名称": "邮箱"}`。

**首次使用前请复制 `contacts.json.example` 为 `contacts.json`**（或首次保存联系人时自动创建）。

## 在 Claude 中的使用

### 保存联系人

当用户首次提到给某人发邮件并提供其邮箱时，**必须自动保存联系人**：

```bash
python send_email.py --save-contact "张三" "zhangsan@qq.com"
# 输出: [OK] Saved contact: 张三 <zhangsan@qq.com>

# 或使用自动保存模式（不覆盖已有冲突）：
python send_email.py --auto-save-contact "张三" "zhangsan@qq.com"
```

### 按名称发送

联系人保存后，可通过姓名直接发送：

```bash
# 通过联系人名称发送
python send_email.py --contact "张三" -s "你好" -b "好久不见"
```

### 管理联系人

```bash
# 列出所有联系人
python send_email.py --list-contacts

# 删除联系人
python send_email.py --delete-contact "张三"

# 从邮箱服务器同步联系人（实验性，需要IMAP支持）
python send_email.py --sync-contacts
```

### 智能联系人解析

脚本支持模糊匹配：如果联系人名称不完整，会自动尝试部分匹配。

## 联系人自动保存规则

1. **显式保存**：通过 `--save-contact 名称 邮箱` 保存
2. **自动保存**：当 Claude 从用户对话中得知某人的姓名和邮箱时，自动调用 `--auto-save-contact`
3. **不覆盖**：如果联系人已存在且邮箱不同，`--auto-save-contact` 不会覆盖，避免误操作
4. **交互式保存**：在交互模式（`-i`）下，输入新收件人会询问是否保存为联系人

## 从邮箱同步联系人（实验性）

`--sync-contacts` 命令通过 IMAP 扫描已发送邮件中的收件人地址，自动构建联系人列表：

```
python send_email.py --sync-contacts
```

支持的邮箱：163、QQ、126、Gmail、Outlook、Yahoo、Foxmail 等（需 IMAP 可用）。

受限于 IMAP 协议，此功能只能扫描已发送邮件的收件人，无法获取邮箱完整的通讯录。
要实现完整的通讯录同步，需要各邮箱提供商的 API（如 Google People API、Microsoft Graph API），
这些需要 OAuth 认证，超出当前纯 SMTP 工具的范围。

## 注意事项

- `contacts.json` 已加入 `.gitignore`，不会被提交到 Git
- 建议定期备份 `contacts.json`
- 联系人在发送邮件时自动解析，大小写不敏感模糊匹配
