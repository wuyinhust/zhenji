"""State-aware real-input keepalive for zhenji V4.

Only verified, real HID actions count as keepalive. Read-only observation such
as screenshot(), connection_state(), screen_info(), macOS caffeinate, or
activate() never updates the real-input clock.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any
import time


@dataclass
class InputActivity:
    last_real_input_at: float | None = None
    real_input_count: int = 0
    keepalive_count: int = 0

    def record_business_input(self, now: float | None = None) -> None:
        self.last_real_input_at = time.monotonic() if now is None else now
        self.real_input_count += 1

    def record_keepalive_input(self, now: float | None = None) -> None:
        self.last_real_input_at = time.monotonic() if now is None else now
        self.real_input_count += 1
        self.keepalive_count += 1


@dataclass
class SafeKeepaliveAction:
    name: str
    page_state: str
    action: Callable[[], Any]
    verify_page_fn: Callable[[], str]
    wait_stable_fn: Callable[[], Any] | None = None
    side_effect: str = "none"

    def execute_verified(self) -> None:
        before = self.verify_page_fn()
        if before != self.page_state:
            raise RuntimeError(
                f"keepalive precondition failed: expected={self.page_state} actual={before}"
            )
        self.action()
        if self.wait_stable_fn:
            self.wait_stable_fn()
        after = self.verify_page_fn()
        if after != self.page_state:
            raise RuntimeError(
                f"keepalive changed page: expected={self.page_state} actual={after}"
            )


class KeepaliveRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, list[SafeKeepaliveAction]] = {}

    def register(self, action: SafeKeepaliveAction) -> None:
        if action.side_effect != "none":
            raise ValueError("keepalive action must declare side_effect='none'")
        self._actions.setdefault(action.page_state, []).append(action)

    def get(self, page_state: str) -> SafeKeepaliveAction | None:
        actions = self._actions.get(page_state, [])
        return actions[0] if actions else None


class KeepaliveManager:
    def __init__(
        self,
        *,
        activity: InputActivity,
        registry: KeepaliveRegistry,
        keepalive_after_seconds: float,
        forbidden_pages: set[str] | None = None,
        now_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.activity = activity
        self.registry = registry
        self.keepalive_after_seconds = keepalive_after_seconds
        self.forbidden_pages = forbidden_pages or {
            "LOGIN_REQUIRED", "DEVICE_UNLOCK", "PASSWORD",
            "SECURITY_CHALLENGE", "UNKNOWN_UNSAFE", "MIRROR_RECOVERY",
        }
        self.now_fn = now_fn

    def seconds_since_real_input(self) -> float:
        if self.activity.last_real_input_at is None:
            return float("inf")
        return max(0.0, self.now_fn() - self.activity.last_real_input_at)

    def due(self) -> bool:
        return self.seconds_since_real_input() >= self.keepalive_after_seconds

    def maybe_keepalive(self, current_page_state: str) -> str:
        if not self.due():
            return "not-due"
        if current_page_state in self.forbidden_pages:
            return "forbidden-page"
        candidate = self.registry.get(current_page_state)
        if candidate is None:
            return "no-verified-action"
        candidate.execute_verified()
        self.activity.record_keepalive_input(self.now_fn())
        return f"executed:{candidate.name}"
