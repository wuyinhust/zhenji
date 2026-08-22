"""Idle timeout calibration for zhenji V4.

This module measures the actual iPhone Mirroring idle-pause behavior of the
current Mac/iPhone/runtime combination. It never treats screenshots or status
polls as activity. Calibration deliberately sends no HID input until a pause is
observed, then delegates recovery to the caller.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable
import json, time


@dataclass(frozen=True)
class EnvironmentKey:
    macos_version: str
    ios_version: str
    phone_harness_version: str = "unknown"
    mirror_build: str = "unknown"

    @property
    def key(self) -> str:
        return "|".join([
            self.macos_version,
            self.ios_version,
            self.phone_harness_version,
            self.mirror_build,
        ])


@dataclass
class IdleCalibration:
    environment_key: str
    samples_seconds: list[float]
    minimum_seconds: float
    trigger_ratio: float
    keepalive_after_seconds: float
    measured_at_epoch: float

    @classmethod
    def from_samples(
        cls,
        environment_key: str,
        samples_seconds: list[float],
        trigger_ratio: float = 0.80,
    ) -> "IdleCalibration":
        if not samples_seconds:
            raise ValueError("at least one idle-timeout sample is required")
        if not 0.1 <= trigger_ratio < 1.0:
            raise ValueError("trigger_ratio must be >=0.1 and <1.0")
        minimum = min(samples_seconds)
        return cls(
            environment_key=environment_key,
            samples_seconds=list(samples_seconds),
            minimum_seconds=minimum,
            trigger_ratio=trigger_ratio,
            keepalive_after_seconds=minimum * trigger_ratio,
            measured_at_epoch=time.time(),
        )


class CalibrationStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load_all(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, env: EnvironmentKey) -> IdleCalibration | None:
        raw = self.load_all().get(env.key)
        return IdleCalibration(**raw) if raw else None

    def put(self, result: IdleCalibration) -> None:
        payload = self.load_all()
        payload[result.environment_key] = asdict(result)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)


def measure_one_idle_timeout(
    *,
    is_ready_fn: Callable[[], bool],
    is_paused_fn: Callable[[], bool],
    poll_seconds: float = 5.0,
    max_wait_seconds: float = 3600.0,
    now_fn: Callable[[], float] = time.monotonic,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> float:
    """Measure one idle timeout without sending any HID input."""
    if not is_ready_fn():
        raise RuntimeError("calibration requires a ready mirroring session")
    started = now_fn()
    while True:
        if is_paused_fn():
            return max(0.0, now_fn() - started)
        if now_fn() - started >= max_wait_seconds:
            raise TimeoutError("idle pause was not observed within max_wait_seconds")
        sleep_fn(poll_seconds)


def calibrate_idle_timeout(
    *,
    environment: EnvironmentKey,
    is_ready_fn: Callable[[], bool],
    is_paused_fn: Callable[[], bool],
    recover_fn: Callable[[], bool],
    samples: int = 3,
    poll_seconds: float = 5.0,
    trigger_ratio: float = 0.80,
    max_wait_seconds: float = 3600.0,
) -> IdleCalibration:
    if samples < 1:
        raise ValueError("samples must be >= 1")
    observed: list[float] = []
    for index in range(samples):
        observed.append(measure_one_idle_timeout(
            is_ready_fn=is_ready_fn,
            is_paused_fn=is_paused_fn,
            poll_seconds=poll_seconds,
            max_wait_seconds=max_wait_seconds,
        ))
        if index < samples - 1:
            if not recover_fn():
                raise RuntimeError("could not recover mirroring between calibration samples")
            if not is_ready_fn():
                raise RuntimeError("mirroring did not return to ready after recovery")
    return IdleCalibration.from_samples(environment.key, observed, trigger_ratio)
