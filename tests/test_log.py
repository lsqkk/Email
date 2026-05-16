"""Tests for email_sender.log — CSV rotation."""

from __future__ import annotations

import csv

import pytest

from email_sender.log import append_send_log, show_send_log


class TestSendLog:
    def test_append_and_show(self, tmp_path, monkeypatch):
        log_file = tmp_path / "send_log.csv"
        monkeypatch.setattr("email_sender.log.SEND_LOG_FILE", log_file)
        monkeypatch.setattr("email_sender.log.MAX_LOG_ROWS", 5)  # lower threshold

        for i in range(10):
            append_send_log({
                "timestamp": f"2026-01-01T00:00:{i:02d}",
                "sender": "test@test.com",
                "recipient": f"user{i}@test.com",
                "subject": f"Test {i}",
                "cc": "",
                "bcc": "",
                "attachments": "",
                "status": "OK",
            })

        result = show_send_log(lines=5)
        assert "Test " in result
