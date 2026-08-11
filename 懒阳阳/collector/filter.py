from __future__ import annotations

from collections.abc import Iterable, Sequence

from collector.models import HotspotItem

DEFAULT_KEYWORDS = [
    "穿搭", "女装", "造型", "同款", "街拍", "时尚",
    "艺人", "明星", "品牌", "连衣裙", "大衣", "风衣",
    "衬衫", "外套", "套装", "新中式", "小香风", "通勤", "中女",
]


def filter_by_keywords(
    items: Iterable[HotspotItem],
    keywords: Sequence[str] = DEFAULT_KEYWORDS,
) -> list[HotspotItem]:
    return [item for item in items if any(kw in item.topic for kw in keywords)]
