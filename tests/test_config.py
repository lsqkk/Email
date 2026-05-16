"""Tests for email_sender.config."""

from __future__ import annotations

from email_sender.config import (
    PROVIDERS,
    DEFAULT_PROVIDER,
    validate_config,
    resolve_smtp_settings,
    get_account_config,
)


class TestProviders:
    def test_default_provider_exists(self):
        assert DEFAULT_PROVIDER in PROVIDERS

    def test_all_providers_have_required_fields(self):
        for key, p in PROVIDERS.items():
            assert p.name, f"{key} missing name"
            assert p.smtp_server, f"{key} missing smtp_server"
            assert isinstance(p.smtp_port, int), f"{key} smtp_port not int"
            assert isinstance(p.use_ssl, bool), f"{key} use_ssl not bool"

    def test_163_smtp_details(self):
        p = PROVIDERS["163"]
        assert p.smtp_server == "smtp.163.com"
        assert p.smtp_port == 465
        assert p.use_ssl is True

    def test_gmail_uses_starttls(self):
        p = PROVIDERS["gmail"]
        assert p.smtp_port == 587
        assert p.use_ssl is False  # STARTTLS


class TestValidateConfig:
    def test_empty_config_returns_errors(self):
        errors = validate_config({})
        assert len(errors) > 0

    def test_minimal_config_passes(self):
        errors = validate_config({
            "EMAIL_ADDRESS": "test@163.com",
            "EMAIL_PASSWORD": "secret",
        })
        assert len(errors) == 0

    def test_missing_email(self):
        errors = validate_config({"EMAIL_PASSWORD": "secret"})
        assert any("EMAIL_ADDRESS" in e for e in errors)


class TestResolveSmtpSettings:
    def test_defaults_to_163(self):
        settings = resolve_smtp_settings({})
        assert settings.smtp_server == "smtp.163.com"
        assert settings.smtp_port == 465

    def test_provider_override(self):
        settings = resolve_smtp_settings({}, provider_override="qq")
        assert settings.smtp_server == "smtp.qq.com"

    def test_explicit_smtp_overrides_provider(self):
        settings = resolve_smtp_settings({
            "EMAIL_PROVIDER": "qq",
            "SMTP_SERVER": "custom.smtp.com",
            "SMTP_PORT": "587",
        })
        assert settings.smtp_server == "custom.smtp.com"
        assert settings.smtp_port == 587


class TestGetAccountConfig:
    def test_simple_format_returns_as_is(self):
        config = {"EMAIL_ADDRESS": "test@163.com", "EMAIL_PASSWORD": "pwd"}
        result = get_account_config(config)
        assert result is config  # same object

    def test_multi_account_finds_default(self):
        config = {
            "_format": "multi",
            "_default_account": "163",
            "_accounts": {
                "163": {"EMAIL_ADDRESS": "a@163.com", "EMAIL_PASSWORD": "p1"},
                "qq": {"EMAIL_ADDRESS": "b@qq.com", "EMAIL_PASSWORD": "p2"},
            },
        }
        result = get_account_config(config)
        assert result["EMAIL_ADDRESS"] == "a@163.com"
