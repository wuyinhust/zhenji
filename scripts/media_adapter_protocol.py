"""Media adapter protocol + unified result types (Zhenji V5.1.2).

引入目的：
- xhs_media 和 douyin_media 在 V5.1 之前各自定义 `DownloadResult(ok, backend, files, ...)`。
- 但 `ok=True` 在 iesdouyin/v0 场景下意味着\"只拿到 metadata、本地无视频\"——下游 pipeline 误以为\"下载成功\"。
- 需要一个跨平台统一的结果类型，区分 metadata 状态 vs media 状态。

状态机：
    metadata_only   - 仅有 metadata，无本地副本（浮光够用，掠影/听澜/观澜拒收）
    media_ready     - 本地副本下载成功 + metadata 拿到
    partial         - metadata 拿到但下载不完整
    blocked         - 平台反爬拦截（登录失效 / 验证码 / 地区限制）
    retryable_error - 网络 / 临时错，可重试
    failed          - 不可恢复错误

四档含义：
    fuguang   - 接受 metadata_only、media_ready（本地副本可选）
    lueying   - 必须 media_ready
    tinglan   - 必须 media_ready
    guanlan   - 必须 media_ready

Protocol:
    MediaAdapter
        key                str  'xhs' | 'douyin' | ...
        normalize_url()    一致化短链到一致形态
        resolve_url()      短链 → canonical URL，提取 media_id
        probe()            拿 metadata（不下载）
        fetch()            拿 media + metadata（按 mode 决定 quality）
        capabilities()     metadata_only_supported / media_ready_supported / requires_login
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class FetchStatus(str, Enum):
    METADATA_ONLY = "metadata_only"
    MEDIA_READY = "media_ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    RETRYABLE_ERROR = "retryable_error"
    FAILED = "failed"


# 四档对应的最低要求
MODE_REQUIREMENTS: dict[str, set[FetchStatus]] = {
    "fuguang": {FetchStatus.METADATA_ONLY, FetchStatus.MEDIA_READY},
    "lueying": {FetchStatus.MEDIA_READY},
    "tinglan": {FetchStatus.MEDIA_READY},
    "guanlan": {FetchStatus.MEDIA_READY},
}


@dataclass(frozen=True)
class ResolvedURL:
    """短链 → 一致化的规范形态。"""
    source_url: str
    canonical_url: str
    media_id: str
    platform: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class MediaFetchResult:
    """跨平台统一的下载结果（替代各自 adapter 私有的 DownloadResult）。"""
    platform: str
    status: FetchStatus
    output_dir: str
    files: list[str]               # 本地副本路径（metadata_only 可为空）
    metadata: dict[str, Any] | None
    error: str | None = None
    backend: str | None = None     # yt_dlp / iesdouyin / smile7up / f2 ...

    @property
    def metadata_ready(self) -> bool:
        return self.metadata is not None

    @property
    def media_ready(self) -> bool:
        return self.status == FetchStatus.MEDIA_READY

    @property
    def ok(self) -> bool:
        """兼容 V5.1 旧调用方：`ok == metadata_ready` (NOT media_ready)."""
        return self.metadata_ready

    def acceptable_for_mode(self, mode: str) -> bool:
        return self.status in MODE_REQUIREMENTS.get(mode, set())

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "status": self.status.value,
            "output_dir": self.output_dir,
            "files": self.files,
            "metadata": self.metadata,
            "error": self.error,
            "backend": self.backend,
            "metadata_ready": self.metadata_ready,
            "media_ready": self.media_ready,
        }


@runtime_checkable
class MediaAdapter(Protocol):
    """所有平台适配器必须实现这套接口。"""
    key: str

    def normalize_url(self, url: str) -> str: ...
    def resolve_url(self, url: str) -> ResolvedURL: ...
    def probe(self, url: str, **kwargs: Any) -> dict[str, Any]: ...
    def fetch(
        self,
        url: str,
        *,
        output_dir: str,
        mode: str,
        backend: str = "auto",
        **kwargs: Any,
    ) -> MediaFetchResult: ...

    def capabilities(self) -> dict[str, Any]:
        """声明能力，影响 routing / worker 决策。"""
        return {
            "metadata_only_supported": True,
            "media_ready_supported": True,
            "requires_login": False,
        }

