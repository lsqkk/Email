"""Tests for email_sender.templates."""

from __future__ import annotations

import pytest

from email_sender.templates import apply_template, list_templates


class TestApplyTemplate:
    def test_greeting_template(self):
        subject, body, errors = apply_template("greeting", {
            "name": "小王",
            "message": "最近好吗？",
            "sender": "me@test.com",
        })
        assert errors is None
        assert "小王" in subject
        assert "最近好吗？" in body

    def test_missing_params_detected(self):
        subject, body, errors = apply_template("meeting", {
            "topic": "周会",
            # missing: time, location, sender
        })
        assert subject == "会议邀请：周会"
        assert errors is not None
        assert len(errors) > 0
        missing_names = [e for e in errors if "Missing" in e]
        assert len(missing_names) > 0

    def test_unknown_template(self):
        subject, body, errors = apply_template("nonexistent", {})
        assert subject is None
        assert body is None
        assert errors is not None

    def test_param_replacement(self):
        subject, body, errors = apply_template("report", {
            "type": "周报",
            "date": "2026-05-16",
            "sender": "me@test.com",
        })
        assert errors is None
        assert "周报" in subject
        assert "2026-05-16" in subject


class TestListTemplates:
    def test_returns_string(self):
        result = list_templates()
        assert isinstance(result, str)
        assert "greeting" in result
        assert "meeting" in result
