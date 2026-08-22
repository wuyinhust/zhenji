"""Batch write planning for Zhenji.

The module creates ordered mutation plans. Actual Google Sheets connector calls
are performed by the agent/runtime that has credentials.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json, time

PHASES = ("facts", "features", "knowledge", "cursor")


@dataclass(frozen=True)
class Mutation:
    phase: str
    sheet: str
    op: str          # append | upsert | update
    key_field: str | None
    key_value: str | None
    values: dict[str, Any]


class RunBuffer:
    def __init__(self, run_id: str, staging_dir: str | Path | None = None) -> None:
        self.run_id = run_id
        self.ops: list[Mutation] = []
        self.created_at = time.time()
        self.staging_dir = Path(staging_dir) if staging_dir else None

    def add(self, mutation: Mutation) -> None:
        if mutation.phase not in PHASES:
            raise ValueError(f"invalid phase: {mutation.phase}")
        self.ops.append(mutation)

    def upsert(self, phase: str, sheet: str, key_field: str, key_value: str, values: dict[str, Any]) -> None:
        self.add(Mutation(phase, sheet, "upsert", key_field, key_value, values))

    def append(self, phase: str, sheet: str, values: dict[str, Any]) -> None:
        self.add(Mutation(phase, sheet, "append", None, None, values))

    def compact(self) -> list[Mutation]:
        """Coalesce repeated upserts for the same key, preserving last values."""
        append_ops: list[Mutation] = []
        upserts: dict[tuple[str, str, str | None, str | None], Mutation] = {}
        for m in self.ops:
            if m.op == "upsert":
                k = (m.phase, m.sheet, m.key_field, m.key_value)
                if k in upserts:
                    merged = dict(upserts[k].values)
                    merged.update(m.values)
                    upserts[k] = Mutation(m.phase, m.sheet, m.op, m.key_field, m.key_value, merged)
                else:
                    upserts[k] = m
            else:
                append_ops.append(m)
        combined = append_ops + list(upserts.values())
        phase_rank = {p: i for i, p in enumerate(PHASES)}
        return sorted(combined, key=lambda m: phase_rank[m.phase])

    def plan(self) -> dict[str, list[dict[str, Any]]]:
        out = {p: [] for p in PHASES}
        for m in self.compact():
            out[m.phase].append(asdict(m))
        return out

    def stage(self) -> Path | None:
        if self.staging_dir is None:
            return None
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        path = self.staging_dir / f"{self.run_id}.json"
        payload = {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "plan": self.plan(),
            "cursor_committed": False,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def should_flush(self, threshold: int = 30) -> bool:
        return len(self.ops) >= threshold
