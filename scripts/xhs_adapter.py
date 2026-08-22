"""XhsAdapter — wraps low-level xhs_media.download into MediaAdapter protocol."""
from __future__ import annotations

import logging
from typing import Any

import xhs_media
from media_adapter_protocol import (
    FetchStatus,
    MediaAdapter,
    MediaFetchResult,
    ResolvedURL,
)

logger = logging.getLogger(__name__)


class XhsAdapter:
    key: str = "xhs"

    def normalize_url(self, url: str) -> str:
        # 小红书 URL 形态相对简单；暂不做 normalize，留待后续按需扩展。
        return url

    def resolve_url(self, url: str) -> ResolvedURL:
        # 短链没法在不联网的情况下 resolve；调用方应该先让 yt-dlp/工具跟进。
        from urllib.parse import urlparse
        u = urlparse(url)
        host = u.hostname or ""
        media_id = (u.path.rstrip("/").split("/")[-1] or "unknown")
        return ResolvedURL(
            source_url=url,
            canonical_url=url,
            media_id=media_id,
            platform=self.key,
            extra={"host": host},
        )

    def probe(self, url: str, **kwargs: Any) -> dict[str, Any]:
        return xhs_media.probe(url, **kwargs)

    def fetch(
        self,
        url: str,
        *,
        output_dir: str,
        mode: str,
        backend: str = "auto",
        **kwargs: Any,
    ) -> MediaFetchResult:
        dr = xhs_media.download(
            url,
            output_dir=output_dir,
            mode=mode,
            backend=backend,
            **kwargs,
        )
        if not dr.ok:
            return MediaFetchResult(
                platform=self.key,
                status=FetchStatus.FAILED,
                output_dir=output_dir,
                files=dr.files,
                metadata=dr.metadata,
                backend=dr.backend,
                error=dr.error or "xhs_download_failed",
            )
        # xhs_media 在 smile7up/yt-dlp 路径下都会产生本地视频；据此推断 media_ready
        has_video = any(
            f.lower().endswith((".mp4", ".mov", ".m4v", ".webm", ".mkv"))
            for f in dr.files
        )
        status = FetchStatus.MEDIA_READY if has_video else FetchStatus.PARTIAL
        return MediaFetchResult(
            platform=self.key,
            status=status,
            output_dir=output_dir,
            files=dr.files,
            metadata=dr.metadata,
            backend=dr.backend,
            error=None if has_video else "xhs_returned_no_local_video",
        )

    def capabilities(self) -> dict[str, Any]:
        return {
            "metadata_only_supported": True,
            "media_ready_supported": True,
            "requires_login": True,
            "notes": "xhs web requires logged-in chrome; otherwise yt-dlp returns no formats.",
        }

