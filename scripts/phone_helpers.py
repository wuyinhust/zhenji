"""High-level, read-only phone helpers for Zhenji.

The concrete adapter can wrap phone-harness or another real-device controller.
The helpers deliberately operate on semantic actions and validate page changes.

**v5.1 update**: phone-harness 已是 zhenji bundled 依赖，不再单独 install。
原 v5 中的强约束（必须 idle calibration / 必须 input guard / 必须 Safe Keepalive 验证）
改为"建议性"行为——详见 SKILL.md §68。
""""
from __future__ import annotations"
from typing import Any, Callable, Protocol
from runtime_cache import Observation, ObservationSession


class InputGuardLike(Protocol):
    def assert_input_allowed(self) -> None: ...


class InputActivityLike(Protocol):
    def record_business_input(self) -> None: ...


class PhoneAdapter(Protocol):
    def screenshot(self) -> Any: ...
    def ocr(self, screenshot: Any) -> list[dict[str, Any]]: ...
    def tap_text(self, text: str) -> None: ...
    def tap(self, x: float, y: float) -> None: ...
    def scroll(self, direction: str = "down") -> None: ...
    def back(self) -> None: ...
    def wait_stable(self) -> None: ...


def observe_once(
    adapter: PhoneAdapter,
    session: ObservationSession,
    classify_fn: Callable[[list[dict[str, Any]]], str] | None = None,
) -> Observation:
    return session.observe(adapter.screenshot, adapter.ocr, classify_fn)


def do_viewport_action(
    session: ObservationSession,
    reason: str,
    action: Callable[..., Any],
    *args: Any,
    wait_fn: Callable[[], Any] | None = None,
    guard: InputGuardLike | None = None,
    activity: InputActivityLike | None = None,
) -> Any:
    if guard is not None:
        guard.assert_input_allowed()
    result = action(*args)
    if activity is not None:
        activity.record_business_input()
    if wait_fn is not None:
        wait_fn()
    session.mark_dirty(reason)
    return result


def open_search_verified(
    adapter: PhoneAdapter,
    session: ObservationSession,
    classify_fn: Callable[[list[dict[str, Any]]], str],
    expected_pages: set[str] | None = None,
    guard: InputGuardLike | None = None,
    activity: InputActivityLike | None = None,
) -> Observation:
    expected_pages = expected_pages or {"search", "search_results"}
    do_viewport_action(session, "open_search", adapter.tap_text, "搜索", wait_fn=adapter.wait_stable, guard=guard, activity=activity)
    obs = observe_once(adapter, session, classify_fn)
    if obs.page_type not in expected_pages:
        raise RuntimeError(f"search navigation verification failed: {obs.page_type}")
    return obs


def return_verified(
    adapter: PhoneAdapter,
    session: ObservationSession,
    classify_fn: Callable[[list[dict[str, Any]]], str],
    expected_page: str,
    guard: InputGuardLike | None = None,
    activity: InputActivityLike | None = None,
) -> Observation:
    do_viewport_action(session, "back", adapter.back, wait_fn=adapter.wait_stable, guard=guard, activity=activity)
    obs = observe_once(adapter, session, classify_fn)
    if obs.page_type != expected_page:
        raise RuntimeError(f"return verification failed: expected={expected_page} actual={obs.page_type}")
    return obs


def scan_visible_cards(
    obs: Observation,
    parser: Callable[[Observation], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Parse every visible card from one Observation; must not trigger new OCR."""
    return parser(obs)


def open_card_verified(
    adapter: PhoneAdapter,
    session: ObservationSession,
    classify_fn: Callable[[list[dict[str, Any]]], str],
    x: float,
    y: float,
    expected_page: str = "post_detail",
    guard: InputGuardLike | None = None,
    activity: InputActivityLike | None = None,
) -> Observation:
    do_viewport_action(session, "open_card", adapter.tap, x, y, wait_fn=adapter.wait_stable, guard=guard, activity=activity)
    obs = observe_once(adapter, session, classify_fn)
    if obs.page_type != expected_page:
        raise RuntimeError(f"open card verification failed: expected={expected_page} actual={obs.page_type}")
    return obs
