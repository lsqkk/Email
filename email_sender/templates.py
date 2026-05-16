"""Email template system — built-in templates + custom file loading."""

from __future__ import annotations

from typing import Optional

# =============================================================================
# Built-in Templates
# =============================================================================
TEMPLATES: dict[str, dict[str, object]] = {
    "greeting": {
        "description": "日常问候",
        "subject": "你好，{name}",
        "body_text": "{name}，你好！\n\n{message}\n\n祝好，\n{sender}",
        "params": {"name": "对方称呼", "message": "问候内容"},
    },
    "meeting": {
        "description": "会议通知",
        "subject": "会议邀请：{topic}",
        "body_text": "你好，\n\n主题：{topic}\n时间：{time}\n地点：{location}\n\n请准时参加。\n\n{sender}",
        "params": {"topic": "会议主题", "time": "会议时间", "location": "会议地点"},
    },
    "report": {
        "description": "报告提交",
        "subject": "{type}报告 - {date}",
        "body_text": "您好，\n\n这是{date}的{type}报告，请查收附件。\n\n{sender}",
        "params": {"type": "报告类型（周报/月报等）", "date": "日期"},
    },
    "notice": {
        "description": "正式通知",
        "subject": "通知：{title}",
        "body_text": "各位好，\n\n{message}\n\n{sender}",
        "params": {"title": "通知标题", "message": "通知内容"},
    },
    "thankyou": {
        "description": "感谢信",
        "subject": "感谢：{reason}",
        "body_text": "{name}，你好！\n\n非常感谢你的{reason}！\n\n{message}\n\n此致\n{sender}",
        "params": {"name": "对方称呼", "reason": "感谢事由", "message": "补充内容"},
    },
}


def apply_template(
    template_name: str,
    params: dict[str, str],
) -> tuple[Optional[str], Optional[str], Optional[list[str]]]:
    """Apply a template with given params.

    Returns (subject, body_text, errors).
      - errors is None if all params resolved.
      - errors lists missing/unresolved placeholders otherwise.
    """
    t = TEMPLATES.get(template_name)
    if not t:
        return None, None, [f"Unknown template: {template_name}"]

    subject = str(t["subject"])
    body = str(t["body_text"])

    # Find all {placeholder} patterns
    import re
    placeholders = set(re.findall(r'\{(\w+)\}', subject + body))
    missing: list[str] = []
    for ph in sorted(placeholders):
        if ph in params:
            val = params[ph]
            subject = subject.replace("{" + ph + "}", val)
            body = body.replace("{" + ph + "}", val)
        else:
            missing.append(ph)

    errors = None
    if missing:
        errors = [f"Missing template parameter: {m}" for m in missing]

    return subject, body, errors


def list_templates() -> str:
    """Return formatted template list."""
    lines: list[str] = [
        f"{'Name':<15} {'Description':<20} {'Parameters':<40}",
        "-" * 75,
    ]
    for key in sorted(TEMPLATES):
        t = TEMPLATES[key]
        params_list = ", ".join(f"{k}={v}" for k, v in t["params"].items())  # type: ignore[union-attr]
        lines.append(f"{key:<15} {t['description']:<20} {params_list:<40}")
    lines.append("")
    lines.append("Usage: --template NAME -p key=value -p key=value ...")
    return "\n".join(lines)
