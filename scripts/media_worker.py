"""Generic media worker (V5.1.2+).

不再 hardcode `if job.platform != "xhs"`。从 media_adapters.ADAPTERS 取 platform key。
未注册 platform → failed:adapter_not_registered。
可重复入队（attempts >= 3 才转 failed）。
"""
from __future__ import annotations

import argparse
import logging
import time

from media_queue import MediaQueue
from media_pipeline import process_media_url
from media_adapters import get as get_adapter

logger = logging.getLogger(__name__)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default="./runtime/media-jobs.sqlite3")
    ap.add_argument("--output", default="./runtime/media")
    ap.add_argument("--backend", default="auto")
    ap.add_argument("--cookies-browser", default="chrome")
    ap.add_argument("--yt-dlp-bin", default="yt-dlp")
    ap.add_argument("--whisper-model", default="small")
    ap.add_argument("--once", action="store_true", help="Process one job then exit")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    q = MediaQueue(args.queue)

    while True:
        job = q.claim_next()
        if job is None:
            if args.once:
                return 0
            time.sleep(1.0)
            continue

        # 平台 registry 校验
        adapter = get_adapter(job.platform)
        if adapter is None:
            q.mark(
                job.job_id, "failed",
                error=f"adapter_not_registered:{job.platform}",
            )
            if args.once:
                return 0
            continue

        try:
            result = process_media_url(
                platform=job.platform,
                url=job.source_url,
                post_key=job.post_key,
                mode=job.mode,
                output_root=args.output,
                downloader_backend=args.backend,
                yt_dlp_bin=args.yt_dlp_bin,
                cookies_from_browser=args.cookies_browser or None,
                whisper_model=args.whisper_model,
            )

            # P0 (v5.2): 用 acceptable_for_mode 做档位强校验，而非模糊的 result.ok。
            # acceptable=True 表示 fetch 结果满足该 job.mode 的最低要求
            # （浮光可接受 metadata_only；掠影/听澜/观澜必须 media_ready）。
            if result.acceptable:
                q.mark(
                    job.job_id,
                    "done",
                    backend=result.backend,
                    output_dir=args.output,
                    metadata={
                        "fetch_status": result.fetch_status,
                        "platform": result.platform,
                        "video_path": result.video_path,
                        "audio_path": result.audio_path,
                        "keyframes": result.keyframes,
                        "scene_frames": result.scene_frames,
                        "transcript_txt": result.transcript_txt,
                        "transcript_json": result.transcript_json,
                    },
                )
            else:
                state = "retry" if job.attempts < 3 else "failed"
                q.mark(
                    job.job_id, state,
                    backend=result.backend,
                    error=result.error or f"not_acceptable_for_mode:{job.mode}",
                )
        except Exception as exc:
            state = "retry" if job.attempts < 3 else "failed"
            q.mark(
                job.job_id, state,
                error=f"{type(exc).__name__}:{exc}",
            )
            logger.exception("job %s crashed", job.job_id)

        if args.once:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())

