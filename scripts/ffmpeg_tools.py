"""Local FFmpeg helpers for Zhenji V5."""
from __future__ import annotations

from pathlib import Path
import json
import math
import shutil
import subprocess


def _run(cmd: list[str], timeout: float = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=timeout, check=False
    )


def probe_duration(video_path: str, ffprobe_bin: str = "ffprobe") -> float:
    if shutil.which(ffprobe_bin) is None:
        raise RuntimeError(f"tool_missing:{ffprobe_bin}")
    p = _run([
        ffprobe_bin, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        video_path,
    ], timeout=60)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "ffprobe failed")
    data = json.loads(p.stdout)
    return float(data["format"]["duration"])


def extract_audio(
    video_path: str,
    output_path: str,
    ffmpeg_bin: str = "ffmpeg",
) -> str:
    if shutil.which(ffmpeg_bin) is None:
        raise RuntimeError(f"tool_missing:{ffmpeg_bin}")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    p = _run([
        ffmpeg_bin, "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "mp3", str(out),
    ])
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "ffmpeg audio extraction failed")
    return str(out)


def extract_uniform_frames(
    video_path: str,
    output_dir: str,
    count: int = 8,
    max_width: int = 720,
    ffmpeg_bin: str = "ffmpeg",
    ffprobe_bin: str = "ffprobe",
) -> list[str]:
    if count < 1:
        return []
    duration = max(probe_duration(video_path, ffprobe_bin), 0.001)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # One ffmpeg invocation; fps interval approximates evenly-spaced samples.
    fps = count / duration
    pattern = str(out / "frame_%03d.jpg")
    vf = f"fps={fps:.8f},scale='min({max_width},iw)':-2"
    p = _run([
        ffmpeg_bin, "-y", "-i", video_path,
        "-vf", vf,
        "-frames:v", str(count),
        "-q:v", "3",
        pattern,
    ])
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "ffmpeg frame extraction failed")
    return [str(p) for p in sorted(out.glob("frame_*.jpg"))]


def extract_scene_frames(
    video_path: str,
    output_dir: str,
    threshold: float = 0.35,
    max_frames: int = 40,
    max_width: int = 960,
    ffmpeg_bin: str = "ffmpeg",
) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pattern = str(out / "scene_%03d.jpg")
    vf = (
        f"select='gt(scene,{threshold})',"
        f"scale='min({max_width},iw)':-2"
    )
    p = _run([
        ffmpeg_bin, "-y", "-i", video_path,
        "-vf", vf,
        "-vsync", "vfr",
        "-frames:v", str(max_frames),
        "-q:v", "3",
        pattern,
    ])
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "ffmpeg scene extraction failed")
    return [str(p) for p in sorted(out.glob("scene_*.jpg"))]
