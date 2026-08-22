"""MediaFetchResult 语义测试 (V5.2 P0)。

核心：删除误导性的 `ok` 属性，业务层必须用
- succeeded               (status 不在 {FAILED, BLOCKED})
- acceptable_for_mode(m)  (对该档位"够用")
"""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from media_adapter_protocol import (
    FetchStatus,
    MediaFetchResult,
    MediaNotReadyError,
)


def test_ok_removed():
    r = MediaFetchResult("xhs", FetchStatus.METADATA_ONLY, "/tmp", [], {"t": 1})
    assert not hasattr(r, "ok"), "MediaFetchResult.ok 应已删除，禁止业务层继续使用"


def test_succeeded_true_for_metadata_only():
    r = MediaFetchResult("xhs", FetchStatus.METADATA_ONLY, "/tmp", [], {"t": 1})
    assert r.succeeded is True
    assert r.metadata_ready is True
    assert r.media_ready is False


def test_succeeded_false_for_failed_and_blocked():
    for st in (FetchStatus.FAILED, FetchStatus.BLOCKED):
        r = MediaFetchResult("xhs", st, "/tmp", [], None, error="x")
        assert r.succeeded is False


def test_succeeded_true_for_retryable_partial_ready():
    for st in (FetchStatus.RETRYABLE_ERROR, FetchStatus.PARTIAL, FetchStatus.MEDIA_READY):
        r = MediaFetchResult("xhs", st, "/tmp", [], {"t": 1})
        assert r.succeeded is True


def test_acceptable_for_mode():
    meta = MediaFetchResult("xhs", FetchStatus.METADATA_ONLY, "/tmp", [], {"t": 1})
    assert meta.acceptable_for_mode("fuguang") is True
    assert meta.acceptable_for_mode("lueying") is False
    assert meta.acceptable_for_mode("tinglan") is False
    assert meta.acceptable_for_mode("guanlan") is False

    ready = MediaFetchResult("xhs", FetchStatus.MEDIA_READY, "/tmp", ["/tmp/v.mp4"], {"t": 1})
    for m in ("fuguang", "lueying", "tinglan", "guanlan"):
        assert ready.acceptable_for_mode(m) is True


def test_media_not_ready_error_is_exception():
    assert issubclass(MediaNotReadyError, Exception)


def test_succeeded_vs_acceptable_distinct():
    # 核心区别：metadata_only 是 succeeded 但不是 acceptable(lueying)
    r = MediaFetchResult("xhs", FetchStatus.METADATA_ONLY, "/tmp", [], {"t": 1})
    assert r.succeeded and not r.acceptable_for_mode("lueying")


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
