"""Action Recipe — 真机操作知识库 (Zhenji V5.2).

把"在某个 App 里怎么拿到分享链接"固化成声明式 recipe，
替代每次截图 + OCR 的视觉探索。

    Platform Knowledge (YAML recipe)
        ↓
    engine.load(platform)
        ↓
    engine.run(flow, harness, validator)
        ↓ 逐 action
    harness.screen_info() → LiveBounds → ratio 换算真实坐标
    harness.<action>(...)
    validator 校验状态
        ↓
    成功：产出结果（如 clipboard 链接）
    失败：抛 RecipeStepError → 调用方转视觉探索 fallback
"""
from __future__ import annotations

from .schema import (
    Action,
    ActionTarget,
    ActionType,
    CoordinateType,
    NormalizedCoordinate,
    Recipe,
    RecipeApp,
    Validation,
)
from .validator import RecipeValidationError, validate_recipe
from .engine import (
    PhoneHarness,
    RecipeEngine,
    RecipeNotFoundError,
    RecipeStepError,
    StateValidator,
    load_recipe,
)

__all__ = [
    "Action",
    "ActionTarget",
    "ActionType",
    "CoordinateType",
    "NormalizedCoordinate",
    "Recipe",
    "RecipeApp",
    "Validation",
    "RecipeValidationError",
    "validate_recipe",
    "PhoneHarness",
    "RecipeEngine",
    "RecipeNotFoundError",
    "RecipeStepError",
    "StateValidator",
    "load_recipe",
]
