"""Adapter registry — single point that ties platforms to their MediaAdapter.

V5.1.2 引入目的：
- V5.1.0/5.1.1 阶段 media_worker.py 仍然 hardcode `if job.platform != "xhs"`。
- 必须有一个平台 key → adapter 实例的注册表；
- 第三方插件（IG / TikTok / 第三方抖音）可以 `register(MyAdapter())` 注入。

设计原则：
- ADAPTERS 是稳定 registry，不允许被破坏（register 校验 key 不能冲突）
- get(key) 找不到时返回 None 而非抛异常（worker 自决）
- `platform` → adapter key 来自 platform_router.route_url() 的输出，绝不在此处重新判断域名
"""
from __future__ import annotations

import logging
from typing import Iterable

from media_adapter_protocol import MediaAdapter

logger = logging.getLogger(__name__)

# 默认注册。允许运行时 register() 增量扩展。
ADAPTERS: dict[str, MediaAdapter] = {}


def register(adapter: MediaAdapter) -> None:
    """Register a platform adapter. Raises if key conflicts with existing entry."""
    if not isinstance(adapter, MediaAdapter):
        raise TypeError(f"{adapter!r} does not satisfy MediaAdapter protocol")
    key = adapter.key
    if not isinstance(key, str) or not key:
        raise ValueError(f"adapter.key must be a non-empty string, got {key!r}")
    if key in ADAPTERS:
        existing = type(ADAPTERS[key]).__name__
        new = type(adapter).__name__
        if existing != new:
            logger.warning(
                "adapter %r is being replaced: %s -> %s", key, existing, new
            )
    ADAPTERS[key] = adapter


def unregister(key: str) -> None:
    ADAPTERS.pop(key, None)


def get(key: str) -> MediaAdapter | None:
    return ADAPTERS.get(key)


def keys() -> list[str]:
    return list(ADAPTERS)


def supported_keys() -> list[str]:
    """Only platforms whose adapter says media_ready_supported=True."""
    return [
        k for k, a in ADAPTERS.items()
        if a.capabilities().get("media_ready_supported", False)
    ]


# Default adapter wiring (imports happen lazily to avoid cycles).
def _register_defaults() -> None:
    from xhs_adapter import XhsAdapter
    from douyin_adapter import DouyinAdapter

    register(XhsAdapter())
    register(DouyinAdapter())


_register_defaults()
