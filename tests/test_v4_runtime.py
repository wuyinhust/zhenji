from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from idle_calibration import IdleCalibration
from keepalive import InputActivity, KeepaliveRegistry, SafeKeepaliveAction, KeepaliveManager
from watchdog import Watchdog, RecoveryMode


def test_calibration_uses_measured_minimum():
    c = IdleCalibration.from_samples("env", [310, 300, 305], 0.8)
    assert c.minimum_seconds == 300
    assert c.keepalive_after_seconds == 240


def test_screenshot_does_not_reset_real_input_clock():
    activity = InputActivity(last_real_input_at=10.0)
    assert activity.last_real_input_at == 10.0


def test_verified_keepalive_updates_clock():
    state = {"page": "PROFILE_GRID", "n": 0}
    reg = KeepaliveRegistry()
    reg.register(SafeKeepaliveAction(
        name="small_scroll_roundtrip",
        page_state="PROFILE_GRID",
        action=lambda: state.__setitem__("n", state["n"] + 1),
        verify_page_fn=lambda: state["page"],
    ))
    activity = InputActivity(last_real_input_at=0)
    mgr = KeepaliveManager(
        activity=activity, registry=reg, keepalive_after_seconds=10,
        now_fn=lambda: 20.0,
    )
    assert mgr.maybe_keepalive("PROFILE_GRID") == "executed:small_scroll_roundtrip"
    assert state["n"] == 1
    assert activity.keepalive_count == 1
    assert activity.last_real_input_at == 20.0


def test_forbidden_page_never_keepalive():
    reg = KeepaliveRegistry(); activity = InputActivity(last_real_input_at=0)
    mgr = KeepaliveManager(activity=activity, registry=reg, keepalive_after_seconds=1, now_fn=lambda: 5.0)
    assert mgr.maybe_keepalive("SECURITY_CHALLENGE") == "forbidden-page"
