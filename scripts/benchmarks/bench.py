"""Benchmark runner for zhenji four-tier video modes.

Modes:
  fuguang  浮光 — phone-harness 陪看抽帧，无本地副本
  lueying  掠影 — yt-dlp 480p + 8 帧均匀关键帧
  tinglan  听澜 — yt-dlp 720p + faster-whisper small 转录 + 10 关键帧
  guanlan  观澜 — yt-dlp best + faster-whisper medium 转录 + scene detection + 时间轴

Usage:
  bench.py --mode fuguang --note-id <note_id> --xsec-token <tok>
  bench.py --mode lueying --note-id <note_id> --xsec-token <tok>
  bench.py --mode tinglan --note-id <note_id> --xsec-token <tok>
  bench.py --mode guanlan --note-id <note_id> --xsec-token <tok>
  bench.py --mode all     --note-id <note_id> --xsec-token <tok>

Output:
  ~/WorkBuddy/zhenji/benchmarks/<run_id>/<mode>/{video.mp4, frames/, transcript/, scenes/, manifest.json, bench_result.json}
  ~/WorkBuddy/zhenji/benchmarks/<run_id>/REPORT.md
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ZJ_SCRIPTS = Path("/Users/vuyin/.workbuddy/skills/zhenji/scripts")
sys.path.insert(0, str(ZJ_SCRIPTS))

OUT_ROOT = Path("/Users/vuyin/WorkBuddy/zhenji/benchmarks")
PYBIN = "/Users/vuyin/.workbuddy/binaries/python/envs/default/bin/python3"
PHONE_SH = "/usr/local/bin/phone-harness"  # CLI fallback path
WHISPER_MODEL_SMALL = "small"
WHISPER_MODEL_MEDIUM = "medium"

XHS_BASE = "https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source=app_share&type=video"


@dataclass
class TierResult:
    mode: str
    ok: bool
    wall_clock_seconds: float
    mp4_path: str | None
    mp4_bytes: int
    keyframes_count: int
    frames_bytes: int
    transcript_chars: int
    scenes_count: int
    error: str | None
    notes: dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


# ============================ Helpers ============================

def _run(cmd: list[str], timeout: float = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)


def _dir_size_bytes(p: Path) -> int:
    if not p.exists():
        return 0
    total = 0
    for f in p.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total


def _probe_duration(video_path: str) -> float:
    p = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", video_path], timeout=60)
    if p.returncode != 0:
        return 0.0
    try:
        return float(json.loads(p.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def build_xhs_url(note_id: str, xsec_token: str) -> str:
    return XHS_BASE.format(note_id=note_id, xsec_token=xsec_token)


# ============================ Tier 1: fuguang (浮光) ============================

def run_fuguang(
    note_id: str,
    work_dir: Path,
    *,
    sample_interval_seconds: int = 25,
    target_frame_count: int = 6,
    duration_hint_seconds: float | None = None,
) -> TierResult:
    """fuguang: 真机陪看抽帧 (V4 mirror fallback path).

    假设 iPhone 已经在该视频详情页（手动搜过 → 进账号 → 进视频）。
    """
    t0 = time.time()
    work_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    # F1: ensure video is paused first
    pause_py = (
        "import time\n"
        "tap(1436, 405)\n"   # pause at video center
        "time.sleep(0.8)\n"
        f'screenshot("{str(frames_dir / "frame_000.png")}")\n'
    )
    p = _run([PHONE_SH], input=pause_py, timeout=30)
    frames_count = 0
    if (frames_dir / "frame_000.png").exists():
        frames_count += 1

    # resume + sample N times
    sample_py_lines = [
        "import time",
        "tap(1436, 405)  # resume",
        f"time.sleep({sample_interval_seconds})",
    ]
    for i in range(1, target_frame_count):
        sample_py_lines.append(f'screenshot("{str(frames_dir / f"frame_{i:03d}.png")}")')

    sample_py = "\n".join(sample_py_lines) + "\n"
    p = _run([PHONE_SH], input=sample_py, timeout=300)
    frames_count = sum(1 for _ in frames_dir.glob("frame_*.png"))

    # F{last+1}: pause again for clean exit
    final_py = (
        "import time\n"
        "tap(1436, 405)\n"  # pause
        "time.sleep(0.4)\n"
    )
    _run([PHONE_SH], input=final_py, timeout=20)

    return TierResult(
        mode="fuguang",
        ok=frames_count > 0,
        wall_clock_seconds=time.time() - t0,
        mp4_path=None,
        mp4_bytes=0,
        keyframes_count=frames_count,
        frames_bytes=_dir_size_bytes(frames_dir),
        transcript_chars=0,
        scenes_count=0,
        error=None if frames_count > 0 else "no_frames_captured",
        notes={
            "sample_interval_seconds": sample_interval_seconds,
            "target_frame_count": target_frame_count,
            "duration_hint_seconds": duration_hint_seconds,
            "approach": "V4 mirror fallback",
            "requires_local_copy": False,
        },
    )


# ============================ Tier 2-4 share download core ============================

def _yt_dlp_download(
    note_id: str, xsec_token: str, quality: str, out_dir: Path
) -> dict:
    """Returns metadata + file list from xhs_media.download()."""
    url = build_xhs_url(note_id, xsec_token)
    out_dir.mkdir(parents=True, exist_ok=True)

    from xhs_media import download  # type: ignore
    result = download(
        url,
        output_dir=str(out_dir),
        mode={"480p": "lueying", "720p": "tinglan", "best": "guanlan"}[quality],
        backend="yt_dlp",
        yt_dlp_bin="/Users/vuyin/.workbuddy/binaries/python/envs/default/bin/yt-dlp",
        cookies_from_browser="chrome",
    )
    return {"ok": result.ok, "files": result.files, "error": result.error}


# ============================ Tier 2: lueying (掠影) ============================

def run_lueying(note_id: str, xsec_token: str, work_dir: Path) -> TierResult:
    t0 = time.time()
    work_dir.mkdir(parents=True, exist_ok=True)

    dl = _yt_dlp_download(note_id, xsec_token, "480p", work_dir)
    if not dl["ok"]:
        return TierResult(
            mode="lueying", ok=False, wall_clock_seconds=time.time() - t0,
            mp4_path=None, mp4_bytes=0, keyframes_count=0, frames_bytes=0,
            transcript_chars=0, scenes_count=0, error=dl.get("error") or "download_failed",
            notes={"quality": "480p"},
        )

    mp4 = _pick_largest_video(dl["files"])
    if not mp4:
        return TierResult(
            mode="lueying", ok=False, wall_clock_seconds=time.time() - t0,
            mp4_path=None, mp4_bytes=0, keyframes_count=0, frames_bytes=0,
            transcript_chars=0, scenes_count=0, error="no_video_file_after_download",
            notes={"quality": "480p"},
        )

    from ffmpeg_tools import extract_uniform_frames  # type: ignore
    frames = extract_uniform_frames(mp4, str(work_dir / "frames"), count=8)
    mp4_size = Path(mp4).stat().st_size if Path(mp4).exists() else 0

    return TierResult(
        mode="lueying", ok=True, wall_clock_seconds=time.time() - t0,
        mp4_path=mp4, mp4_bytes=mp4_size, keyframes_count=len(frames),
        frames_bytes=_dir_size_bytes(work_dir / "frames"),
        transcript_chars=0, scenes_count=0, error=None,
        notes={"quality": "480p", "expected_keyframes": 8},
    )


# ============================ Tier 3: tinglan (听澜) ============================

def run_tinglan(note_id: str, xsec_token: str, work_dir: Path) -> TierResult:
    t0 = time.time()
    work_dir.mkdir(parents=True, exist_ok=True)

    dl = _yt_dlp_download(note_id, xsec_token, "720p", work_dir)
    if not dl["ok"]:
        return TierResult(
            mode="tinglan", ok=False, wall_clock_seconds=time.time() - t0,
            mp4_path=None, mp4_bytes=0, keyframes_count=0, frames_bytes=0,
            transcript_chars=0, scenes_count=0, error=dl.get("error") or "download_failed",
            notes={"quality": "720p"},
        )

    mp4 = _pick_largest_video(dl["files"])
    if not mp4:
        return TierResult(
            mode="tinglan", ok=False, wall_clock_seconds=time.time() - t0,
            mp4_path=None, mp4_bytes=0, keyframes_count=0, frames_bytes=0,
            transcript_chars=0, scenes_count=0, error="no_video_file_after_download",
            notes={"quality": "720p"},
        )

    from ffmpeg_tools import extract_uniform_frames, extract_audio  # type: ignore
    from transcription import transcribe_faster_whisper, save_transcript  # type: ignore

    frames = extract_uniform_frames(mp4, str(work_dir / "frames"), count=10)
    audio_path = extract_audio(mp4, str(work_dir / "audio.mp3"))
    tr = transcribe_faster_whisper(audio_path, model_name=WHISPER_MODEL_SMALL)
    txt, js = save_transcript(tr, str(work_dir / "transcript"))

    mp4_size = Path(mp4).stat().st_size if Path(mp4).exists() else 0

    return TierResult(
        mode="tinglan", ok=True, wall_clock_seconds=time.time() - t0,
        mp4_path=mp4, mp4_bytes=mp4_size, keyframes_count=len(frames),
        frames_bytes=_dir_size_bytes(work_dir / "frames"),
        transcript_chars=len(tr.text), scenes_count=0, error=None,
        notes={"quality": "720p", "whisper_model": WHISPER_MODEL_SMALL, "expected_keyframes": 10},
    )


# ============================ Tier 4: guanlan (观澜) ============================

def run_guanlan(note_id: str, xsec_token: str, work_dir: Path) -> TierResult:
    t0 = time.time()
    work_dir.mkdir(parents=True, exist_ok=True)

    dl = _yt_dlp_download(note_id, xsec_token, "best", work_dir)
    if not dl["ok"]:
        return TierResult(
            mode="guanlan", ok=False, wall_clock_seconds=time.time() - t0,
            mp4_path=None, mp4_bytes=0, keyframes_count=0, frames_bytes=0,
            transcript_chars=0, scenes_count=0, error=dl.get("error") or "download_failed",
            notes={"quality": "best"},
        )

    mp4 = _pick_largest_video(dl["files"])
    if not mp4:
        return TierResult(
            mode="guanlan", ok=False, wall_clock_seconds=time.time() - t0,
            mp4_path=None, mp4_bytes=0, keyframes_count=0, frames_bytes=0,
            transcript_chars=0, scenes_count=0, error="no_video_file_after_download",
            notes={"quality": "best"},
        )

    from ffmpeg_tools import extract_uniform_frames, extract_scene_frames, extract_audio  # type: ignore
    from transcription import transcribe_faster_whisper, save_transcript  # type: ignore

    frames = extract_uniform_frames(mp4, str(work_dir / "keyframes"), count=24)
    scenes = extract_scene_frames(mp4, str(work_dir / "scenes"), threshold=0.35, max_frames=40)
    audio_path = extract_audio(mp4, str(work_dir / "audio.mp3"))
    tr = transcribe_faster_whisper(audio_path, model_name=WHISPER_MODEL_MEDIUM)
    txt, js = save_transcript(tr, str(work_dir / "transcript"))

    mp4_size = Path(mp4).stat().st_size if Path(mp4).exists() else 0

    return TierResult(
        mode="guanlan", ok=True, wall_clock_seconds=time.time() - t0,
        mp4_path=mp4, mp4_bytes=mp4_size, keyframes_count=len(frames),
        frames_bytes=_dir_size_bytes(work_dir / "keyframes"),
        transcript_chars=len(tr.text), scenes_count=len(scenes), error=None,
        notes={"quality": "best", "whisper_model": WHISPER_MODEL_MEDIUM,
               "expected_keyframes": 24, "max_scenes": 40},
    )


# ============================ Helpers ============================

def _pick_largest_video(files: list[str]) -> str | None:
    candidates = [f for f in files if Path(f).suffix.lower() in {".mp4", ".mov", ".m4v", ".webm", ".mkv"}]
    if not candidates:
        return None
    candidates.sort(key=lambda f: Path(f).stat().st_size if Path(f).exists() else 0)
    return candidates[-1]


# ============================ Report ============================

def write_report(run_dir: Path, note_id: str, results: dict[str, TierResult]) -> Path:
    lines = []
    lines.append(f"# 四档 benchmark · note_id={note_id}")
    lines.append("")
    lines.append(f"run_id: `{run_dir.name}`")
    lines.append(f"generated_at: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    lines.append("")
    lines.append("| 档 | wall-clock | mp4 bytes | 关键帧数 | 帧 bytes | 转录 chars | 场景数 | 状态 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for mode in ("fuguang", "lueying", "tinglan", "guanlan"):
        r = results.get(mode)
        if r is None:
            continue
        status = "✅" if r.ok else f"❌ {r.error}"
        lines.append(
            f"| {mode} | {r.wall_clock_seconds:.1f}s | {r.mp4_bytes//1024} KB | {r.keyframes_count} | "
            f"{r.frames_bytes//1024} KB | {r.transcript_chars} | {r.scenes_count} | {status} |"
        )
    lines.append("")
    lines.append("## 结论摘要")
    lines.append("")
    # pick fastest ok tier
    ok_results = [r for r in results.values() if r.ok]
    if ok_results:
        fastest = min(ok_results, key=lambda r: r.wall_clock_seconds)
        slowest = max(ok_results, key=lambda r: r.wall_clock_seconds)
        lines.append(f"- **最快**：{fastest.mode} {fastest.wall_clock_seconds:.1f}s")
        lines.append(f"- **最慢**：{slowest.mode} {slowest.wall_clock_seconds:.1f}s")
        lines.append(f"- **观澜相比听澜额外成本**：相对观澜 vs 听澜 wall-clock 差")
    lines.append("")
    lines.append("## 各档详情")
    for mode in ("fuguang", "lueying", "tinglan", "guanlan"):
        r = results.get(mode)
        if r is None:
            continue
        lines.append("")
        lines.append(f"### {mode}")
        lines.append("```json")
        lines.append(r.to_json())
        lines.append("```")
    out = run_dir / "REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# ============================ CLI ============================

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["fuguang", "lueying", "tinglan", "guanlan", "all"])
    ap.add_argument("--note-id", required=True)
    ap.add_argument("--xsec-token", required=True)
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    run_id = args.run_id or time.strftime("bench-%Y%m%d-%H%M%S")
    run_dir = OUT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    runner_map = {
        "fuguang": lambda: run_fuguang(args.note_id, run_dir / "fuguang"),
        "lueying": lambda: run_lueying(args.note_id, args.xsec_token, run_dir / "lueying"),
        "tinglan": lambda: run_tinglan(args.note_id, args.xsec_token, run_dir / "tinglan"),
        "guanlan": lambda: run_guanlan(args.note_id, args.xsec_token, run_dir / "guanlan"),
    }

    results: dict[str, TierResult] = {}
    modes = ["fuguang", "lueying", "tinglan", "guanlan"] if args.mode == "all" else [args.mode]
    for mode in modes:
        print(f"=== running {mode} ===", flush=True)
        r = runner_map[mode]()
        results[mode] = r
        (run_dir / mode / "bench_result.json").write_text(r.to_json(), encoding="utf-8")
        print(f"  ok={r.ok} wall={r.wall_clock_seconds:.1f}s frames={r.keyframes_count}", flush=True)

    report = write_report(run_dir, args.note_id, results)
    print(f"REPORT: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
