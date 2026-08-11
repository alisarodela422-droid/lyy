from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class HotspotItem:
    topic: str
    source: str
    heat: int
    url: str
    fetched_at: str


def today_iso() -> str:
    return date.today().isoformat()


def heat_level(heat: int) -> str:
    if heat >= 1_000_000:
        return "S"
    if heat >= 500_000:
        return "A"
    if heat >= 100_000:
        return "B"
    return "C"
