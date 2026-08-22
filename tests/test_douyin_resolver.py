"""Douyin resolver 测试 (V5.2 P1)。

覆盖：
- 正常：v.douyin.com/xxx → www.douyin.com/video/<id>（mock redirect，不联网）
- 异常：redirect timeout / 验证码或登录页 / 无 aweme_id

全部离线：通过 monkeypatch douyin_adapter._follow_redirect 阻断真实联网。
"""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import douyin_adapter


def _patch(map_or_exc):
    orig = douyin_adapter._follow_redirect
    if isinstance(map_or_exc, Exception):
        def _boom(url, *a, **k):
            raise map_or_exc
        douyin_adapter._follow_redirect = _boom
    else:
        def _fake(url, *a, **k):
            return map_or_exc.get(url, url)
        douyin_adapter._follow_redirect = _fake
    return orig


def test_resolve_long_url_known_aweme():
    a = douyin_adapter.DouyinAdapter()
    ru = a.resolve_url("https://www.douyin.com/video/7234567890123456789")
    assert ru.media_id == "7234567890123456789"
    assert ru.canonical_url == "https://www.douyin.com/video/7234567890123456789"
    assert ru.extra.get("short_link") is False


def test_resolve_short_link_redirect_walk():
    orig = _patch({"https://v.douyin.com/iABCxyz/": "https://www.douyin.com/video/7234567890123456789"})
    try:
        a = douyin_adapter.DouyinAdapter()
        ru = a.resolve_url("https://v.douyin.com/iABCxyz/")
        assert ru.extra.get("short_link") is True
        assert ru.media_id == "7234567890123456789"
        assert "douyin.com" in ru.canonical_url
    finally:
        douyin_adapter._follow_redirect = orig


def test_resolve_redirect_timeout_returns_original():
    orig = _patch(TimeoutError("redirect timeout"))
    try:
        a = douyin_adapter.DouyinAdapter()
        ru = a.resolve_url("https://v.douyin.com/iABCxyz/")
        # 不崩溃；回退到原短链，media_id unknown
        assert ru.media_id == "unknown"
        assert ru.canonical_url == "https://v.douyin.com/iABCxyz/"
    finally:
        douyin_adapter._follow_redirect = orig


def test_resolve_captcha_or_login_page_no_aweme():
    orig = _patch({"https://v.douyin.com/iABCxyz/": "https://www.douyin.com/login?need_code=1"})
    try:
        a = douyin_adapter.DouyinAdapter()
        ru = a.resolve_url("https://v.douyin.com/iABCxyz/")
        assert ru.media_id == "unknown"
        assert "douyin.com" in ru.canonical_url
    finally:
        douyin_adapter._follow_redirect = orig


def test_resolve_no_aweme_id_in_long_url():
    a = douyin_adapter.DouyinAdapter()
    ru = a.resolve_url("https://www.douyin.com/user/12345")
    assert ru.media_id == "unknown"


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
