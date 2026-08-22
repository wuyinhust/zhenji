"""Platform status 测试 (V5.2 P1)。

确认 platform_status.yaml 的声明被正确加载，且
router_only 不被误判为业务支持 (supported=False)。
"""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from platform_status import load_status, all_statuses


def test_xhs_production():
    s = load_status("xhs")
    assert s is not None
    assert s.status == "production"
    assert s.supported is True
    assert s.production_ready is True


def test_douyin_beta():
    s = load_status("douyin")
    assert s is not None
    assert s.status == "beta"
    assert s.supported is True
    assert s.production_ready is False


def test_instagram_router_only_not_supported():
    s = load_status("instagram")
    assert s is not None
    assert s.status == "router_only"
    assert s.supported is False
    assert s.production_ready is False


def test_tiktok_router_only_not_supported():
    s = load_status("tiktok")
    assert s is not None
    assert s.status == "router_only"
    assert s.supported is False


def test_all_statuses_present():
    all_s = all_statuses()
    for p in ("xhs", "douyin", "instagram", "tiktok"):
        assert p in all_s


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
