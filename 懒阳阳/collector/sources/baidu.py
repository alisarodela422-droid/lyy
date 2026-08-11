from __future__ import annotations

from urllib.parse import quote

import requests

from collector.models import HotspotItem, today_iso

BOARD_URL = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
SEARCH_URL_TEMPLATE = "https://www.baidu.com/s?wd={}"


def fetch_baidu(session: requests.Session) -> list[HotspotItem]:
    resp = session.get(BOARD_URL, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    items = []
    for card in payload.get("data", {}).get("cards", []):
        for section in card.get("content", []):
            for entry in section.get("content", []):
                topic = entry.get("word")
                if not topic:
                    continue
                url = entry.get("url") or SEARCH_URL_TEMPLATE.format(quote(topic))
                items.append(
                    HotspotItem(
                        topic=topic,
                        source="baidu",
                        heat=int(entry.get("hotScore") or 0),
                        url=url,
                        fetched_at=today_iso(),
                    )
                )
    return items
