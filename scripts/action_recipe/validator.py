"""Action Recipe validator (Zhenji V5.2).

硬规则：
1. 坐标只允许 normalized ratio，禁止绝对像素（出现 x:/y: 绝对数字直接拒）。
2. 必须有 platform / app.bundle_id / flow / states / actions。
3. action.type 必须在 ActionType 枚举内。
4. 每个 action 必须有至少一个 validation（否则无法确认状态，必须走视觉探索）。
5. 坐标 ratio 必须在 [0,1]。
"""
from __future__ import annotations

from typing import Any

from .schema import (
    Action,
    ActionTarget,
    ActionType,
    NormalizedCoordinate,
    Recipe,
    RecipeApp,
    Validation,
)


class RecipeValidationError(ValueError):
    """recipe 不合法（结构或坐标违规）。"""


def _is_ratio(value: Any) -> bool:
    return isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0


def validate_recipe(data: dict[str, Any]) -> Recipe:
    """把 dict (YAML 解析结果) 校验并构造 Recipe。"""
    if not isinstance(data, dict):
        raise RecipeValidationError("recipe root must be a mapping")

    platform = data.get("platform")
    if not isinstance(platform, str) or not platform:
        raise RecipeValidationError("missing platform")

    app = data.get("app")
    if not isinstance(app, dict) or not app.get("bundle_id"):
        raise RecipeValidationError("missing app.bundle_id")
    bundle_id = app["bundle_id"]

    flow = data.get("flow")
    if not isinstance(flow, str) or not flow:
        raise RecipeValidationError("missing flow")

    states = data.get("states")
    if not isinstance(states, list) or not states:
        raise RecipeValidationError("states must be a non-empty list")

    actions_raw = data.get("actions")
    if not isinstance(actions_raw, list) or not actions_raw:
        raise RecipeValidationError("actions must be a non-empty list")

    actions: list[Action] = []
    for i, a in enumerate(actions_raw):
        if not isinstance(a, dict):
            raise RecipeValidationError(f"action[{i}] must be a mapping")
        name = a.get("name")
        if not isinstance(name, str) or not name:
            raise RecipeValidationError(f"action[{i}] missing name")
        atype = a.get("type")
        try:
            atype_enum = ActionType(atype)
        except ValueError:
            raise RecipeValidationError(
                f"action[{i}] type {atype!r} not in {[t.value for t in ActionType]}"
            )
        target = _validate_target(a.get("target"), i)
        validations = _validate_validations(a.get("validation"), i)
        if not validations:
            raise RecipeValidationError(
                f"action[{i}] ({name}) 必须有至少一个 validation；"
                f"无校验则无法确认状态，应走视觉探索 fallback。"
            )
        actions.append(
            Action(
                name=name,
                type=atype_enum,
                target=target,
                validation=validations,
                extra=a.get("extra") or {},
            )
        )

    return Recipe(
        platform=platform,
        app=RecipeApp(bundle_id=bundle_id),
        flow=flow,
        states=list(states),
        actions=actions,
        status=data.get("status", "production"),
        notes=data.get("notes", ""),
    )


def _validate_target(target: Any, idx: int) -> ActionTarget | None:
    if target is None:
        return None
    if not isinstance(target, dict):
        raise RecipeValidationError(f"action[{idx}].target must be a mapping")

    coord = target.get("coordinate")
    src: dict[str, Any] = dict(target)
    if isinstance(coord, dict):
        # 兼容 review 示例的嵌套写法：target.coordinate.{type,x,y}
        for k, v in coord.items():
            if k != "type":
                src.setdefault(k, v)

    xr = src.get("x_ratio")
    yr = src.get("y_ratio")
    x = src.get("x")
    y = src.get("y")

    if xr is None and yr is None and x is None and y is None:
        coordinate = None
    elif xr is not None or yr is not None:
        if xr is None or yr is None:
            raise RecipeValidationError(
                f"action[{idx}].target normalized 坐标需同时提供 x_ratio/y_ratio"
            )
        if not _is_ratio(xr) or not _is_ratio(yr):
            raise RecipeValidationError(f"ratio 必须在 [0,1]，got ({xr},{yr})")
        coordinate = NormalizedCoordinate(float(xr), float(yr))
    else:
        # x/y 是 ratio 的"已弃用别名"；>1.0 一律视为绝对像素坐标，拒绝
        if not _is_ratio(x) or not _is_ratio(y):
            raise RecipeValidationError(
                f"检测到疑似绝对像素坐标 x={x}, y={y}（>1.0）。"
                f"禁止保存绝对值；改用 x_ratio/y_ratio (0-1)。"
            )
        coordinate = NormalizedCoordinate(float(x), float(y))

    text = target.get("text")
    if text is not None and not isinstance(text, dict):
        raise RecipeValidationError(f"action[{idx}].target.text 必须是 {{lang: label}} 映射")

    bundle_id = target.get("bundle_id")
    if coordinate is None and text is None and bundle_id is None:
        raise RecipeValidationError(
            f"action[{idx}].target 必须提供 coordinate / text / bundle_id 之一"
        )
    return ActionTarget(coordinate=coordinate, text=text, bundle_id=bundle_id)


def _validate_validations(validations: Any, idx: int) -> list[Validation]:
    if validations is None:
        return []
    if not isinstance(validations, list):
        raise RecipeValidationError(f"action[{idx}].validation 必须是 list")
    for v in validations:
        if not isinstance(v, dict) or "kind" not in v:
            raise RecipeValidationError(f"action[{idx}].validation 项需含 kind")
    return [Validation(kind=v["kind"], params=v.get("params") or {}) for v in validations]
