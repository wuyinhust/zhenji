"""Generic local media pipeline (Zhenji V5.1.2+).

平台无关：通过 media_adapters.ADAPTERS registry 拉 platform → adapter；
不再写死 from xhs_media import download。

四档路由（MODE_REQUIREMENTS 来自 media_adapter_protocol）：
    fuguang → metadata_only or media_ready 均可
    lueying / tinglan / guanlan → 必须 media_ready
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

from ffmpeg_tools import extract_audio, extract_scene_frames, extract_uniform_frames
from transcription import transcribe_faster_whisper, save_transcript
from media_adapters import get as get_adapter
from media_adapter_protocol import (
    FetchStatus,
    MediaFetchResult,
)

logger = logging.getLogger(__name__)


VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}


@dataclass
class PipelineResult:
    ok: bool
    platform: str
    backend: str | None
    mode: str
    fetch_status: str
    video_path: str | None
    audio_path: str | None
    keyframes: list[str]
    scene_frames: list[str]
    transcript_txt: str | None
    transcript_json: str | None
    metadata: dict[str, Any] | None
    error: str | None


def _pick_video(files: list[str]) -> str | None:
    candidates = [f for f in files if Path(f).suffix.lower() in VIDEO_EXTS]
    if not candidates:
        return None
    candidates.sort(key=lambda f: Path(f).stat().st_size if Path(f).exists() else 0)
    return candidates[-1]


def process_media_url(
    *,
    platform: str,
    url: str,
    post_key: str,
    mode: str,
    output_root: str,
    downloader_backend: str = "auto",
    yt_dlp_bin: str = "yt-dlp",
    cookies_from_browser: str | None = "chrome",
    ffmpeg_bin: str = "ffmpeg",
    ffprobe_bin: str = "ffprobe",
    whisper_model: str = "small",
    whisper_device: str = "auto",
    **adapter_kwargs: Any,
) -> PipelineResult:
    """Run one media job regardless of platform.

    Steps:
        1. Resolve adapter from registry
        2. Adapter.fetch() → MediaFetchResult
        3. Validate status against mode requirement
        4. Run extract_audio / extract_uniform_frames / extract_scene_frames
        5. Run transcribe_faster_whisper for tinglan/guanlan
        6. Persist zhenji-media-manifest.json
    """
    adapter = get_adapter(platform)
    if adapter is None:
        return PipelineResult(
            ok=False, platform=platform, backend=None, mode=mode,
            fetch_status="failed",
            video_path=None, audio_path=None, keyframes=[], scene_frames=[],
            transcript_txt=None, transcript_json=None, metadata=None,
            error=f"adapter_not_registered:{platform}",
        )

    job_dir = Path(output_root) / post_key
    job_dir.mkdir(parents=True, exist_ok=True)

    fetch: MediaFetchResult = adapter.fetch(
        url,
        output_dir=str(job_dir),
        mode=mode,
        backend=downloader_backend,
        yt_dlp_bin=yt_dlp_bin,
        cookies_from_browser=cookies_from_browser,
        **adapter_kwargs,
    )

    # 档位强约束
    if not fetch.acceptable_for_mode(mode):
        return PipelineResult(
            ok=False, platform=platform, backend=fetch.backend, mode=mode,
            fetch_status=fetch.status.value,
            video_path=None, audio_path=None, keyframes=[], scene_frames=[],
            transcript_txt=None, transcript_json=None,
            metadata=fetch.metadata,
            error=(
                f"fetch_status_not_acceptable_for_mode:{mode}:"
                f"{fetch.status.value}:{fetch.error or ''}"
            ).strip(":"),
        )

    video = _pick_video(fetch.files)
    if mode != "fuguang" and not video:
        return PipelineResult(
            ok=False, platform=platform, backend=fetch.backend, mode=mode,
            fetch_status=fetch.status.value,
            video_path=None, audio_path=None, keyframes=[], scene_frames=[],
            transcript_txt=None, transcript_json=None,
            metadata=fetch.metadata,
            error="fetch_returned_no_local_video",
        )

    keyframe_count = {
        "lueying": 8,
        "tinglan": 10,
        "guanlan": 24,
    }.get(mode, 8)

    keyframes: list[str] = []
    audio_path: str | None = None
    transcript_txt: str | None = None
    transcript_json: str | None = None
    scene_frames: list[str] = []

    if video is not None:
        if mode in {"lueying", "tinglan", "guanlan"}:
            keyframes = extract_uniform_frames(
                video, str(job_dir / "keyframes"),
                count=keyframe_count, ffmpeg_bin=ffmpeg_bin, ffprobe_bin=ffprobe_bin,
            )
        if mode in {"tinglan", "guanlan"}:
            audio_path = extract_audio(
                video, str(job_dir / "audio.mp3"), ffmpeg_bin=ffmpeg_bin,
            )
            try:
                tresult = transcribe_faster_whisper(
                    audio_path,
                    model_name=whisper_model,
                    device=whisper_device,
                )
                transcript_txt, transcript_json = save_transcript(
                    tresult, str(job_dir / "transcript"),
                )
            except Exception as exc:
                logger.warning("transcription failed: %s", exc)
                error_str = f"transcription_failed:{type(exc).__name__}:{exc}"
        if mode == "guanlan":
            scene_frames = extract_scene_frames(
                video, str(job_dir / "scenes"), ffmpeg_bin=ffmpeg_bin,
            )

    manifest = {
        "post_key": post_key,
        "platform": platform,
        "source_url": url,
        "mode": mode,
        "fetch_status": fetch.status.value,
        "backend": fetch.backend,
        "metadata_ready": fetch.metadata_ready,
        "media_ready": fetch.media_ready,
        "video_path": video,
        "audio_path": audio_path,
        "keyframes": keyframes,
        "scene_frames": scene_frames,
        "transcript_txt": transcript_txt,
        "transcript_json": transcript_json,
        "metadata": fetch.metadata,
    }
    (job_dir / "zhenji-media-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return PipelineResult(
        ok=True, platform=platform, backend=fetch.backend, mode=mode,
        fetch_status=fetch.status.value,
        video_path=video, audio_path=audio_path,
        keyframes=keyframes, scene_frames=scene_frames,
        transcript_txt=transcript_txt, transcript_json=transcript_json,
        metadata=fetch.metadata, error=None,
    )


# === 兼容 V5.1 旧 API ===
def process_xhs_url(
    *,
    url: str,
    post_key: str,
    mode: str,
    output_root: str,
    downloader_backend: str = "auto",
    smile7up_script: str | None = None,  # 旧参数；忽略
    **kwargs: Any,
) -> PipelineResult:
    """Deprecated shim. 旧代码仍可调用；内部走 process_media_url(platform='xhs')。"""
    result = process_media_url(
        platform="xhs",
        url=url,
        post_key=post_key,
        mode=mode,
        output_root=output_root,
        downloader_backend=downloader_backend,
        **kwargs,
    )
