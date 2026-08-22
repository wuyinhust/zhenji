"""Read macOS clipboard and extract social-media share URLs."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable
import re
import subprocess
import time

from platform_router import route_url


URL_RE = re.compile(r"https?://[^\s<>\"'，。；、）)\]]+")


def clipboard_text() -> str:
    p = subprocess.run(
        ["pbpaste"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(f"pbpaste failed: {p.stderr.strip()}")
    return p.stdout


def fingerprint(text: str) -> str:
    return sha256(text.encode("utf-8", errors="replace")).hexdigest()


def extract_urls(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in URL_RE.findall(text or ""):
        url = raw.rstrip(".,;:!?，。；：！？")
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def extract_platform_url(text: str, expected_platform: str | None = None) -> str | None:
    for url in extract_urls(text):
        route = route_url(url)
        if route.key == "unknown":
            continue
        if expected_platform and route.key != expected_platform:
            continue
        return url
    return None


@dataclass
class ClipboardWaitResult:
    changed: bool
    text: str
    url: str | None
    elapsed_seconds: float


def wait_for_new_share_url(
    *,
    previous_text: str,
    expected_platform: str | None = "xhs",
    read_fn: Callable[[], str] = clipboard_text,
    timeout_seconds: float = 8.0,
    poll_interval_seconds: float = 0.25,
) -> ClipboardWaitResult:
    old_fp = fingerprint(previous_text)
    start = time.monotonic()
    latest = previous_text

    while time.monotonic() - start < timeout_seconds:
        latest = read_fn()
        changed = fingerprint(latest) != old_fp
        if changed:
            url = extract_platform_url(latest, expected_platform)
            if url:
                return ClipboardWaitResult(
                    True, latest, url, time.monotonic() - start
                )
        time.sleep(poll_interval_seconds)

    return ClipboardWaitResult(
        fingerprint(latest) != old_fp,
        latest,
        extract_platform_url(latest, expected_platform),
        time.monotonic() - start,
    )
