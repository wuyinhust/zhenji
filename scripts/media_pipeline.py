"""One local media job processor for Zhenji V5."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

from ffmpeg_tools import extract_audio, extract_scene_frames, extract_uniform_frames
from transcription import transcribe_faster_whisper, save_transcript
from xhs_media import download


VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}


@dataclass
class PipelineResult:
    ok: bool
    backend: str | None
    mode: str
    video_path: str | None
    audio_path: str | None
    keyframes: list[str]
    scene_frames: list[str]
    transcript_txt: str | None
    transcript_json: str | None
    metadata: dict[str, Any] | None
    error: str | None


def _pick_video(files: list[str]) -> str | None:
    candidates = [
        f for f in files
        if Path(f).suffix.lower() in VIDEO_EXTS
    ]
    if not candidates:
        return None
    # Prefer the largest file as the likely merged/full media.
    candidates.sort(key=lambda f: Path(f).stat().st_size if Path(f).exists() else 0)
    return candidates[-1]


def process_xhs_url(
    *,
    url: str,
    post_key: str,
    mode: str,
    output_root: str,
    downloader_backend: str = "auto",
    smile7up_script: str | None = None,
    yt_dlp_bin: str = "yt-dlp",
    cookies_from_browser: str | None = "chrome",
    ffmpeg_bin: str = "ffmpeg",
    ffprobe_bin: str = "ffprobe",
    whisper_model: str = "small",
    whisper_device: str = "auto",
) -> PipelineResult:
    job_dir = Path(output_root) / post_key
    job_dir.mkdir(parents=True, exist_ok=True)

    dl = download(
        url,
        output_dir=str(job_dir),
        mode=mode,
        backend=downloader_backend,
        smile7up_script=smile7up_script,
        yt_dlp_bin=yt_dlp_bin,
        cookies_from_browser=cookies_from_browser,
    )
    if not dl.ok:
        return PipelineResult(
            False, dl.backend, mode, None, None, [], [],
            None, None, dl.metadata, dl.error
        )

    video = _pick_video(dl.files)
    if not video:
        return PipelineResult(
            False, dl.backend, mode, None, None, [], [],
            None, None, dl.metadata, "download_succeeded_but_video_not_found"
        )

    keyframe_count = {
        "lueying": 8,
        "tinglan": 10,
        "guanlan": 24,
    }.get(mode, 8)

    keyframes = extract_uniform_frames(
        video,
        str(job_dir / "keyframes"),
        count=keyframe_count,
        ffmpeg_bin=ffmpeg_bin,
        ffprobe_bin=ffprobe_bin,
    )

    audio_path = None
    transcript_txt = None
    transcript_json = None
    scene_frames: list[str] = []

    if mode in {"tinglan", "guanlan"}:
        audio_path = extract_audio(
            video,
            str(job_dir / "audio.mp3"),
            ffmpeg_bin=ffmpeg_bin,
        )
        result = transcribe_faster_whisper(
            audio_path,
            model_name=whisper_model,
            device=whisper_device,
        )
        transcript_txt, transcript_json = save_transcript(
            result, str(job_dir / "transcript")
        )

    if mode == "guanlan":
        scene_frames = extract_scene_frames(
            video,
            str(job_dir / "scenes"),
            ffmpeg_bin=ffmpeg_bin,
        )

    manifest = {
        "post_key": post_key,
        "source_url": url,
        "mode": mode,
        "backend": dl.backend,
        "video_path": video,
        "audio_path": audio_path,
        "keyframes": keyframes,
        "scene_frames": scene_frames,
        "transcript_txt": transcript_txt,
        "transcript_json": transcript_json,
        "metadata": dl.metadata,
    }
    (job_dir / "zhenji-media-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return PipelineResult(
        True, dl.backend, mode, video, audio_path,
        keyframes, scene_frames,
        transcript_txt, transcript_json,
        dl.metadata, None
    )
