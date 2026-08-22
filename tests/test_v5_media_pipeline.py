from __future__ import annotations

import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from clipboard_link import extract_platform_url, fingerprint
from media_queue import MediaQueue
from platform_router import route_url
from share_link_flow import harvest_share_link


def test_url_extract():
    text = "复制这条笔记 https://xhslink.com/a/abc123 打开小红书"
    assert extract_platform_url(text, "xhs") == "https://xhslink.com/a/abc123"
    assert route_url("https://www.xiaohongshu.com/explore/123").key == "xhs"


def test_queue_dedupe_and_claim():
    with tempfile.TemporaryDirectory() as td:
        q = MediaQueue(Path(td) / "jobs.sqlite3")
        a = q.enqueue(
            platform="xhs",
            post_key="p1",
            source_url="https://xhslink.com/a/a",
            mode="lueying",
        )
        b = q.enqueue(
            platform="xhs",
            post_key="p1",
            source_url="https://xhslink.com/a/a",
            mode="lueying",
        )
        assert a == b
        job = q.claim_next()
        assert job is not None
        assert job.job_id == a
        assert job.state == "downloading"


def test_harvest_rejects_old_clipboard():
    values = iter([
        "https://xhslink.com/a/old",
        "https://xhslink.com/a/old",
        "https://xhslink.com/a/old",
    ])
    def read():
        try:
            return next(values)
        except StopIteration:
            return "https://xhslink.com/a/old"

    result = harvest_share_link(
        open_share_action=lambda: None,
        copy_link_action=lambda: None,
        expected_platform="xhs",
        max_copy_retries=0,
        clipboard_read_fn=read,
        timeout_seconds=0.02,
        poll_interval_seconds=0.001,
    )
    assert not result.ok
    assert result.error == "clipboard_unchanged"


def test_harvest_accepts_changed_and_probed():
    values = iter([
        "old clipboard",
        "复制 https://xhslink.com/a/new",
    ])
    def read():
        try:
            return next(values)
        except StopIteration:
            return "复制 https://xhslink.com/a/new"

    result = harvest_share_link(
        open_share_action=lambda: None,
        copy_link_action=lambda: None,
        probe_fn=lambda url: {"id": "abc", "duration": 12.0},
        expected_platform="xhs",
        expected_post_hint={"note_type": "video"},
        max_copy_retries=0,
        clipboard_read_fn=read,
        timeout_seconds=0.1,
        poll_interval_seconds=0.001,
    )
    assert result.ok
    assert result.url == "https://xhslink.com/a/new"


if __name__ == "__main__":
    test_url_extract()
    test_queue_dedupe_and_claim()
    test_harvest_rejects_old_clipboard()
    test_harvest_accepts_changed_and_probed()
    print("V5 media tests passed")
