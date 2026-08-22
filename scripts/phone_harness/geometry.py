"""Geometry helpers — iPhone Mirroring 窗口坐标系常量。

v5.1 bundled：作为 phone-harness 子包的一部分，给 zhenji 提供常用坐标换算。

历史窗口几何（默认 440×970 @ (1216,25)）来自 2026-08-22 实测。
实际窗口尺寸/位置应通过 `screen_info()` 动态获取，不要硬编码。
"""
from __future__ import annotations

# 默认 iPhone Mirroring 窗口尺寸（历史值；实际用 screen_info() 取最新）
DEFAULT_MIRROR_WIDTH = 440
DEFAULT_MIRROR_HEIGHT = 970
DEFAULT_MIRROR_OFFSET_X = 1216
DEFAULT_MIRROR_OFFSET_Y = 25

# 截图/视频中央点（用于暂停视频等）
VIDEO_CENTER = (220, 380)

# 详情页右上角分享按钮（截图箭头 ⬆）
SHARE_BUTTON_TOP_RIGHT = (394, 105)

# 分享面板第三行第 2 个（Copy link）
COPY_LINK_BUTTON = (105, 830)

# 关闭任何弹窗的 X（top-left）
CLOSE_MODAL_X = (50, 130)


def visual_to_screen(vx: float, vy: float, *, offset_x: int | None = None, offset_y: int | None = None) -> tuple[float, float]:
    """Visual → screen coords."""
    ox = offset_x if offset_x is not None else DEFAULT_MIRROR_OFFSET_X
    oy = offset_y if offset_y is not None else DEFAULT_MIRROR_OFFSET_Y
    return (vx + ox, vy + oy)


def screen_to_visual(sx: float, sy: float, *, offset_x: int | None = None, offset_y: int | None = None) -> tuple[float, float]:
    """Screen → visual coords."""
    ox = offset_x if offset_x is not None else DEFAULT_MIRROR_OFFSET_X
    oy = offset_y if offset_y is not None else DEFAULT_MIRROR_OFFSET_Y
    return (sx - ox, sy - oy)