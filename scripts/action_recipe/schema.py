"""Action Recipe schema (Zhenji V5.2).

坐标约定（强制，见 validator）：
- 只允许 normalized ratio (0.0-1.0)：x_ratio / y_ratio
- 绝对像素坐标 (x: 1320, y: 850) 一律禁止
- 运行时：ratio → screen_info() 拿当前窗口 bounds → 真实屏幕坐标

语义点击（semantic_tap）用 text 而非坐标，避免依赖固定布局。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    OPEN_APP = "open_app"
    TAP = "tap"
    SEMANTIC_TAP = "semantic_tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    ASSERT_STATE = "assert_state"


class CoordinateType(str, Enum):
    NORMALIZED = "normalized"
    # 故意不提供 ABSOLUTE —— validator 拒绝任何绝对坐标


@dataclass(frozen=True)
class NormalizedCoordinate:
    """0.0-1.0 ratio on the live window. 运行时换算成屏幕像素。"""

    x_ratio: float
    y_ratio: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.x_ratio <= 1.0 and 0.0 <= self.y_ratio <= 1.0):
            raise ValueError(
                f"coordinate ratio must be within [0,1], got ({self.x_ratio},{self.y_ratio})"
            )

    @property
    def as_tuple(self) -> tuple[float, float]:
        return (self.x_ratio, self.y_ratio)


@dataclass(frozen=True)
class ActionTarget:
    """动作目标：normalized 坐标点击 / 语义文本点击 / bundle_id 启动。"""

    coordinate: NormalizedCoordinate | None = None
    text: dict[str, str] | None = None  # {"zh": "复制链接"}
    bundle_id: str | None = None        # open_app 用

    def __post_init__(self) -> None:
        if self.coordinate is None and self.text is None and self.bundle_id is None:
            raise ValueError("ActionTarget 必须提供 coordinate / text / bundle_id 之一")


@dataclass(frozen=True)
class Validation:
    """执行动作后的状态校验。"""

    kind: str  # share_panel_visible / clipboard_changed / url_match / state
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    name: str
    type: ActionType
    target: ActionTarget | None = None
    validation: list[Validation] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecipeApp:
    bundle_id: str


@dataclass(frozen=True)
class Recipe:
    platform: str
    app: RecipeApp
    flow: str
    states: list[str]
    actions: list[Action]
    status: str = "production"  # production / beta / router_only
    notes: str = ""

    def action_by_name(self, name: str) -> Action | None:
        for a in self.actions:
            if a.name == name:
                return a
        return None
