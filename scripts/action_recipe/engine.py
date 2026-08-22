"""Action Recipe engine (Zhenji V5.2).

执行模型：
    Platform Knowledge (YAML recipe)
        ↓
    engine.load(platform)
        ↓
    engine.run(flow, harness, validator)
        ↓ 逐 action
    harness.screen_info() → LiveBounds → ratio_to_screen 换算真实坐标
    harness.<action>(...)
    validator 校验状态
        ↓
    成功：产出结果（如 clipboard 链接）
    失败：抛 RecipeStepError → 调用方转入视觉探索 fallback

harness / validator 以 Protocol 注入，便于离线测试（fake harness）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol

from .schema import Action, ActionType, Recipe
from .validator import RecipeValidationError, validate_recipe
from phone_harness.geometry import LiveBounds, ratio_to_screen


class RecipeStepError(Exception):
    """单步动作校验失败，应转入视觉探索 fallback。"""


class RecipeNotFoundError(Exception):
    pass


class PhoneHarness(Protocol):
    """engine 依赖的最小真机接口；测试可注入 fake。"""

    def screen_info(self) -> dict[str, Any]: ...
    def tap(self, x: float, y: float) -> None: ...
    def long_press(self, x: float, y: float, duration: float = 1.0) -> None: ...
    def swipe(self, x1: float, y1: float, x2: float, y2: float, duration: float = 0.3) -> None: ...
    def screenshot(self) -> str: ...  # returns image path
    def open_app(self, bundle_id: str) -> None: ...
    def get_clipboard(self) -> str: ...
    # 可选：语义点击（依赖 OCR/视觉模型）
    def semantic_tap(self, text: dict[str, str]) -> None: ...


class StateValidator(Protocol):
    def validate(self, kind: str, params: dict[str, Any], harness: Any) -> bool: ...


def load_recipe(platform: str, recipes_dir: str | Path) -> Recipe:
    p = Path(recipes_dir) / f"{platform}.yaml"
    if not p.exists():
        raise RecipeNotFoundError(platform)
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RecipeValidationError(
            "PyYAML 未安装，无法加载 recipe YAML；请 `pip install pyyaml`"
        ) from exc
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return validate_recipe(data)


class RecipeEngine:
    def __init__(self, recipes_dir: str | Path):
        self.recipes_dir = Path(recipes_dir)

    def load(self, platform: str) -> Recipe:
        return load_recipe(platform, self.recipes_dir)

    def run(
        self,
        platform: str,
        *,
        harness: PhoneHarness,
        validator: StateValidator,
        flow: str | None = None,
        recipe: Recipe | None = None,
        on_fallback: Callable[[Action, Exception], None] | None = None,
    ) -> dict[str, Any]:
        recipe = recipe or self.load(platform)
        if flow is not None and recipe.flow != flow:
            raise RecipeStepError(f"recipe flow {recipe.flow!r} != requested {flow!r}")
        context: dict[str, Any] = {"platform": platform, "flow": recipe.flow}
        for action in recipe.actions:
            try:
                self._exec_action(action, harness, validator, context)
            except RecipeStepError as exc:
                if on_fallback is not None:
                    on_fallback(action, exc)
                raise
        return context

    def _exec_action(
        self,
        action: Action,
        harness: PhoneHarness,
        validator: StateValidator,
        context: dict[str, Any],
    ) -> None:
        if action.type is ActionType.OPEN_APP:
            bid = action.target.bundle_id if action.target else None
            if not bid:
                raise RecipeStepError(f"{action.name}: open_app 缺少 bundle_id")
            harness.open_app(bid)

        elif action.type is ActionType.TAP:
            x, y = self._coord(action, harness)
            harness.tap(x, y)

        elif action.type is ActionType.SEMANTIC_TAP:
            text = action.target.text if action.target else None
            if text is None:
                raise RecipeStepError(f"{action.name}: semantic_tap 缺 text")
            if not hasattr(harness, "semantic_tap"):
                raise RecipeStepError(f"{action.name}: harness 未实现 semantic_tap")
            harness.semantic_tap(text)

        elif action.type is ActionType.LONG_PRESS:
            x, y = self._coord(action, harness)
            dur = float(action.extra.get("duration", 1.0))
            harness.long_press(x, y, dur)

        elif action.type is ActionType.SWIPE:
            coords = self._swipe_coords(action, harness)
            harness.swipe(*coords)

        elif action.type is ActionType.SCREENSHOT:
            context["last_screenshot"] = harness.screenshot()

        elif action.type is ActionType.WAIT:
            import time

            time.sleep(float(action.extra.get("seconds", 0.5)))

        elif action.type is ActionType.ASSERT_STATE:
            pass

        else:  # pragma: no cover
            raise RecipeStepError(f"未实现 action type: {action.type}")

        # 状态校验
        for v in action.validation:
            ok = validator.validate(v.kind, v.params, harness)
            if not ok:
                raise RecipeStepError(f"action {action.name} 校验失败: {v.kind}")

    def _coord(self, action: Action, harness: PhoneHarness) -> tuple[float, float]:
        if action.target is None or action.target.coordinate is None:
            raise RecipeStepError(f"{action.name}: 需要坐标目标")
        info = harness.screen_info()
        bounds = LiveBounds(
            offset_x=int(info.get("offset_x", 0)),
            offset_y=int(info.get("offset_y", 0)),
            width=int(info.get("width", 0)),
            height=int(info.get("height", 0)),
        )
        return ratio_to_screen(
            action.target.coordinate.x_ratio, action.target.coordinate.y_ratio, bounds
        )

    def _swipe_coords(self, action: Action, harness: PhoneHarness) -> tuple[float, float, float, float, float]:
        if action.target is None or action.target.coordinate is None:
            raise RecipeStepError(f"{action.name}: swipe 需起坐标")
        info = harness.screen_info()
        bounds = LiveBounds(
            offset_x=int(info.get("offset_x", 0)),
            offset_y=int(info.get("offset_y", 0)),
            width=int(info.get("width", 0)),
            height=int(info.get("height", 0)),
        )
        c = action.target.coordinate
        sx, sy = ratio_to_screen(c.x_ratio, c.y_ratio, bounds)
        # 终点是 extra 中的 ratio_to（默认向下 0.3）
        tx = float(action.extra.get("x2_ratio", c.x_ratio))
        ty = float(action.extra.get("y2_ratio", c.y_ratio + 0.3))
        ex, ey = ratio_to_screen(tx, ty, bounds)
        dur = float(action.extra.get("duration", 0.3))
        return (sx, sy, ex, ey, dur)
