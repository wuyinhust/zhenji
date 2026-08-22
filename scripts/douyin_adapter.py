"""DouyinAdapter — wraps low-level douyin_media + adds P0.2 share-url resolver.

V5.1.2 重要语义修正：
- iesdouyin 在 v5.1 v0 永远不下载 video body，只输出 metadata。
- `fetch()` 把这种情况显式映射到 FetchStatus.METADATA_ONLY，不再让 ok=True 误导下游。
- 浮光档可以走 metadata_only；掠影/听澜/观澜必须 media_ready（由 worker 拒收）。
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from typing import Any
from urllib.parse import urlparse

import douyin_media
from media_adapter_protocol import (
    FetchStatus,
    MediaAdapter,
    MediaFetchResult,
    ResolvedURL,
)

logger = logging.getLogger(__name__)

SHORT_LINK_RE = re.compile(r"^https?://v\.douyin\.com/[A-Za-z0-9_-]+/?")
AWEME_ID_RE = re.compile(r"/(?:video|note)/(\d+)|modal_?[Ii]d=(\d+)")


def _follow_redirect(url: str, *, timeout: float = 10.0) -> str:
    """Follow redirects manually via GET. Returns final URL after redirect chain."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        },
        method="GET",
    )
    try:
        # Disable auto-redirect to read Location header
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        # Use a no-redirect opener to get Location, then loop.
        # Simpler approach: just walk urllib's redirect chain via custom handler.
        seen: set[str] = set()
        current = url
        for _ in range(8):
            if current in seen:
                return current
            seen.add(current)
            req = urllib.request.Request(
                current,
                headers={
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.geturl()
            except urllib.error.HTTPError as exc:
                if exc.code in (301, 302, 303, 307, 308):
                    loc = exc.headers.get("Location")
                    if loc:
                        current = loc if "://" in loc else f"{urlparse(current).scheme}://{urlparse(current).netloc}{loc}"
                        continue
                raise
    except Exception as exc:
        logger.warning("douyin redirect walk failed for %s: %s", url, exc)
        return url
    return url


def _extract_aweme_id(url: str) -> str | None:
    m = AWEME_ID_RE.search(url)
    if m:
        return m.group(1) or m.group(2)
    return None


class DouyinAdapter:
    key: str = "douyin"

    def normalize_url(self, url: str) -> str:
        return url

    def resolve_url(self, url: str) -> ResolvedURL:
        """短链 → canonical URL → 提取 aweme_id。

        关键：v.douyin.com/xxx 短链里没有 aweme_id，需要先跟 redirect 拿到完整页面 URL。
        返回的 canonical_url 给 adapter.fetch() 用，media_id 写到元数据。
        """
        canonical = url
        aweme_id: str | None = None

        if SHORT_LINK_RE.match(url):
            # 短链：跟 redirect 到完整 URL，再提取 aweme_id
            try:
                final = _follow_redirect(url)
            except Exception as exc:
                logger.warning("douyin short-link resolve failed for %s: %s", url, exc)
                final = url
            canonical = final
            aweme_id = _extract_aweme_id(final)
            # 重定向链有时返回 /share/video/<id>，再正则一次
            if not aweme_id:
                aweme_id = _extract_aweme_id(final)
        else:
            # 已经是长链形式：regex 提取
            aweme_id = _extract_aweme_id(url)

        return ResolvedURL(
            source_url=url,
            canonical_url=canonical,
            media_id=aweme_id or "unknown",
            platform=self.key,
            extra={"short_link": bool(SHORT_LINK_RE.match(url))},
        )

    def probe(self, url: str, **kwargs: Any) -> dict[str, Any]:
        return douyin_media.probe(url, **kwargs)

    def fetch(
        self,
        url: str,
        *,
        output_dir: str,
        mode: str,
        backend: str = "auto",
        ms_token: str | None = None,
        **kwargs: Any,
    ) -> MediaFetchResult:
        # mode=fuguang 跳过下载；只跑 resolve + metadata
        if mode == "fuguang":
            resolved = self.resolve_url(url)
            try:
                meta = douyin_media.probe(resolved.canonical_url, **kwargs)
            except Exception as exc:
                logger.warning("douyin metadata probe failed: %s", exc)
                meta = {
                    "aweme_id": resolved.media_id,
                    "canonical_url": resolved.canonical_url,
                    "error": str(exc),
                }
            return MediaFetchResult(
                platform=self.key,
                status=FetchStatus.METADATA_ONLY,
                output_dir=output_dir,
                files=[],
                metadata=meta,
                backend="iesdouyin_metadata_only",
                error=None,
            )

        # 浮光以外的档：调用底层 auto 调度
        dr = douyin_media.download(
            url,
            output_dir=output_dir,
            mode=mode,
            backend=backend,
            ms_token=ms_token,
            **kwargs,
        )

        if not dr.ok:
            # 区分 retryable / blocked / failed
            err = dr.error or "douyin_download_failed"
            status = FetchStatus.FAILED
            if "yt_dlp" in (dr.backend or ""):
                status = FetchStatus.RETRYABLE_ERROR
            return MediaFetchResult(
                platform=self.key,
                status=status,
                output_dir=output_dir,
                files=dr.files,
                metadata=dr.metadata,
                backend=dr.backend,
                error=err,
            )

        if dr.backend == "iesdouyin":
            return MediaFetchResult(
                platform=self.key,
                status=FetchStatus.METADATA_ONLY,
                output_dir=output_dir,
                files=dr.files,
                metadata=dr.metadata,
                backend=dr.backend,
                error=None,
            )

        has_video = any(
            f.lower().endswith((".mp4", ".mov", ".m4v", ".webm", ".mkv"))
            for f in dr.files
        )
        return MediaFetchResult(
            platform=self.key,
            status=FetchStatus.MEDIA_READY if has_video else FetchStatus.PARTIAL,
            output_dir=output_dir,
            files=dr.files,
            metadata=dr.metadata,
            backend=dr.backend,
            error=None if has_video else "douyin_returned_no_local_video",
        )

    def capabilities(self) -> dict[str, Any]:
        return {
            "metadata_only_supported": True,
            "media_ready_supported": True,
            "requires_login": True,
            "notes": (
                "v.douyin.com short-link needs redirect walk to obtain canonical URL and aweme_id; "
                "iesdouyin API fallback may hit X-Bogus/msToken limits; "
                "yt-dlp path requires logged-in Chrome douyin web."
            ),
        }
