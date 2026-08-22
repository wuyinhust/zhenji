"""Geometry helpers — iPhone Mirroring 窗口坐标换算（v5.1.2 动态版）。

V5.1.2 关键变更（修复 v5.1.1 hardcode 问题）：
- 默认常量仅作 fallback / 测试用；**运行时必须** `screen_info()` 拿真实窗口；
- normalized templates（visual (x,y) on a 440×970 frame）→ 通过
  `live_screen_info()` 拿当前 offset/width/height 做 viewbox 缩放后产生屏幕坐标；
- 不存全局屏幕坐标常量；mirror 重建后自动 invalidate。

已知 normalized templates（来自 2026-08-22 实测 440×970 窗口）：
    VIDEO_CENTER          (220, 380)   视频中央；用于 tap 暂停
    SHARE_BUTTON_TOP_RIGHT (394, 105)   详情页右上角分享箭头
    COPY_LINK_BUTTON       (105, 830)   分享面板第三行第 2 个
    CLOSE_MODAL_X          ( 50, 130)   关闭任何弹窗的 X

使用示例：
    from phone_harness import screen_info
    from phone_harness.geometry import visual_to_screen_live, COPY_LINK_BUTTON

    info = screen_info()
    sx, sy = visual_to_screen_live(*COPY_LINK_BUTTON, info)
    tap(sx, sy)
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

# =============================================================
# 历史窗口几何（仅 fallback / 测试；运行时必须 screen_info）
# =============================================================
DEFAULT_MIRROR_WIDTH = 440
DEFAULT_MIRROR_HEIGHT = 970
DEFAULT_MIRROR_OFFSET_X = 1216
DEFAULT_MIRROR_OFFSET_Y = 25


# =============================================================
# Normalized templates（440×970 视图内坐标）
# =============================================================
VIDEO_CENTER = (220, 380)
SHARE_BUTTON_TOP_RIGHT = (394, 105)
COPY_LINK_BUTTON = (105, 830)
CLOSE_MODAL_X = (50, 130)


# =============================================================
# Live geometry helpers
# =============================================================
@dataclass(frozen=True)
class LiveBounds:
    """iPhone Mirroring 窗口当前真实矩形（运行时由 screen_info() 拿）。"""
    offset_x: int
    offset_y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.offset_x + self.width

    @property
    def bottom(self) -> int:
        return self.offset_y + self.height

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


def visual_to_screen_live(
    vx: float,
    vy: float,
    bounds: LiveBounds,
    *,
    template_width: int = DEFAULT_MIRROR_WIDTH,
    template_height: int = DEFAULT_MIRROR_HEIGHT,
) -> tuple[float, float]:
    """将 normalized 模板坐标换算到当前窗口的屏幕坐标。

    计算：(vx / template_w) * bounds.width + bounds.offset_x,
          (vy / template_h) * bounds.height + bounds.offset_y
    """
    if template_width <= 0 or template_height <= 0:
        raise ValueError(f"invalid template dims: {template_width}x{template_height}")
    sx = (vx / template_width) * bounds.width + bounds.offset_x
    sy = (vy / template_height) * bounds.height + bounds.offset_y
    return (sx, sy)


def visual_to_screen(
    vx: float,
    vy: float,
    *,
    offset_x: int | None = None,
    offset_y: int | None = None,
) -> tuple[float, float]:
    """向后兼容：未传 offset 时用 DEFAULT_*（仅供历史代码兼容）。

    v5.1.2 推荐使用 `visual_to_screen_live(vx, vy, bounds)`。
    """
    ox = offset_x if offset_x is not None else DEFAULT_MIRROR_OFFSET_X
    oy = offset_y if offset_y is not None else DEFAULT_MIRROR_OFFSET_Y
    return (vx + ox, vy + oy)


def screen_to_visual(
    sx: float,
    sy: float,
    *,
    offset_x: int | None = None,
    offset_y: int | None = None,
) -> tuple[float, float]:
    ox = offset_x if offset_x is not None else DEFAULT_MIRROR_OFFSET_X
    oy = offset_y if offset_y is not None else DEFAULT_MIRROR_OFFSET_Y
    return (sx - ox, sy - oy)


def live_bounds_from_screen_info(info: dict[str, object]) -> LiveBounds:
    """Build LiveBounds from a phone-harness screen_info() payload.

    The phone-harness screen_info() returns keys that have varied over time:
    prefer `window` sub-dict when present, else fall back to top-level keys.
    """
    win = info.get("window") if isinstance(info, dict) else None
    if isinstance(win, dict):
        return LiveBounds(
            offset_x=int(win.get("x", DEFAULT_MIRROR_OFFSET_X)),
            offset_y=int(win.get("y", DEFAULT_MIRROR_OFFSET_Y)),
            width=int(win.get("w", DEFAULT_MIRROR_WIDTH)),
            height=int(win.get("h", DEFAULT_MIRROR_HEIGHT)),
        )
    # Fallback: top-level offset/width/height keys
    return LiveBounds(
        offset_x=int(info.get("offset_x", DEFAULT_MIRROR_OFFSET_X)),
        offset_y=int(info.get("offset_y", DEFAULT_MIRROR_OFFSET_Y)),
        width=int(info.get("width", DEFAULT_MIRROR_WIDTH)),
        height=int(info.get("height", DEFAULT_MIRROR_HEIGHT)),
    )
