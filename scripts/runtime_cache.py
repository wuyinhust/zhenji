"""Runtime caches for Zhenji.

Pure helper module: it does not control a phone by itself. The platform adapter
supplies screenshot/OCR functions and calls mark_dirty() after viewport changes.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable
import time


@dataclass
class Observation:
    generation: int
    screenshot: Any
    ocr_rows: list[dict[str, Any]]
    page_type: str | None = None
    anchors: dict[str, Any] = field(default_factory=dict)
    card_layout: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class ObservationSession:
    """Guarantee at most one expensive OCR per stable viewport generation."""

    def __init__(self) -> None:
        self.generation = 0
        self._cached: Observation | None = None
        self.ocr_calls = 0
        self.cache_hits = 0
        self.dirty_reasons: list[str] = []

    def mark_dirty(self, reason: str) -> None:
        self.generation += 1
        self._cached = None
        self.dirty_reasons.append(reason)

    def observe(
        self,
        screenshot_fn: Callable[[], Any],
        ocr_fn: Callable[[Any], list[dict[str, Any]]],
        classify_fn: Callable[[list[dict[str, Any]]], str] | None = None,
    ) -> Observation:
        if self._cached is not None and self._cached.generation == self.generation:
            self.cache_hits += 1
            return self._cached

        screenshot = screenshot_fn()
        rows = ocr_fn(screenshot)
        self.ocr_calls += 1
        page_type = classify_fn(rows) if classify_fn else None
        self._cached = Observation(
            generation=self.generation,
            screenshot=screenshot,
            ocr_rows=rows,
            page_type=page_type,
        )
        return self._cached


@dataclass
class CardMap:
    page_type: str
    screen_size: tuple[int, int]
    column_centers: list[float]
    row_centers: list[float]
    card_size: tuple[float, float] | None = None
    anchors: tuple[str, ...] = ()
    confidence: float = 0.0
    hits: int = 0
    rebuilds: int = 0


class CardMapCache:
    """Session-scoped layout cache. Coordinates are normalized 0..1."""

    def __init__(self) -> None:
        self._maps: dict[tuple[str, tuple[int, int]], CardMap] = {}

    def put(self, card_map: CardMap) -> None:
        key = (card_map.page_type, card_map.screen_size)
        old = self._maps.get(key)
        card_map.rebuilds = (old.rebuilds + 1) if old else 1
        self._maps[key] = card_map

    def get(
        self,
        page_type: str,
        screen_size: tuple[int, int],
        validator: Callable[[CardMap], bool] | None = None,
    ) -> CardMap | None:
        m = self._maps.get((page_type, screen_size))
        if m is None:
            return None
        if validator is not None and not validator(m):
            return None
        m.hits += 1
        return m

    def invalidate(self, page_type: str | None = None) -> None:
        if page_type is None:
            self._maps.clear()
            return
        for key in [k for k in self._maps if k[0] == page_type]:
            self._maps.pop(key, None)
