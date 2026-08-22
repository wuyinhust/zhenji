"""Platform URL routing for Zhenji V5.1+.

路由策略：
- 严格域名匹配（host == domain or host.endswith("." + domain)）
- 绝对禁止 `domain in host` 这种会被 xhslink.com.evil.example 误识别的形态
- 只用 host == domain 或 host.endswith(".domain") 精确匹配
- host 只取 hostname（不含端口），全部小写

已知平台：
- xhs: 小红书（生产）
- douyin: 抖音 + iesdouyin + v.douyin（v5.1 adapter v0）
- instagram / tiktok: router ready, adapter 待实现
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class PlatformRoute:
    key: str
    supported: bool
    reason: str = ""


def _is_domain(host: str, domain: str) -> bool:
    """Exact-or-subdomain match. Rejects `evil.xhslink.com.attacker.tld`.

    Examples:
        _is_domain("xhslink.com", "xhslink.com")         == True
        _is_domain("www.xhslink.com", "xhslink.com")     == True
        _is_domain("xhslink.com.evil.example", "xhslink.com") == False
    """
    host = host.lower()
    domain = domain.lower()
    return host == domain or host.endswith("." + domain)


def route_url(url: str) -> PlatformRoute:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return PlatformRoute("unknown", False, "no_host")

    # 小红书（生产）
    if _is_domain(host, "xhslink.com") or _is_domain(host, "xhslink.cn"):
        return PlatformRoute("xhs", True)
    if _is_domain(host, "xiaohongshu.com"):
        return PlatformRoute("xhs", True)

    # 抖音 / 抖音短链
    if _is_domain(host, "douyin.com") or _is_domain(host, "v.douyin.com"):
        return PlatformRoute("douyin", True)
    if _is_domain(host, "iesdouyin.com"):
        return PlatformRoute("douyin", True)

    # Instagram / TikTok（仍 stub）
    if _is_domain(host, "instagram.com"):
        return PlatformRoute("instagram", False, "router_ready_adapter_not_implemented")
    if _is_domain(host, "tiktok.com"):
        return PlatformRoute("tiktok", False, "router_ready_adapter_not_implemented")

    return PlatformRoute("unknown", False, "unsupported_host")

