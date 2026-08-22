"""Xiaohongshu media resolver/downloader adapter.

Backends:
- smile7up: call a local checkout's download_xiaohongshu.py
- yt_dlp: direct CLI invocation
- auto: smile7up if configured and exists, otherwise yt_dlp
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import shutil
import subprocess
import sys
import time


@dataclass
class DownloadResult:
    ok: bool
    backend: str
    output_dir: str
    files: list[str]
    metadata: dict[str, Any] | None
    error: str | None


def _run(cmd: list[str], timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def probe(
    url: str,
    *,
    yt_dlp_bin: str = "yt-dlp",
    cookies_from_browser: str | None = "chrome",
    timeout_seconds: float = 45,
) -> dict[str, Any]:
    cmd = [yt_dlp_bin, "-J", "--skip-download", "--no-warnings"]
    if cookies_from_browser:
        cmd += ["--cookies-from-browser", cookies_from_browser]
    cmd += [url]
    p = _run(cmd, timeout_seconds)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "yt-dlp probe failed")
    return json.loads(p.stdout)


def _quality_for_mode(mode: str) -> str:
    return {
        "lueying": "480p",
        "tinglan": "720p",
        "guanlan": "best",
    }.get(mode, "480p")


def _snapshot_files(path: Path) -> set[Path]:
    if not path.exists():
        return set()
    return {p.resolve() for p in path.rglob("*") if p.is_file()}


def _new_files(path: Path, before: set[Path]) -> list[str]:
    if not path.exists():
        return []
    return sorted(
        str(p.resolve())
        for p in path.rglob("*")
        if p.is_file() and p.resolve() not in before
    )


def download_with_smile7up(
    url: str,
    *,
    script_path: str,
    output_dir: str,
    mode: str,
    browser: str = "chrome",
    timeout_seconds: float = 1800,
) -> DownloadResult:
    script = Path(script_path).expanduser()
    if not script.exists():
        return DownloadResult(
            False, "smile7up", output_dir, [], None,
            f"smile7up script not found: {script}"
        )

    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    before = _snapshot_files(out)

    quality = _quality_for_mode(mode)
    cmd = [
        sys.executable, str(script), url,
        "-o", str(out),
        "-q", quality,
        "--browser", browser,
    ]
    if mode in {"tinglan", "guanlan"}:
        cmd.append("--full")

    p = _run(cmd, timeout_seconds)
    files = _new_files(out, before)
    return DownloadResult(
        ok=p.returncode == 0,
        backend="smile7up",
        output_dir=str(out),
        files=files,
        metadata=None,
        error=None if p.returncode == 0 else (p.stderr.strip() or p.stdout.strip()),
    )


def download_with_yt_dlp(
    url: str,
    *,
    output_dir: str,
    mode: str,
    yt_dlp_bin: str = "yt-dlp",
    cookies_from_browser: str | None = "chrome",
    timeout_seconds: float = 1800,
) -> DownloadResult:
    if shutil.which(yt_dlp_bin) is None:
        return DownloadResult(
            False, "yt_dlp", output_dir, [], None,
            f"tool_missing:{yt_dlp_bin}"
        )

    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    before = _snapshot_files(out)

    quality = _quality_for_mode(mode)
    cmd = [
        yt_dlp_bin,
        "--write-info-json",
        "--no-warnings",
        "-o", str(out / "%(id)s" / "%(title).80B [%(id)s].%(ext)s"),
    ]
    if cookies_from_browser:
        cmd += ["--cookies-from-browser", cookies_from_browser]

    if quality == "best":
        cmd += ["-f", "bv*+ba/b"]
    else:
        height = quality.rstrip("p")
        cmd += [
            "-f", "bv*+ba/b",
            "-S", f"res:{height}",
        ]

    if mode in {"tinglan", "guanlan"}:
        cmd += ["--write-subs", "--write-auto-subs"]

    cmd += [url]
    p = _run(cmd, timeout_seconds)
    files = _new_files(out, before)

    metadata = None
    info_files = [Path(f) for f in files if f.endswith(".info.json")]
    if info_files:
        try:
            metadata = json.loads(info_files[-1].read_text(encoding="utf-8"))
        except Exception:
            metadata = None

    return DownloadResult(
        ok=p.returncode == 0,
        backend="yt_dlp",
        output_dir=str(out),
        files=files,
        metadata=metadata,
        error=None if p.returncode == 0 else (p.stderr.strip() or p.stdout.strip()),
    )


def download(
    url: str,
    *,
    output_dir: str,
    mode: str,
    backend: str = "auto",
    smile7up_script: str | None = None,
    yt_dlp_bin: str = "yt-dlp",
    cookies_from_browser: str | None = "chrome",
) -> DownloadResult:
    selected = backend
    if backend == "auto":
        if smile7up_script and Path(smile7up_script).expanduser().exists():
            selected = "smile7up"
        else:
            selected = "yt_dlp"

    if selected == "smile7up":
        if not smile7up_script:
            return DownloadResult(
                False, "smile7up", output_dir, [], None,
                "smile7up_script_not_configured"
            )
        return download_with_smile7up(
            url,
            script_path=smile7up_script,
            output_dir=output_dir,
            mode=mode,
            browser=cookies_from_browser or "none",
        )

    if selected == "yt_dlp":
        return download_with_yt_dlp(
            url,
            output_dir=output_dir,
            mode=mode,
            yt_dlp_bin=yt_dlp_bin,
            cookies_from_browser=cookies_from_browser,
        )

    return DownloadResult(
        False, selected, output_dir, [], None,
        f"unknown_backend:{selected}"
    )
