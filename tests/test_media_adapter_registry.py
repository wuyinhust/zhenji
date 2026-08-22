"""media_adapters 注册表测试 (V5.1.2 P1.10)。

覆盖：
- 默认注册 xhs / douyin
- get() 已知/未知平台返回
- register() / unregister() 行为
- register() 拒绝非 MediaAdapter 对象（TypeError）
- supported_keys() 仅返回 media_ready_supported=True 的平台
- MediaAdapter 是 runtime_checkable Protocol（无需显式子类化即可 isinstance True）
- MediaFetchResult.acceptable_for_mode() 按四档要求判定

注意：xhs_media / douyin_media 均为标准库实现，本测试无网络/无三方依赖。
"""
import sys
from pathlib import Path

# 允许独立运行：把 scripts/ 加进 PYTHONPATH
SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from media_adapter_protocol import (
    MediaAdapter,
    FetchStatus,
    MediaFetchResult,
    ResolvedURL,
)

import media_adapters as m


def test_default_registration():
    keys = set(m.keys())
    assert "xhs" in keys
    assert "douyin" in keys


def test_get_known_and_unknown():
    assert m.get("xhs") is not None
    assert m.get("douyin") is not None
    # 未知平台返回 None（worker 自决），不抛异常
    assert m.get("instagram") is None
    assert m.get("does-not-exist") is None


def test_register_unregister_custom():
    class FakeAdapter:
        key = "fake123"

        def normalize_url(self, url: str) -> str:
            return url

        def resolve_url(self, url: str) -> ResolvedURL:
            return ResolvedURL(url, url, "id", self.key)

        def probe(self, url: str, **kw):
            return {}

        def fetch(self, url, *, output_dir, mode, backend="auto", **kw):
            return MediaFetchResult(
                self.key, FetchStatus.METADATA_ONLY, output_dir, [], None
            )

        def capabilities(self):
            return {
                "metadata_only_supported": True,
                "media_ready_supported": False,
                "requires_login": False,
            }

    inst = FakeAdapter()
    # runtime_checkable：无需显式 subclass MediaAdapter
    assert isinstance(inst, MediaAdapter)

    m.register(inst)
    assert m.get("fake123") is inst
    m.unregister("fake123")
    assert m.get("fake123") is None


def test_register_rejects_non_adapter():
    try:
        m.register(object())
    except TypeError:
        pass
    else:
        raise AssertionError("register(non-adapter) should raise TypeError")


def test_supported_keys_only_media_ready():
    sup = set(m.supported_keys())
    # xhs / douyin 均声明 media_ready_supported=True
    assert "xhs" in sup
    assert "douyin" in sup


def test_result_acceptable_for_mode():
    r_meta = MediaFetchResult(
        "xhs", FetchStatus.METADATA_ONLY, "/tmp", [], {"t": 1}
    )
    assert r_meta.acceptable_for_mode("fuguang") is True
    assert r_meta.acceptable_for_mode("lueying") is False
    assert r_meta.acceptable_for_mode("guanlan") is False

    r_ready = MediaFetchResult(
        "xhs", FetchStatus.MEDIA_READY, "/tmp", ["/tmp/a.mp4"], {"t": 1}
    )
    assert r_ready.acceptable_for_mode("lueying") is True
    assert r_ready.acceptable_for_mode("tinglan") is True
    assert r_ready.acceptable_for_mode("guanlan") is True


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
