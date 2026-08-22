"""phone-harness adapter for zhenji v5.2.

准确说法（v5.1.2 修正 v5.1.1 文案）：
- phone-harness 还是外部 CLI；本子包是 zhenji 内置的 adapter / wrapper。
- `shutil.which('phone-harness')` 运行时探测；找不到时提示用户从
  WorkBuddy Skill marketplace 安装 phone-harness skill。
- zhenji **不会自动 download** phone-harness；也不 vendor 一份。
- 历史 "bundled" 措辞改为 "内置 adapter"。

行为约定（v5.1.2）：
- adapter 模式：v5 强约束改为可配置；PHONE_HARNESS_STRICT=1 恢复严格
- 可见副作用：所有 HID 输入 / 剪贴板写均有 Python 端 callback
- 动态几何：窗口偏移与尺寸不存全局常量；调用 screen_info() 拿最新

子模块：
- geometry: iPhone Mirroring 窗口几何常量 + visual↔screen 换算
            默认值仅作 fallback；运行时必须 screen_info()
- sentinel: 剪贴板哨兵协议
"""
from __future__ import annotations

import logging
import os
import subprocess
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__version__ = "5.2"

# ============================================================
# 1. phone-harness 探测与初始化
# ============================================================

PHONE_HARNESS_BIN = os.environ.get("PHONE_HARNESS_BIN") or shutil.which("phone-harness")


def require_phone_harness() -> str:
    """Find phone-harness executable; raise with actionable message if missing.

    v5.1.2: 这是内置 adapter 模式——zhenji 不会自动 download / vendor phone-harness。
    用户须自行从 WorkBuddy Skill marketplace 安装 phone-harness skill 后再使用。
    """
    global PHONE_HARNESS_BIN
    if PHONE_HARNESS_BIN is None:
        # Re-check in case PATH was set after import
        PHONE_HARNESS_BIN = shutil.which("phone-harness")
    if PHONE_HARNESS_BIN is None:
        raise FileNotFoundError(
            "phone-harness not found in $PATH.\n"
            "zhenji 是内置 phone-harness adapter，但仍需用户已安装 phone-harness skill。\n"
            "请通过 WorkBuddy Skill marketplace 安装 `phone-harness` skill：\n"
            "  • WorkBuddy Settings → Skills → 搜索 'phone-harness'\n"
            "  • 或：打开 phone-harness skill 详情页 → Install\n"
            "安装完成后 `which phone-harness` 应输出路径。\n"
            "如已安装但仍找不到，可设 PHONE_HARNESS_BIN=/path/to/phone-harness 显式指定。"
        )
    return PHONE_HARNESS_BIN


def run_heredoc(script: str, *, timeout: float | None = None) -> subprocess.CompletedProcess:
    """Execute a phone-harness Python script via heredoc.

    Args:
        script: Python source string (already includes imports, helpers are pre-imported in phone-harness env).
        timeout: Optional timeout in seconds. Default: no timeout (large batch jobs).

    Returns:
        subprocess.CompletedProcess with stdout/stderr captured.

    Raises:
        FileNotFoundError: if phone-harness not installed.
    """
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
    """Quick check: is phone-harness installed and accessible?"""
    try:
        require_phone_harness()
        return True
    except FileNotFoundError:
        return False


# ============================================================
# 2. High-level API（包装 phone-harness CLI helper）
# ============================================================

def connection_state() -> str:
    """Return connection state: 'ready' | 'blocked' | 'no-window' | 'not-running' | 'locked'."""
    p = run_heredoc("import json; print(connection_state())\n", timeout=15)
    if p.returncode != 0:
        raise RuntimeError(f"connection_state failed: {p.stderr.strip()}")
    return p.stdout.strip()


def screen_info() -> dict[str, Any]:
    """Return window geometry + image size as dict."""
    import json as _json
    p = run_heredoc(
        "import json; print(json.dumps(screen_info(), ensure_ascii=False))\n",
        timeout=15,
    )
    if p.returncode != 0:
        raise RuntimeError(f"screen_info failed: {p.stderr.strip()}")
    try:
        return _json.loads(p.stdout.strip())
    except _json.JSONDecodeError as exc:
        raise RuntimeError(f"screen_info returned invalid JSON: {p.stdout[:200]!r}") from exc


def screenshot(path: str) -> str:
    """Capture current screen to file. Returns absolute path."""
    p = run_heredoc(
        f"screenshot({path!r})\n",
        timeout=30,
    )
    if p.returncode != 0:
        raise RuntimeError(f"screenshot failed: {p.stderr.strip()}")
    return str(Path(path).resolve())


def tap(x: float, y: float, *, sleep_after: float = 0.0) -> None:
    """Tap screen at (x, y). Coordinates are global screen points (already include window offset)."""
    lines = [f"tap({x}, {y})"]
    if sleep_after > 0:
        lines.append(f"time.sleep({sleep_after})")
    p = run_heredoc(
        "import time\n" + "\n".join(lines) + "\n",
        timeout=15,
    )
    if p.returncode != 0:
        raise RuntimeError(f"tap({x},{y}) failed: {p.stderr.strip()}")


def swipe(x1: float, y1: float, x2: float, y2: float, duration: float = 0.4) -> None:
    """Drag from (x1, y1) to (x2, y2)."""
    p = run_heredoc(
        f"swipe({x1}, {y1}, {x2}, {y2}, duration={duration})\n",
        timeout=15,
    )
    if p.returncode != 0:
        raise RuntimeError(f"swipe failed: {p.stderr.strip()}")


def long_press(x: float, y: float, duration: float = 1.0) -> None:
    """Long-press at (x, y) for `duration` seconds.

    v5.1.2 风险记录（用户自行决定接受/规避）：
        long_press > 1s 历史上偶发 phone-harness SIGKILL (exit 137)。
        zhenji 不再强制规避——用户自行决定。
    """
    p = run_heredoc(
        f"long_press({x}, {y}, duration={duration})\n",
        timeout=30,
    )
    if p.returncode != 0:
        raise RuntimeError(f"long_press failed: {p.stderr.strip()}")


def activate_mirror() -> None:
    """Bring iPhone Mirroring window to front on Mac side."""
    import subprocess as _sp
    _sp.run(
        ["osascript", "-e", 'tell application "iPhone Mirroring" to activate'],
        capture_output=True,
        text=True,
        timeout=10,
    )


# ============================================================
# 3. 剪贴板哨兵协议
# ============================================================

def clipboard_set(text: str) -> None:
    """Set macOS clipboard."""
    import subprocess as _sp
    p = _sp.run(["pbcopy"], input=text, text=True, capture_output=True, timeout=5)
    if p.returncode != 0:
        raise RuntimeError(f"pbcopy failed: {p.stderr}")


def clipboard_read() -> str:
    """Read macOS clipboard."""
    import subprocess as _sp
    p = _sp.run(["pbpaste"], capture_output=True, text=True, timeout=5)
    if p.returncode != 0:
        raise RuntimeError(f"pbpaste failed: {p.stderr}")
    return p.stdout


# ============================================================
# 4. iPhone Mirroring 几何缓存
# ============================================================

DEFAULT_WINDOW_W = 440
DEFAULT_WINDOW_H = 970
DEFAULT_OFFSET_X = 1216
DEFAULT_OFFSET_Y = 25


def visual_to_screen(vx: float, vy: float) -> tuple[float, float]:
    """Convert visual coords (relative to mirror window) to global screen coords."""
    return (vx + DEFAULT_OFFSET_X, vy + DEFAULT_OFFSET_Y)


def screen_to_visual(sx: float, sy: float) -> tuple[float, float]:
    """Convert global screen coords back to visual coords."""
    return (sx - DEFAULT_OFFSET_X, sy - DEFAULT_OFFSET_Y)


# ============================================================
# 5. 健康检查 / 自检
# ============================================================

def doctor() -> dict[str, Any]:
    """Return doctor dict: phone-harness install + iOS Mirroring reachable."""
    import json as _json
    bin_ = require_phone_harness()
    # Try to also probe iOS connection
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
        "phone_harness_version": "adapter-via-cli (v5.1.2)",
        "connection_state": cs,
        "screen_info": si,
        "zhenji_version": __version__,
        "is_strict_mode": bool(int(os.environ.get("PHONE_HARNESS_STRICT", "0"))),
    }