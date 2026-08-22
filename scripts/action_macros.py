"""Declarative macro learning for repeated read-only phone actions."""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Callable
import json

READ_ONLY_ALLOWLIST = {
    "observe",
    "scan_visible_cards",
    "tap_card",
    "tap_text",
    "scroll",
    "wait_stable",
    "verify_page",
    "back",
    "open_search",
    "type_search_query",
    "open_profile",
    "open_comments",
}

FORBIDDEN = {
    "like", "favorite", "follow", "comment", "reply", "dm", "publish", "purchase"
}


@dataclass
class Macro:
    name: str
    platform: str
    precondition: str
    steps: list[dict[str, Any]]
    postcondition: str
    success_count: int = 0
    failure_count: int = 0
    status: str = "experimental"

    def validate_safety(self) -> None:
        for step in self.steps:
            action = step.get("action")
            if action in FORBIDDEN or action not in READ_ONLY_ALLOWLIST:
                raise ValueError(f"action is not eligible for learned macro: {action}")


class MacroRegistry:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.macros: dict[str, Macro] = {}
        self.sequence_counts: dict[str, int] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.sequence_counts = data.get("sequence_counts", {})
        for item in data.get("macros", []):
            m = Macro(**item)
            self.macros[m.name] = m

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sequence_counts": self.sequence_counts,
            "macros": [asdict(m) for m in self.macros.values()],
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def signature(platform: str, precondition: str, steps: list[dict[str, Any]], postcondition: str) -> str:
        actions = [str(s.get("action")) for s in steps]
        return "|".join([platform, precondition, *actions, postcondition])

    def observe_successful_sequence(
        self,
        *,
        name: str,
        platform: str,
        precondition: str,
        steps: list[dict[str, Any]],
        postcondition: str,
        promote_after: int = 3,
    ) -> Macro | None:
        candidate = Macro(name, platform, precondition, steps, postcondition)
        candidate.validate_safety()
        sig = self.signature(platform, precondition, steps, postcondition)
        self.sequence_counts[sig] = self.sequence_counts.get(sig, 0) + 1
        if self.sequence_counts[sig] < promote_after:
            self.save()
            return None
        macro = self.macros.get(name) or candidate
        macro.status = "active"
        macro.success_count += 1
        self.macros[name] = macro
        self.save()
        return macro

    def report_result(self, name: str, success: bool) -> None:
        macro = self.macros[name]
        if success:
            macro.success_count += 1
            macro.failure_count = 0
        else:
            macro.failure_count += 1
            if macro.failure_count >= 2:
                macro.status = "stale"
        self.save()


class MacroExecutor:
    def __init__(self, actions: dict[str, Callable[..., Any]]) -> None:
        self.actions = actions

    def run(self, macro: Macro, variables: dict[str, Any] | None = None) -> None:
        macro.validate_safety()
        variables = variables or {}
        for step in macro.steps:
            action_name = step["action"]
            fn = self.actions[action_name]
            arg = step.get("arg")
            if isinstance(arg, str) and arg.startswith("$"):
                arg = variables[arg[1:]]
            if "arg" in step:
                fn(arg)
            else:
                fn()
