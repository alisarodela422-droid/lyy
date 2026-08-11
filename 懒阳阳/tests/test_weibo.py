import json
from pathlib import Path
from urllib.parse import quote

from collector.sources import weibo as weibo_module

FIXTURE = Path(__file__).parent / "fixtures" / "weibo_hot_search.json"


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self._payload = payload

    def get(self, url, timeout):
        assert url == weibo_module.HOT_SEARCH_URL
        return FakeResponse(self._payload)


def test_fetch_weibo_parses_items(monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    monkeypatch.setattr(weibo_module, "today_iso", lambda: "2026-08-11")
    items = weibo_module.fetch_weibo(FakeSession(payload))
    assert len(items) == 2
    assert items[0].topic == "某女星同款穿搭"
    assert items[0].heat == 1234567
    assert items[0].source == "weibo"
    assert items[0].fetched_at == "2026-08-11"
    assert quote("某女星同款穿搭") in items[0].url
    assert items[1].heat == 99999
