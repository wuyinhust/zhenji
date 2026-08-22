"""Simple persistent media worker.

The production Skill can run multiple instances. This worker processes XHS jobs
from SQLite one-by-one; analysis/storage layers consume generated manifests.
"""
from __future__ import annotations

import argparse
import time

from media_queue import MediaQueue
from media_pipeline import process_xhs_url


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default="./runtime/media-jobs.sqlite3")
    ap.add_argument("--output", default="./runtime/media")
    ap.add_argument("--backend", default="auto")
    ap.add_argument("--smile7up-script", default="")
    ap.add_argument("--cookies-browser", default="chrome")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    q = MediaQueue(args.queue)

    while True:
        job = q.claim_next()
        if job is None:
            if args.once:
                return 0
            time.sleep(1.0)
            continue

        if job.platform != "xhs":
            q.mark(job.job_id, "failed", error=f"adapter_not_implemented:{job.platform}")
            continue

        try:
            result = process_xhs_url(
                url=job.source_url,
                post_key=job.post_key,
                mode=job.mode,
                output_root=args.output,
                downloader_backend=args.backend,
                smile7up_script=args.smile7up_script or None,
                cookies_from_browser=args.cookies_browser or None,
            )
            if result.ok:
                q.mark(
                    job.job_id,
                    "done",
                    backend=result.backend,
                    output_dir=args.output,
                    metadata={
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
                q.mark(job.job_id, state, backend=result.backend, error=result.error)
        except Exception as exc:
            state = "retry" if job.attempts < 3 else "failed"
            q.mark(
                job.job_id,
                state,
                error=f"{type(exc).__name__}:{exc}",
            )

        if args.once:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
