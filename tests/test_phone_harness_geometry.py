"""phone_harness.geometry 动态坐标测试 (V5.1.2 P1.10)。

覆盖：
- LiveBounds 构造与边界属性 (right / bottom / as_dict)
- visual_to_screen_live() 按当前窗口缩放（与 DEFAULT 硬坐标严格区分）
- 不同窗口尺寸下必须重新缩放，不能 hardcode
- live_bounds_from_screen_info() 支持 `window` 子字典 与 顶层 key 两种 payload
- 历史兼容 visual_to_screen() 落回 DEFAULT offset
- 模板尺寸非法（<=0）抛 ValueError

注意：geometry 仅依赖标准库，本测试无网络/无三方依赖。
"""
import sys
from pathlib import Path

# 允许独立运行：把 scripts/ 加进 PYTHONPATH
SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from phone_harness.geometry import (
    LiveBounds,
    visual_to_screen_live,
    visual_to_screen,
    screen_to_visual,
    live_bounds_from_screen_info,
    DEFAULT_MIRROR_OFFSET_X,
    DEFAULT_MIRROR_OFFSET_Y,
    COPY_LINK_BUTTON,
)


def test_live_bounds_edges():
    b = LiveBounds(offset_x=100, offset_y=50, width=440, height=970)
    assert b.right == 540
    assert b.bottom == 1020
    assert b.as_dict() == {
        "offset_x": 100, "offset_y": 50,
        "width": 440, "height": 970,
    }


def test_visual_to_screen_live_scales_to_known_window():
    # 440x970 模板内 (220,380) 在窗口 (1216,25,440,970) 下应等于 (1436,405)
    b = LiveBounds(offset_x=1216, offset_y=25, width=440, height=970)
    sx, sy = visual_to_screen_live(220, 380, b)
    assert (sx, sy) == (1436, 405)


def test_visual_to_screen_live_rescales_on_different_window():
    # 不同窗口尺寸下必须重新缩放，证明没有 hardcode 全局坐标
    b = LiveBounds(offset_x=0, offset_y=0, width=880, height=1940)
    sx, sy = visual_to_screen_live(*COPY_LINK_BUTTON, b)
    # (105/440)*880 = 210 ; (830/970)*1940 = 1660
    assert (sx, sy) == (210, 1660)


def test_live_bounds_from_screen_info_window_subdict():
    info = {"window": {"x": 1216, "y": 25, "w": 440, "h": 970}}
    b = live_bounds_from_screen_info(info)
    assert (b.offset_x, b.offset_y, b.width, b.height) == (1216, 25, 440, 970)


def test_live_bounds_from_screen_info_top_level():
    info = {"offset_x": 10, "offset_y": 20, "width": 300, "height": 600}
    b = live_bounds_from_screen_info(info)
    assert (b.offset_x, b.offset_y, b.width, b.height) == (10, 20, 300, 600)


def test_visual_to_screen_legacy_default():
    # 历史兼容：未传 offset 时落回 DEFAULT（绝不应作为运行时主路径）
    sx, sy = visual_to_screen(105, 830)
    assert (sx, sy) == (
        105 + DEFAULT_MIRROR_OFFSET_X,
        830 + DEFAULT_MIRROR_OFFSET_Y,
    )


def test_visual_to_screen_live_rejects_bad_template():
    b = LiveBounds(offset_x=0, offset_y=0, width=440, height=970)
    try:
        visual_to_screen_live(10, 10, b, template_width=0)
    except ValueError:
        pass
    else:
        raise AssertionError("template_width<=0 should raise ValueError")


def main():
    failures = []
    tests = [
        v for k, v in globals().items()
        if k.startswith("test_") and callable(v)
    ]
    for test_fn in tests:
        try:
            test_fn()
            print(f"  PASS {test_fn.__name__}")
        except AssertionError as e:
            failures.append((test_fn.__name__, str(e)))
            print(f"  FAIL {test_fn.__name__}: {e}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
