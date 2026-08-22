"""Platform URL routing for Zhenji V5."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class PlatformRoute:
    key: str
    supported: bool
    reason: str = ""


def route_url(url: str) -> PlatformRoute:
    host = (urlparse(url).hostname or "").lower()
    if host == "xhslink.com" or host.endswith(".xhslink.com"):
        return PlatformRoute("xhs", True)
    if host == "xiaohongshu.com" or host.endswith(".xiaohongshu.com"):
        return PlatformRoute("xhs", True)
    if host == "instagram.com" or host.endswith(".instagram.com"):
        return PlatformRoute("instagram", False, "router_ready_adapter_not_implemented")
    if host == "tiktok.com" or host.endswith(".tiktok.com"):
        return PlatformRoute("tiktok", False, "router_ready_adapter_not_implemented")
    return PlatformRoute("unknown", False, "unsupported_host")
