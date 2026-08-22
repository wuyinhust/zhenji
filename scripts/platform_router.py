"""Platform URL routing for Zhenji V5.1+.

V5.1 新增 douyin / iesdouyin 路由。TikTok 仍标记 stub（待实现）。
"""
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

    # 小红书（生产）
    if host == "xhslink.com" or host == "xhslink.cn" or ".xhslink.com" in host or ".xhslink.cn" in host:
        return PlatformRoute("xhs", True)
    if host == "xiaohongshu.com" or host.endswith(".xiaohongshu.com"):
        return PlatformRoute("xhs", True)

    # 抖音 / 抖音国际版 (v5.1 新增；adapter 已实现 v0)
    if host == "douyin.com" or host.endswith(".douyin.com"):
        return PlatformRoute("douyin", True)
    if host == "iesdouyin.com" or host.endswith(".iesdouyin.com"):
        return PlatformRoute("douyin", True)  # iesdouyin 也归到 douyin
    if host == "v.douyin.com" or host.endswith(".v.douyin.com"):
        return PlatformRoute("douyin", True)  # v.douyin.com 是分享短链

    # Instagram / TikTok（仍 stub）
    if host == "instagram.com" or host.endswith(".instagram.com"):
        return PlatformRoute("instagram", False, "router_ready_adapter_not_implemented")
    if host == "tiktok.com" or host.endswith(".tiktok.com"):
        return PlatformRoute("tiktok", False, "router_ready_adapter_not_implemented")

    return PlatformRoute("unknown", False, "unsupported_host")