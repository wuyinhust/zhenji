"""platform_router 严格域名匹配测试。

覆盖：
- 已知平台正确路由
- 攻击/钓鱼域名（evil.example 后缀）拒绝
- 空 URL / 非 URL 处理
"""
import sys
from pathlib import Path

# 允许独立运行：把 scripts/ 加进 PYTHONPATH
SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import platform_router as pr


def test_xhs_production():
    assert pr.route_url("https://xhslink.com/o/abc").key == "xhs"
    assert pr.route_url("https://www.xhslink.com/o/abc").key == "xhs"
    assert pr.route_url("https://xhslink.cn/o/abc").key == "xhs"
    assert pr.route_url("https://www.xhslink.cn/o/abc").key == "xhs"
    assert pr.route_url("https://www.xiaohongshu.com/explore/123").key == "xhs"
    assert pr.route_url("https://xiaohongshu.com").key == "xhs"


def test_douyin():
    assert pr.route_url("https://douyin.com/video/123").key == "douyin"
    assert pr.route_url("https://www.douyin.com/video/123").key == "douyin"
    assert pr.route_url("https://v.douyin.com/iABC/").key == "douyin"
    assert pr.route_url("https://www.iesdouyin.com/share/video/123").key == "douyin"


def test_instagram_tiktok_routing_only():
    # router ready, adapter pending
    r1 = pr.route_url("https://www.instagram.com/p/abc")
    assert r1.key == "instagram" and r1.supported is False
    r2 = pr.route_url("https://www.tiktok.com/@u/v/1")
    assert r2.key == "tiktok" and r2.supported is False


def test_adversarial_domains():
    """攻击/钓鱼域名：evil.example 后缀必须拒绝。"""
    cases = [
        "https://xhslink.com.evil.example/path",
        "https://xiaohongshu.com.attacker.tld/x",
        "https://douyin.com.evil.example/",
        "https://iesdouyin.com.attacker.tld/",
        "https://v.douyin.com.evil.example/",
        "https://instagram.com.attacker.tld/",
        "https://tiktok.com.attacker.tld/",
    ]
    for url in cases:
        r = pr.route_url(url)
        assert r.key == "unknown", f"{url} should be unknown, got {r.key}"
        assert r.supported is False


def test_garbage_input():
    assert pr.route_url("").key == "unknown"
    assert pr.route_url("not-a-url").key == "unknown"
    assert pr.route_url("javascript:alert(1)").key == "unknown"


def test_case_insensitive():
    # 大写 host 应该被 lower()
    assert pr.route_url("https://XHSLINK.COM/o/abc").key == "xhs"
    assert pr.route_url("https://Www.Xiaohongshu.Com/x").key == "xhs"


def main():
    failures = []
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
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

