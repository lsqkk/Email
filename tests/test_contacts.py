"""Tests for email_sender.contacts."""

from __future__ import annotations

import json

import pytest

from email_sender.contacts import (
    add_contact,
    delete_contact,
    find_contact,
    load_contacts,
    save_contacts,
)


class TestContacts:
    def test_add_and_load(self, tmp_path, monkeypatch):
        contacts_file = tmp_path / "contacts.json"
        monkeypatch.setattr("email_sender.contacts.CONTACTS_FILE", contacts_file)

        ok, msg = add_contact("张三", "zhangsan@qq.com")
        assert ok
        assert "Saved" in msg

        contacts = load_contacts()
        assert contacts["张三"] == "zhangsan@qq.com"

    def test_add_invalid_email(self, tmp_path, monkeypatch):
        contacts_file = tmp_path / "contacts.json"
        monkeypatch.setattr("email_sender.contacts.CONTACTS_FILE", contacts_file)

        ok, msg = add_contact("Bad", "not-an-email")
        assert not ok
        assert "Invalid email" in msg

    def test_delete_contact(self, tmp_path, monkeypatch):
        contacts_file = tmp_path / "contacts.json"
        monkeypatch.setattr("email_sender.contacts.CONTACTS_FILE", contacts_file)

        add_contact("张三", "zhangsan@qq.com")
        ok, msg = delete_contact("张三")
        assert ok
        assert "Deleted" in msg

        contacts = load_contacts()
        assert "张三" not in contacts

    def test_delete_nonexistent(self, tmp_path, monkeypatch):
        contacts_file = tmp_path / "contacts.json"
        monkeypatch.setattr("email_sender.contacts.CONTACTS_FILE", contacts_file)

        ok, msg = delete_contact("Nobody")
        assert not ok
        assert "not found" in msg

    def test_find_exact_match(self, tmp_path, monkeypatch):
        contacts_file = tmp_path / "contacts.json"
        monkeypatch.setattr("email_sender.contacts.CONTACTS_FILE", contacts_file)

        add_contact("张三", "zhangsan@qq.com")
        add_contact("张三丰", "zhangsf@qq.com")

        email, warning = find_contact("张三")
        assert email == "zhangsan@qq.com"
        assert warning is None

    def test_find_fuzzy_match_single(self, tmp_path, monkeypatch):
        contacts_file = tmp_path / "contacts.json"
        monkeypatch.setattr("email_sender.contacts.CONTACTS_FILE", contacts_file)

        add_contact("Zhang San", "zhangsan@qq.com")
        email, warning = find_contact("zhang")
        assert email == "zhangsan@qq.com"
        assert warning is None

    def test_find_fuzzy_match_multiple(self, tmp_path, monkeypatch):
        contacts_file = tmp_path / "contacts.json"
        monkeypatch.setattr("email_sender.contacts.CONTACTS_FILE", contacts_file)

        add_contact("张三", "zhangsan@qq.com")
        add_contact("张三丰", "zhangsf@qq.com")

        email, warning = find_contact("张三")
        # Exact match should win
        assert email == "zhangsan@qq.com"
        assert warning is None

    def test_find_no_match(self, tmp_path, monkeypatch):
        contacts_file = tmp_path / "contacts.json"
        monkeypatch.setattr("email_sender.contacts.CONTACTS_FILE", contacts_file)

        email, warning = find_contact("Nobody")
        assert email is None
        assert warning is None
