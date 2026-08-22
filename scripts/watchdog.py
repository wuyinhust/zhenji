"""Connection watchdog and recovery controller for zhenji V4.

The normal monitoring path is read-only. In AUTO_CONNECT mode it may perform a
pre-authorized recovery action only when the current screenshot/page classifier
explicitly identifies the mirroring recovery page. It never handles passwords,
unlock, verification codes, CAPTCHAs, or security challenges.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
import threading, time


class RecoveryMode(str, Enum):
    AUTO_CONNECT = "auto_connect"
    MANUAL = "manual"


class WatchdogState(str, Enum):
    INIT="INIT"; PREFLIGHT="PREFLIGHT"; READY="READY"; MONITORING="MONITORING"
    RECOVERY_PENDING="RECOVERY_PENDING"; INPUT_FROZEN="INPUT_FROZEN"; STOPPED="STOPPED"


@dataclass
class RuntimeHealth:
    state: WatchdogState = WatchdogState.INIT
    connection_state: str | None = None
    frontmost: bool | None = None
    window_bounds: dict[str, Any] | None = None
    page_state: str | None = None
    screenshot_path: str | None = None
    last_checked_at: float | None = None
    reason: str | None = None
    input_frozen: bool = True
    recovery_attempts: int = 0

    def to_dict(self):
        d = asdict(self)
        d["state"] = self.state.value
        return d


class InputGuard:
    def __init__(self, health: RuntimeHealth, lock: threading.RLock):
        self.health = health; self.lock = lock

    def assert_input_allowed(self):
        with self.lock:
            if self.health.input_frozen:
                raise RuntimeError(
                    f"input frozen: {self.health.state.value}; {self.health.reason}"
                )


class Watchdog:
    def __init__(
        self, *,
        connection_state_fn: Callable[[], Any],
        screen_info_fn: Callable[[], dict[str, Any]],
        screenshot_fn: Callable[[], Any],
        page_state_fn: Callable[[Any], str],
        checkpoint_fn: Callable[[dict[str, Any]], None],
        checkpoint_payload_fn: Callable[[], dict[str, Any]],
        recovery_mode: RecoveryMode = RecoveryMode.AUTO_CONNECT,
        auto_connect_fn: Optional[Callable[[Any], bool]] = None,
        poll_seconds: float = 5.0,
        recovery_backoff_seconds: tuple[float, ...] = (1.0, 3.0, 10.0),
    ):
        self.connection_state_fn=connection_state_fn; self.screen_info_fn=screen_info_fn
        self.screenshot_fn=screenshot_fn; self.page_state_fn=page_state_fn
        self.checkpoint_fn=checkpoint_fn; self.checkpoint_payload_fn=checkpoint_payload_fn
        self.recovery_mode=recovery_mode; self.auto_connect_fn=auto_connect_fn
        self.poll_seconds=poll_seconds; self.recovery_backoff_seconds=recovery_backoff_seconds
        self.lock=threading.RLock(); self.health=RuntimeHealth()
        self.guard=InputGuard(self.health,self.lock)
        self.stop_event=threading.Event(); self.thread=None

    def _set(self,state,frozen,reason=None):
        with self.lock:
            self.health.state=state; self.health.input_frozen=frozen
            self.health.reason=reason; self.health.last_checked_at=time.time()

    def _observe(self):
        raw=self.connection_state_fn()
        if isinstance(raw,str): conn=raw
        elif isinstance(raw,dict): conn=str(raw.get('state') or raw.get('status') or 'unknown')
        else: conn=str(raw)
        info=self.screen_info_fn() or {}; shot=self.screenshot_fn(); page=self.page_state_fn(shot)
        with self.lock:
            self.health.connection_state=conn; self.health.frontmost=info.get('frontmost')
            self.health.window_bounds=info.get('window_bounds') or info.get('bounds')
            self.health.page_state=page
            self.health.screenshot_path=str(shot) if isinstance(shot,(str,Path)) else None
            self.health.last_checked_at=time.time()
        return conn,info,shot,page

    @staticmethod
    def _unsafe_page(page):
        return page in {'SECURITY_CHALLENGE','LOGIN_REQUIRED','DEVICE_UNLOCK','PASSWORD','UNKNOWN_UNSAFE'}

    @classmethod
    def _ready(cls,conn,page):
        return conn=='ready' and not cls._unsafe_page(page) and page!='MIRROR_RECOVERY'

    def _freeze(self,reason):
        self._set(WatchdogState.INPUT_FROZEN,True,reason)
        payload=dict(self.checkpoint_payload_fn()); payload['watchdog']=self.health.to_dict()
        self.checkpoint_fn(payload)

    def _try_auto_recovery(self, shot, page) -> bool:
        if not (
            self.recovery_mode == RecoveryMode.AUTO_CONNECT
            and page == 'MIRROR_RECOVERY'
            and self.auto_connect_fn is not None
        ):
            return False
        self._set(WatchdogState.RECOVERY_PENDING,True,'mirror_recovery_detected')
        for delay in self.recovery_backoff_seconds:
            self.health.recovery_attempts += 1
            if self.auto_connect_fn(shot):
                time.sleep(delay)
                conn, _info, shot, page = self._observe()
                if self._ready(conn,page):
                    self._set(WatchdogState.READY,False)
                    return True
            else:
                time.sleep(delay)
                conn, _info, shot, page = self._observe()
                if self._ready(conn,page):
                    self._set(WatchdogState.READY,False)
                    return True
                if page != 'MIRROR_RECOVERY':
                    break
        return False

    def preflight(self):
        self._set(WatchdogState.PREFLIGHT,True)
        conn,_info,shot,page=self._observe()
        if self._ready(conn,page):
            self._set(WatchdogState.READY,False); return self.health
        if self._unsafe_page(page):
            self._freeze(f'unsafe_page:{conn}:{page}'); return self.health
        if self._try_auto_recovery(shot,page):
            return self.health
        self._freeze(f'preflight_failed:{conn}:{page}'); return self.health

    def poll_once(self):
        conn,_info,shot,page=self._observe()
        if self._ready(conn,page):
            self._set(WatchdogState.MONITORING,False); return self.health
        if self._unsafe_page(page):
            self._freeze(f'unsafe_page:{conn}:{page}'); return self.health
        if self._try_auto_recovery(shot,page):
            self._set(WatchdogState.MONITORING,False); return self.health
        self._freeze(f'unhealthy:{conn}:{page}'); return self.health

    def _run(self, skip_preflight=False):
        if not skip_preflight:
            self.preflight()
        while not self.stop_event.wait(self.poll_seconds):
            self.poll_once()

    def start(self, skip_preflight=False):
        if self.thread and self.thread.is_alive(): return
        self.stop_event.clear()
        self.thread=threading.Thread(
            target=self._run, kwargs={'skip_preflight': skip_preflight},
            name='zhenji-watchdog', daemon=True
        )
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=max(1.0,self.poll_seconds+1))
        self._set(WatchdogState.STOPPED,True)

    def resume_after_manual_recovery(self):
        return self.preflight()
