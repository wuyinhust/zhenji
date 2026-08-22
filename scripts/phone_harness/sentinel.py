"""剪贴板哨兵协议 — V5 Link Harvester 的关键防护。

每次分享 → Copy link 前，先 pbcopy 写一个 SENTINEL_BEFORE_COPY_<ts>；
点完 Copy link 后读 pbpaste 与哨值不同才算真拷贝到了新内容。

v5.1 bundled：随 phone-harness 子包一起提供，仍是 v5 Link Harvester 的关键防护。
"""
from __future__ import annotations

import time
import subprocess
from typing import Optional

SENTINEL_PREFIX = "SENTINEL_BEFORE_COPY_"


def write_sentinel() -> str:
    """Write a fresh sentinel to macOS clipboard. Returns the sentinel string."""
    sentinel = f"{SENTINEL_PREFIX}{int(time.time())}"
    p = subprocess.run(["pbcopy"], input=sentinel, text=True, capture_output=True, timeout=5)
    if p.returncode != 0:
        raise RuntimeError(f"pbcopy failed: {p.stderr}")
    return sentinel


def read_clipboard() -> str:
    """Read current macOS clipboard."""
    p = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
    if p.returncode != 0:
        raise RuntimeError(f"pbpaste failed: {p.stderr}")
    return p.stdout


def changed_after(baseline: str, *, settle_seconds: float = 0.3, retries: int = 3) -> Optional[str]:
    """Return new clipboard content if it differs from baseline, else None.

    Retries `retries` times with `settle_seconds` between polls.
    """
    deadline = time.time() + settle_seconds * retries
    for _ in range(retries):
        cur = read_clipboard()
        if cur != baseline:
            return cur
        time.sleep(settle_seconds)
        if time.time() > deadline:
            break
    return None