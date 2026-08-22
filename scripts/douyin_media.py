"""Douyin media adapter for Zhenji V5.1+.

类比 xhs_media.py，但目标是抖音。

下载策略（v5.1.2 现状，按实际能力描述，不夸大）：
    1. yt-dlp Douyin extractor（需要 Chrome 已登录 douyin web）
    2. iesdouyin.com web API（公开 metadata endpoint；成功率不稳定，
       不视为稳定保证；不实现 X-Bogus / a_bogus 签名算法）

绝对不要写成既定能力的描述：
    - \"免 cookie，仅需 msToken header\" × → 必须实际验证当前接口可用
    - \"msToken (X-MS-STUB) header\" × → 当前仅作为可选 Cookie 携带
    - \"抖音国际/反爬 API\" × → iesdouyin.com 不是国际版，是 web 端点，
      跟 tiktok 国际版无关

诚实版本：
    用户主动提供 msToken 或 cookie 时可走 iesdouyin metadata 接口；
    不实现 X-Bogus / a_bogus 签名；
    命中率与字段可用性不做稳定保证。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import shutil
import subprocess
import sys


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
    """Probe a douyin URL via yt-dlp. Returns parsed metadata dict.

    Requires user to be logged in to douyin web in Chrome.
    """
    cmd = [yt_dlp_bin, "-J", "--skip-download", "--no-warnings"]
    if cookies_from_browser:
        cmd += ["--cookies-from-browser", cookies_from_browser]
    cmd += [url]
    p = _run(cmd, timeout_seconds)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "yt-dlp douyin probe failed")
    return json.loads(p.stdout)


def _quality_for_mode(mode: str) -> str:
    return {
        "fuguang": "none",  # 浮光不需要本地副本
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


def download_with_yt_dlp(
    url: str,
    *,
    output_dir: str,
    mode: str,
    yt_dlp_bin: str = "yt-dlp",
    cookies_from_browser: str | None = "chrome",
    timeout_seconds: float = 1800,
) -> DownloadResult:
    """Download via yt-dlp. Requires user to be logged in to douyin web."""
    if shutil.which(yt_dlp_bin) is None:
        return DownloadResult(
            False, "yt_dlp", output_dir, [], None,
            f"tool_missing:{yt_dlp_bin}",
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
    elif quality != "none":
        height = quality.rstrip("p")
        cmd += ["-f", "bv*+ba/b", "-S", f"res:{height}"]

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


def download_with_iesdouyin(
    url: str,
    *,
    output_dir: str,
    ms_token: str | None = None,
    timeout_seconds: float = 600,
) -> DownloadResult:
    """Try iesdouyin.com/web/api/v2/aweme/iteminfo to get public metadata.

    已知事实（v5.1.2 实测 / 当前环境观察）：
        - 当前接口在不携带 cookie 时通常也会返回 item 字段，
          但命中率与 schema 字段可用性不能视为稳定保证；
        - 即便带了 msToken cookie，仍可能受 X-Bogus 签名校验失败；
        - 抖音水印 video_url 即使拿到，也需要 ffmpeg 二次处理去水印；
        - 因此 v0 路径只写 metadata.json，不下载视频本体。

    Args:
        url: 完整 URL（必须是 canonical douyin.com/video/<id> 形式；
              v.douyin.com 短链请先用 DouyinAdapter.resolve_url() 跟 redirect）。
        ms_token: 用户可选提供的 msToken cookie。
        timeout_seconds: HTTP 请求超时。

    Returns:
        DownloadResult with metadata only — files=[iesdouyin_metadata.json]，
        backend='iesdouyin'。never ok=True 表示"已下载视频"。

    NOT implemented:
        X-Bogus / a_bogus 签名算法
        Video body download (含水印处理 / 去水印)
    """
    import re
    import urllib.request

    # Extract aweme_id from URL
    m = re.search(r"/(?:video|note)/(\d+)", url) or re.search(r"modal_?[Ii]d=(\d+)", url)
    if not m:
        return DownloadResult(
            False, "iesdouyin", output_dir, [], None,
            "could_not_extract_aweme_id_from_url",
        )
    aweme_id = m.group(1)

    api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={aweme_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        "Referer": "https://www.douyin.com/",
    }
    if ms_token:
        headers["Cookie"] = f"msToken={ms_token}"

    req = urllib.request.Request(api_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return DownloadResult(
            False, "iesdouyin", output_dir, [], None,
            f"iesdouyin_request_failed:{type(exc).__name__}:{exc}",
        )

    if payload.get("status_code") != 0:
        return DownloadResult(
            False, "iesdouyin", output_dir, [], None,
            f"iesdouyin_api_status:{payload.get('status_code')}:{payload.get('status_msg', '?')}",
        )

    item_list = payload.get("item_list") or []
    if not item_list:
        return DownloadResult(False, "iesdouyin", output_dir, [], None, "no_item_in_response")

    item = item_list[0]
    metadata = {
        "aweme_id": item.get("aweme_id"),
        "title": item.get("desc", ""),
        "author": (item.get("author") or {}).get("nickname"),
        "author_id": (item.get("author") or {}).get("uid"),
        "duration_ms": item.get("duration"),
        "video": {
            "playwm_url": ((item.get("video") or {}).get("play_addr") or {}).get("url_list", [None])[0],
            "play_url": (((item.get("video") or {}).get("play_addr2") or {}).get("url_list") or [None])[0],
            "cover_url": (((item.get("video") or {}).get("cover") or {}).get("url_list") or [None])[0],
            "width": (item.get("video") or {}).get("width"),
            "height": (item.get("video") or {}).get("height"),
            "ratio": (item.get("video") or {}).get("ratio"),
        },
        "stats": {
            "likes": (item.get("statistics") or {}).get("digg_count"),
            "comments": (item.get("statistics") or {}).get("comment_count"),
            "collects": (item.get("statistics") or {}).get("collect_count"),
            "shares": (item.get("statistics") or {}).get("share_count"),
        },
        "hashtags": [t.get("title_name", "") for t in (item.get("text_extra") or [])],
        "create_time": item.get("create_time"),
    }

    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    (out / "iesdouyin_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # v0: 仅 metadata，不下载视频本体（避免 watermark 处理 + 第三方 ffmpeg 复杂度）
    return DownloadResult(
        ok=True,
        backend="iesdouyin",
        output_dir=str(out),
        files=[str((out / "iesdouyin_metadata.json").resolve())],
        metadata=metadata,
        error=None,
    )


def download(
    url: str,
    *,
    output_dir: str,
    mode: str,
    backend: str = "yt_dlp",
    yt_dlp_bin: str = "yt-dlp",
    cookies_from_browser: str | None = "chrome",
    ms_token: str | None = None,
) -> DownloadResult:
    """Top-level douyin download dispatcher."""
    if backend == "yt_dlp":
        return download_with_yt_dlp(
            url,
            output_dir=output_dir,
            mode=mode,
            yt_dlp_bin=yt_dlp_bin,
            cookies_from_browser=cookies_from_browser,
        )
    if backend == "iesdouyin":
        return download_with_iesdouyin(
            url,
            output_dir=output_dir,
            ms_token=ms_token,
        )
    if backend == "auto":
        # yt_dlp first; if it fails, fallback to iesdouyin (metadata only)
        yt_result = download_with_yt_dlp(
            url,
            output_dir=output_dir,
            mode=mode,
            yt_dlp_bin=yt_dlp_bin,
            cookies_from_browser=cookies_from_browser,
        )
        if yt_result.ok:
            return yt_result
        return download_with_iesdouyin(url, output_dir=output_dir, ms_token=ms_token)

    return DownloadResult(
        False, backend, output_dir, [], None,
        f"unknown_backend:{backend}",
    )