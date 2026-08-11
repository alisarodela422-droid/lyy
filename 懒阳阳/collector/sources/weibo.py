from __future__ import annotations

from urllib.parse import quote

import requests

from collector.models import HotspotItem, today_iso

HOT_SEARCH_URL = "https://weibo.com/ajax/side/hotSearch"
SEARCH_URL_TEMPLATE = "https://s.weibo.com/weibo?q={}"


def fetch_weibo(session: requests.Session) -> list[HotspotItem]:
    resp = session.get(HOT_SEARCH_URL, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    items = []
    for entry in payload.get("data", {}).get("realtime", []):
        topic = entry.get("word")
        if not topic:
            continue
        items.append(
            HotspotItem(
                topic=topic,
                source="weibo",
                heat=int(entry.get("num") or 0),
                url=SEARCH_URL_TEMPLATE.format(quote(topic)),
                fetched_at=today_iso(),
            )
        )
    return items
