"""Platform status declaration (Zhenji V5.2).

避免 router 支持被误读为业务支持：
- status: production   → adapter + 真机 recipe 就绪
- status: beta         → adapter 就绪，recipe 待校验/部分能力
- status: router_only  → 仅 URL router 识别，adapter/recipe 未实现

纯标准库解析（不依赖 PyYAML），loader 只为这种两级扁平结构服务。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "references" / "platform-status.yaml"


@dataclass(frozen=True)
class PlatformStatus:
    key: str
    status: str
    adapter: str
    notes: str

    @property
    def supported(self) -> bool:
        """router_only 不算业务支持。"""
        return self.status in ("production", "beta")

    @property
    def production_ready(self) -> bool:
        return self.status == "production"


def _parse_simple(text: str) -> dict[str, dict[str, str]]:
    """解析两级扁平 YAML（top: sub: value）。无 PyYAML 依赖。"""
    root: dict[str, dict[str, str]] = {}
    cur: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if " #" in line:
            line = line.split(" #", 1)[0].rstrip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            cur = key
            root[cur] = {}
        elif cur is not None:
            root[cur][key] = val
    return root


def load_status(platform: str, path: str | Path = DEFAULT_PATH) -> PlatformStatus | None:
    p = Path(path)
    if not p.exists():
        return None
    data = _parse_simple(p.read_text(encoding="utf-8"))
    entry = data.get(platform)
    if not isinstance(entry, dict):
        return None
    return PlatformStatus(
        key=platform,
        status=entry.get("status", "unknown"),
        adapter=entry.get("adapter", "unknown"),
        notes=entry.get("notes", ""),
    )


def all_statuses(path: str | Path = DEFAULT_PATH) -> dict[str, PlatformStatus]:
    p = Path(path)
    if not p.exists():
        return {}
    data = _parse_simple(p.read_text(encoding="utf-8"))
    return {
        k: PlatformStatus(
            key=k,
            status=v.get("status", "unknown"),
            adapter=v.get("adapter", "unknown"),
            notes=v.get("notes", ""),
        )
        for k, v in data.items()
    }
