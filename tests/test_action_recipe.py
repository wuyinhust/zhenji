"""Action Recipe 测试 (V5.2 P1)。

覆盖：
- validator 拒绝绝对像素坐标（x:1320,y:850）
- validator 接受 normalized ratio（嵌套 x_ratio/y_ratio）
- validator 拒绝未知 action type
- validator 要求每个 action 至少一个 validation
- engine 用 ratio+bounds 换算真实屏幕坐标执行 tap
- engine 校验失败抛 RecipeStepError 并触发 on_fallback
- 真实 YAML recipe 可被校验加载（无 pyyaml 时 skip）
"""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from action_recipe.validator import RecipeValidationError, validate_recipe
from action_recipe.engine import RecipeEngine, RecipeStepError


def _recipe_dict():
    return {
        "platform": "xhs",
        "app": {"bundle_id": "com.xingin.xhs"},
        "flow": "harvest_share_link",
        "states": ["VIDEO_PAGE", "SHARE_PANEL", "CLIPBOARD_READY"],
        "actions": [
            {
                "name": "open_share",
                "type": "tap",
                "target": {"coordinate": {"type": "normalized", "x_ratio": 0.895, "y_ratio": 0.108}},
                "validation": [{"kind": "share_panel_visible"}],
            },
            {
                "name": "copy_link",
                "type": "semantic_tap",
                "target": {"text": {"zh": "复制链接"}},
                "validation": [
                    {"kind": "clipboard_changed"},
                    {"kind": "url_match", "params": {"domains": ["xhslink.com"]}},
                ],
            },
        ],
    }


class FakeHarness:
    def __init__(self, bounds):
        self.bounds = bounds
        self.taps = []
        self.opened = None
        self.semantic = None

    def screen_info(self):
        ox, oy, w, h = self.bounds
        return {"offset_x": ox, "offset_y": oy, "width": w, "height": h}

    def tap(self, x, y):
        self.taps.append((x, y))

    def open_app(self, bid):
        self.opened = bid

    def screenshot(self):
        return "/tmp/shot.png"

    def semantic_tap(self, text):
        self.semantic = text


class FakeValidator:
    def __init__(self, fail_on=None):
        self.fail_on = set(fail_on or [])
        self.kinds = []

    def validate(self, kind, params, harness):
        self.kinds.append(kind)
        return kind not in self.fail_on


def test_validator_rejects_absolute_coords():
    bad = _recipe_dict()
    bad["actions"][0]["target"] = {"coordinate": {"type": "normalized", "x": 1320, "y": 850}}
    try:
        validate_recipe(bad)
    except RecipeValidationError as e:
        assert "绝对" in str(e) or "1320" in str(e)
        return
    raise AssertionError("absolute coords should be rejected")


def test_validator_accepts_ratio_nested():
    r = validate_recipe(_recipe_dict())
    assert r.actions[0].target.coordinate.x_ratio == 0.895
    assert r.actions[0].target.coordinate.y_ratio == 0.108


def test_validator_rejects_unknown_action_type():
    bad = _recipe_dict()
    bad["actions"][0]["type"] = "teleport"
    try:
        validate_recipe(bad)
    except RecipeValidationError:
        return
    raise AssertionError("unknown action type should be rejected")


def test_validator_requires_validation_per_action():
    bad = _recipe_dict()
    bad["actions"][0]["validation"] = []
    try:
        validate_recipe(bad)
    except RecipeValidationError:
        return
    raise AssertionError("missing validation should be rejected")


def test_engine_runs_recipe_and_maps_coords():
    recipe = validate_recipe(_recipe_dict())
    harness = FakeHarness(bounds=(100, 100, 400, 800))
    validator = FakeValidator()
    engine = RecipeEngine(SKILL_DIR / "references" / "platform-recipes")
    ctx = engine.run("xhs", harness=harness, validator=validator, recipe=recipe)
    # open_share tap: 100 + 0.895*400 = 458, 100 + 0.108*800 = 186.4
    assert harness.taps[0] == (458.0, 186.4)
    assert harness.semantic == {"zh": "复制链接"}
    # 所有 validation kind 都被触发
    assert "share_panel_visible" in validator.kinds
    assert "clipboard_changed" in validator.kinds
    assert ctx["platform"] == "xhs"


def test_engine_fallback_on_validation_failure():
    recipe = validate_recipe(_recipe_dict())
    harness = FakeHarness(bounds=(100, 100, 400, 800))
    validator = FakeValidator(fail_on={"share_panel_visible"})
    engine = RecipeEngine(SKILL_DIR / "references" / "platform-recipes")
    fallen = []
    try:
        engine.run(
            "xhs", harness=harness, validator=validator, recipe=recipe,
            on_fallback=lambda a, e: fallen.append((a.name, e)),
        )
    except RecipeStepError:
        pass
    else:
        raise AssertionError("validation failure should raise RecipeStepError")
    assert fallen and fallen[0][0] == "open_share"


def test_recipes_yaml_loadable():
    """真实 YAML recipe 可被校验加载；无 pyyaml 时 skip。"""
    try:
        import yaml  # noqa
    except ImportError:
        print("  SKIP test_recipes_yaml_loadable: pyyaml 未安装")
        return
    engine = RecipeEngine(SKILL_DIR / "references" / "platform-recipes")
    for plat in ("xhs", "douyin", "instagram", "tiktok"):
        r = engine.load(plat)
        assert r.platform == plat
        assert r.app.bundle_id


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    failures = []
    for fn in tests:
        try:
            fn()
            print(f"  PASS {fn.__name__}")
        except (AssertionError, Exception) as e:
            failures.append((fn.__name__, e))
            print(f"  FAIL {fn.__name__}: {e!r}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
