"""Tests for email_sender.utils."""

from __future__ import annotations

import pytest
from email_sender.utils import (
    is_valid_email,
    validate_attachment,
    html_to_plain_text,
    format_bytes,
)


class TestIsValidEmail:
    def test_valid_emails(self):
        assert is_valid_email("user@example.com")
        assert is_valid_email("test.user+tag@domain.co.uk")
        assert is_valid_email("a@b.cn")

    def test_invalid_emails(self):
        assert not is_valid_email("")
        assert not is_valid_email("not-an-email")
        assert not is_valid_email("@domain.com")
        assert not is_valid_email("user@")
        assert not is_valid_email("user@.com")


class TestValidateAttachment:
    def test_file_not_found(self):
        ok, msg = validate_attachment("/nonexistent/file.txt")
        assert not ok
        assert "not found" in msg

    def test_file_too_large(self, tmp_path):
        f = tmp_path / "big.txt"
        f.write_bytes(b"x" * (30 * 1024 * 1024))  # 30 MB
        ok, msg = validate_attachment(str(f), max_bytes=25 * 1024 * 1024)
        assert not ok
        assert "too large" in msg

    def test_file_within_limit(self, tmp_path):
        f = tmp_path / "small.txt"
        f.write_text("hello")
        ok, msg = validate_attachment(str(f), max_bytes=25 * 1024 * 1024)
        assert ok
        assert msg == ""


class TestHtmlToPlainText:
    def test_strips_tags(self):
        result = html_to_plain_text("<p>Hello <b>world</b></p>")
        assert "Hello" in result
        assert "world" in result
        assert "<b>" not in result

    def test_converts_br_to_newline(self):
        result = html_to_plain_text("Line1<br>Line2<br/>Line3")
        assert "Line1\nLine2" in result

    def test_decodes_entities(self):
        result = html_to_plain_text("&amp; &lt; &gt; &quot;")
        assert "& < >" in result  # &amp; → &

    def test_strips_style_and_script(self):
        html = "<style>body { color: red; }</style><p>Hello</p><script>alert(1)</script>"
        result = html_to_plain_text(html)
        assert "Hello" in result
        assert "color" not in result
        assert "alert" not in result


class TestFormatBytes:
    def test_bytes(self):
        assert format_bytes(500) == "500 B"

    def test_kilobytes(self):
        assert "KB" in format_bytes(2048)

    def test_megabytes(self):
        assert "MB" in format_bytes(1048576 * 5)
