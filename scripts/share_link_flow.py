"""Verified share-link harvesting flow.

Phone actions are injected callbacks so the flow can use phone-harness without
hard-coding screen coordinates into this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from clipboard_link import clipboard_text, wait_for_new_share_url
from platform_router import route_url


@dataclass
class ShareLinkResult:
    ok: bool
    url: str | None
    raw_clipboard_text: str | None
    attempts: int
    metadata: dict[str, Any] | None
    error: str | None


def weak_match(expected: dict[str, Any] | None, metadata: dict[str, Any]) -> bool:
    """Reject clear mismatches; do not over-reject small text differences."""
    if not expected:
        return True

    expected_type = (expected.get("note_type") or "").lower()
    if expected_type == "video":
        # yt-dlp metadata for a resolved video normally has duration/formats.
        if not metadata.get("duration") and not metadata.get("formats"):
            return False

    expected_id = str(expected.get("note_id") or "").strip()
    resolved_id = str(metadata.get("id") or "").strip()
    if expected_id and resolved_id and expected_id != resolved_id:
        return False

    # Title/author are weak hints only.
    return True


def harvest_share_link(
    *,
    open_share_action: Callable[[], None],
    copy_link_action: Callable[[], None],
    probe_fn: Callable[[str], dict[str, Any]] | None = None,
    expected_platform: str = "xhs",
    expected_post_hint: dict[str, Any] | None = None,
    max_copy_retries: int = 1,
    clipboard_read_fn: Callable[[], str] = clipboard_text,
    timeout_seconds: float = 8.0,
    poll_interval_seconds: float = 0.25,
) -> ShareLinkResult:
    last_error = "unknown"

    for attempt in range(1, max_copy_retries + 2):
        before = clipboard_read_fn()

        open_share_action()
        copy_link_action()

        waited = wait_for_new_share_url(
            previous_text=before,
            expected_platform=expected_platform,
            read_fn=clipboard_read_fn,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

        if not waited.changed:
            last_error = "clipboard_unchanged"
            continue
        if not waited.url:
            last_error = "no_supported_url_in_clipboard"
            continue

        route = route_url(waited.url)
        if route.key != expected_platform:
            last_error = f"wrong_platform:{route.key}"
            continue

        metadata = None
        if probe_fn is not None:
            try:
                metadata = probe_fn(waited.url)
            except Exception as exc:
                last_error = f"probe_failed:{type(exc).__name__}:{exc}"
                continue
            if not weak_match(expected_post_hint, metadata):
                last_error = "resolved_post_mismatch"
                continue

        return ShareLinkResult(
            ok=True,
            url=waited.url,
            raw_clipboard_text=waited.text,
            attempts=attempt,
            metadata=metadata,
            error=None,
        )

    return ShareLinkResult(
        ok=False,
        url=None,
        raw_clipboard_text=None,
        attempts=max_copy_retries + 1,
        metadata=None,
        error=last_error,
    )
