"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_contacts() -> dict[str, str]:
    return {
        "张三": "zhangsan@qq.com",
        "李四": "lisi@163.com",
        "Alice": "alice@gmail.com",
    }
