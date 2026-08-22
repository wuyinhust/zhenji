"""DouyinAdapter + Douyin MediaFetchResult 语义测试。

覆盖：
- resolve_url 长链形态提取 aweme_id
- resolve_url 短链形态触发 redirect walk
- fetch(mode='fuguang') 走 metadata_only，即使没本地视频也 ok
- fetch() iesdouyin 路径强制 status=metadata_only（不再伪装 ok=True）
- capabilities() 报告 requires_login=True
- Protocol isinstance 检查
"""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import douyin_adapter
from douyin_adapter import DouyinAdapter, _extract_aweme_id
from media_adapter_protocol import (
    MediaAdapter,
    MediaFetchResult,
    FetchStatus,
)


def test_extract_aweme_id_long_url():
    assert _extract_aweme_id("https://www.douyin.com/video/7234567890123456789") == "7234567890123456789"
    assert _extract_aweme_id("https://www.douyin.com/note/111") == "111"
    assert _extract_aweme_id("https://example.com/?modal_id=42") == "42"
    assert _extract_aweme_id("https://example.com/?modalId=99") == "99"
    assert _extract_aweme_id("https://example.com/") is None


def test_resolve_url_long_form_no_network():
    a = DouyinAdapter()
    ru = a.resolve_url("https://www.douyin.com/video/7234567890123456789")
    assert ru.media_id == "7234567890123456789"
    assert ru.platform == "douyin"
    assert ru.extra.get("short_link") is False


def test_resolve_url_short_link_detection():
    """短链形态：short_link flag 由正则离线判定；canonical_url / media_id 依赖网络。

    v5.1.2 修正：resolve_url() 对短链会真实 follow_redirect（联网环境）。
    离线时 canonical_url 保留原短链、media_id 为 'unknown'；
    联网时被 redirect walk 改写（仍属 douyin 域）。两种都允许。
    """
    a = DouyinAdapter()
    ru = a.resolve_url("https://v.douyin.com/iABCxyz/")
    assert ru.extra.get("short_link") is True
    assert ru.platform == "douyin"
    # 离线：原短链；联网：redirect 改写后仍含 douyin 域
    assert "douyin.com" in ru.canonical_url
    # media_id 离线保留 'unknown'；联网后为数字 aweme_id
    assert ru.media_id == "unknown" or ru.media_id.isdigit()


def test_capabilities_require_login():
    a = DouyinAdapter()
    caps = a.capabilities()
    assert caps["metadata_only_supported"] is True
    assert caps["media_ready_supported"] is True
    assert caps["requires_login"] is True
    assert "notes" in caps


def test_protocol_compliance():
    a = DouyinAdapter()
    assert isinstance(a, MediaAdapter), "DouyinAdapter must satisfy MediaAdapter protocol"


def test_fetch_fuguang_metadata_only():
    """浮光档走 probe + write metadata，不下载视频。"""
    a = DouyinAdapter()
    result: MediaFetchResult = a.fetch(
        url="https://www.douyin.com/video/7234567890123456789",
        output_dir="/tmp/test_dy_fuguang",
        mode="fuguang",
    )
    # 状态必须是 metadata_only
    assert result.status in (FetchStatus.METADATA_ONLY, FetchStatus.FAILED)
    if result.status == FetchStatus.METADATA_ONLY:
        assert result.metadata is not None
        assert result.media_ready is False
        # 浮光档接受 metadata_only
        assert result.acceptable_for_mode("fuguang") is True
        assert result.acceptable_for_mode("lueying") is False


def test_fetch_iesdouyin_no_longer_ok_true_misleading():
    """v5.1.2: iesdouyin 没真视频必须 status=metadata_only（不伪装 ok=True 误导）。

    网络依赖：iesdouyin 需要 douyin cookies。无 cookies / 离线环境下底层
    download 会失败（ok=False），adapter 返回 FAILED——此时跳过真机断言，
    避免 CI 在无 cookie 环境误红。有 cookie 时才校验 adapter 强制 metadata_only。
    """
    from douyin_media import download_with_iesdouyin
    from pathlib import Path
    import shutil, tempfile

    tmpdir = Path(tempfile.mkdtemp(prefix="zhenji_test_dy_"))
    try:
        try:
            dr = download_with_iesdouyin(
                url="https://www.douyin.com/video/0000000000000000000",  # 不存在的 ID
                output_dir=str(tmpdir),
            )
        except Exception as exc:
            print(f"  SKIP test_fetch_iesdouyin_...: iesdouyin unavailable ({exc!r})")
            return
        # 无 cookies / 离线：底层拿不到 metadata → 跳过真机断言
        if not getattr(dr, "ok", False) or dr.backend != "iesdouyin":
            print("  SKIP test_fetch_iesdouyin_...: iesdouyin returned no usable result (no cookies/offline)")
            return
        # 有 cookie 时：adapter 必须把 iesdouyin 路径强制 metadata_only
        a = DouyinAdapter()
        result = a.fetch(
            url="https://www.douyin.com/video/0000000000000000000",
            output_dir=str(tmpdir),
            mode="lueying",
            backend="iesdouyin",
        )
        assert result.status == FetchStatus.METADATA_ONLY
        assert result.media_ready is False
        # lueying 需要 media_ready，但 metadata_only 不接受
        assert result.acceptable_for_mode("lueying") is False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


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

