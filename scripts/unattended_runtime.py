"""Unattended supervisor wiring for zhenji V4."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from keepalive import InputActivity, KeepaliveManager


@dataclass
class RuntimeCounters:
    watchdog_polls: int = 0
    connection_recoveries: int = 0
    keepalive_actions: int = 0
    keepalive_failures: int = 0
    unexpected_idle_pauses: int = 0


class UnattendedSupervisor:
    """Coordinates Watchdog, real-input liveness, and batch worker state."""

    def __init__(
        self,
        *,
        watchdog,
        keepalive: KeepaliveManager,
        current_page_state_fn: Callable[[], str],
        invalidate_runtime_caches_fn: Callable[[], None],
        checkpoint_fn: Callable[[], None],
    ) -> None:
        self.watchdog = watchdog
        self.keepalive = keepalive
        self.activity: InputActivity = keepalive.activity
        self.current_page_state_fn = current_page_state_fn
        self.invalidate_runtime_caches_fn = invalidate_runtime_caches_fn
        self.checkpoint_fn = checkpoint_fn
        self.counters = RuntimeCounters()

    def start(self) -> None:
        health = self.watchdog.preflight()
        if health.input_frozen:
            raise RuntimeError(f"preflight failed: {health.reason}")
        self.watchdog.start(skip_preflight=True)

    def before_business_input(self) -> None:
        self.watchdog.guard.assert_input_allowed()

    def after_business_input(self) -> None:
        self.activity.record_business_input()

    def idle_tick(self) -> str:
        """Run during real waits; does not count observation as activity."""
        self.watchdog.guard.assert_input_allowed()
        page = self.current_page_state_fn()
        try:
            result = self.keepalive.maybe_keepalive(page)
            if result.startswith("executed:"):
                self.counters.keepalive_actions += 1
            return result
        except Exception:
            self.counters.keepalive_failures += 1
            self.checkpoint_fn()
            raise

    def after_recovery(self) -> None:
        # Never reuse mirror offsets, card coordinates, OCR observations, or scroll position.
        self.invalidate_runtime_caches_fn()
        self.counters.connection_recoveries += 1
