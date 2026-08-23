"""phone-harness runtime adapter for zhenji.

Zhenji vendors a complete, pinned phone-harness snapshot under
``vendor/phone-harness``. Resolution order is:

1. ``PHONE_HARNESS_BIN`` when explicitly supplied by the user;
2. the repository's vendored launcher;
3. ``phone-harness`` found on ``$PATH``.

This keeps a checkout self-contained while still allowing an operator to
substitute another phone-harness build deliberately.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

__version__ = "5.2.1"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VENDOR_ROOT = _REPO_ROOT / "vendor" / "phone-harness"
_VENDOR_BIN = _VENDOR_ROOT / "phone-harness"


def _resolve_phone_harness() -> str | None:
    explicit = os.environ.get("PHONE_HARNESS_BIN")
    if explicit:
        return explicit
    if _VENDOR_BIN.is_file():
        return str(_VENDOR_BIN)
    return shutil.which("phone-harness")


PHONE_HARNESS_BIN = _resolve_phone_harness()


def require_phone_harness() -> str:
    """Return the launcher used by zhenji or raise an actionable error."""
    global PHONE_HARNESS_BIN
    PHONE_HARNESS_BIN = _resolve_phone_harness()
    if PHONE_HARNESS_BIN is None:
        raise FileNotFoundError(
            "phone-harness runtime not found. The normal zhenji checkout should "
            "contain vendor/phone-harness/phone-harness. Re-clone the repository "
            "or set PHONE_HARNESS_BIN=/path/to/phone-harness explicitly."
        )
    return PHONE_HARNESS_BIN


def run_heredoc(script: str, *, timeout: float | None = None) -> subprocess.CompletedProcess:
    """Execute a phone-harness script with its standard helper namespace."""
    bin_ = require_phone_harness()
    return subprocess.run(
        [bin_],
        input=script,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def is_available() -> bool:
    return _resolve_phone_harness() is not None


def connection_state() -> str:
    p = run_heredoc("print(connection_state())\n", timeout=15)
    if p.returncode != 0:
        raise RuntimeError(f"connection_state failed: {p.stderr.strip()}")
    return p.stdout.strip()


def screen_info() -> dict[str, Any]:
    p = run_heredoc(
        "import json; print(json.dumps(screen_info(), ensure_ascii=False))\n",
        timeout=15,
    )
    if p.returncode != 0:
        raise RuntimeError(f"screen_info failed: {p.stderr.strip()}")
    try:
        return json.loads(p.stdout.strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"screen_info returned invalid JSON: {p.stdout[:200]!r}") from exc


def screenshot(path: str) -> str:
    p = run_heredoc(f"screenshot({path!r})\n", timeout=30)
    if p.returncode != 0:
        raise RuntimeError(f"screenshot failed: {p.stderr.strip()}")
    return str(Path(path).resolve())


def tap(x: float, y: float, *, sleep_after: float = 0.0) -> None:
    lines = [f"tap({x}, {y})"]
    if sleep_after > 0:
        lines.append(f"time.sleep({sleep_after})")
    p = run_heredoc("import time\n" + "\n".join(lines) + "\n", timeout=15)
    if p.returncode != 0:
        raise RuntimeError(f"tap({x},{y}) failed: {p.stderr.strip()}")


def swipe(x1: float, y1: float, x2: float, y2: float, duration: float = 0.4) -> None:
    p = run_heredoc(
        f"swipe({x1}, {y1}, {x2}, {y2}, duration={duration})\n",
        timeout=15,
    )
    if p.returncode != 0:
        raise RuntimeError(f"swipe failed: {p.stderr.strip()}")


def long_press(x: float, y: float, duration: float = 1.0) -> None:
    p = run_heredoc(
        f"long_press({x}, {y}, duration={duration})\n",
        timeout=30,
    )
    if p.returncode != 0:
        raise RuntimeError(f"long_press failed: {p.stderr.strip()}")


def activate_mirror() -> None:
    subprocess.run(
        ["osascript", "-e", 'tell application "iPhone Mirroring" to activate'],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def clipboard_set(text: str) -> None:
    p = subprocess.run(["pbcopy"], input=text, text=True, capture_output=True, timeout=5)
    if p.returncode != 0:
        raise RuntimeError(f"pbcopy failed: {p.stderr}")


def clipboard_read() -> str:
    p = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
    if p.returncode != 0:
        raise RuntimeError(f"pbpaste failed: {p.stderr}")
    return p.stdout


def doctor() -> dict[str, Any]:
    """Return zhenji + phone-harness health without hiding failures."""
    bin_ = require_phone_harness()
    try:
        cs = connection_state()
    except Exception as exc:
        cs = f"error: {exc}"
    try:
        si = screen_info()
    except Exception as exc:
        si = {"error": str(exc)}
    return {
        "phone_harness_bin": bin_,
        "phone_harness_source": "vendored" if Path(bin_).resolve() == _VENDOR_BIN.resolve() else "override_or_path",
        "phone_harness_vendor_commit": "47f37a6dd5baae9f10f16e21e50a6898ee42cd22",
        "connection_state": cs,
        "screen_info": si,
        "zhenji_version": __version__,
        "is_strict_mode": bool(int(os.environ.get("PHONE_HARNESS_STRICT", "0"))),
    }
