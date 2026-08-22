"""Persistent SQLite media job queue for Zhenji V5."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import sqlite3
import time
import uuid


SCHEMA = """
CREATE TABLE IF NOT EXISTS media_jobs (
    job_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    post_key TEXT NOT NULL,
    source_url TEXT NOT NULL,
    mode TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    state TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    backend TEXT,
    output_dir TEXT,
    metadata_json TEXT,
    error TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    claimed_at REAL,
    finished_at REAL,
    UNIQUE(platform, post_key, source_url, mode)
);
CREATE INDEX IF NOT EXISTS idx_media_jobs_claim
ON media_jobs(state, priority, created_at);
"""


@dataclass
class MediaJob:
    job_id: str
    platform: str
    post_key: str
    source_url: str
    mode: str
    priority: int
    state: str
    attempts: int
    backend: str | None
    output_dir: str | None
    metadata: dict[str, Any] | None
    error: str | None


class MediaQueue:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        return db

    def enqueue(
        self,
        *,
        platform: str,
        post_key: str,
        source_url: str,
        mode: str,
        priority: int = 100,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        now = time.time()
        with self._connect() as db:
            row = db.execute(
                """SELECT job_id FROM media_jobs
                   WHERE platform=? AND post_key=? AND source_url=? AND mode=?""",
                (platform, post_key, source_url, mode),
            ).fetchone()
            if row:
                return str(row["job_id"])

            job_id = uuid.uuid4().hex
            db.execute(
                """INSERT INTO media_jobs
                   (job_id, platform, post_key, source_url, mode, priority,
                    metadata_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job_id, platform, post_key, source_url, mode, priority,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now, now,
                ),
            )
            return job_id

    def claim_next(self) -> MediaJob | None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT * FROM media_jobs
                   WHERE state IN ('queued','retry')
                   ORDER BY priority ASC, created_at ASC
                   LIMIT 1"""
            ).fetchone()
            if not row:
                db.execute("COMMIT")
                return None

            now = time.time()
            db.execute(
                """UPDATE media_jobs
                   SET state='downloading', attempts=attempts+1,
                       claimed_at=?, updated_at=?
                   WHERE job_id=?""",
                (now, now, row["job_id"]),
            )
            db.execute("COMMIT")
            return self.get(str(row["job_id"]))

    def get(self, job_id: str) -> MediaJob | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM media_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def mark(
        self,
        job_id: str,
        state: str,
        *,
        backend: str | None = None,
        output_dir: str | None = None,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        now = time.time()
        finished = now if state in {"done", "failed"} else None
        with self._connect() as db:
            db.execute(
                """UPDATE media_jobs
                   SET state=?, backend=COALESCE(?, backend),
                       output_dir=COALESCE(?, output_dir),
                       metadata_json=COALESCE(?, metadata_json),
                       error=?, updated_at=?,
                       finished_at=COALESCE(?, finished_at)
                   WHERE job_id=?""",
                (
                    state,
                    backend,
                    output_dir,
                    json.dumps(metadata, ensure_ascii=False)
                    if metadata is not None else None,
                    error,
                    now,
                    finished,
                    job_id,
                ),
            )

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> MediaJob:
        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else None
        return MediaJob(
            job_id=row["job_id"],
            platform=row["platform"],
            post_key=row["post_key"],
            source_url=row["source_url"],
            mode=row["mode"],
            priority=int(row["priority"]),
            state=row["state"],
            attempts=int(row["attempts"]),
            backend=row["backend"],
            output_dir=row["output_dir"],
            metadata=meta,
            error=row["error"],
        )
