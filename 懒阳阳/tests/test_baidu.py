import json
from pathlib import Path
from urllib.parse import quote

from collector.sources import baidu as baidu_module

FIXTURE = Path(__file__).parent / "fixtures" / "baidu_board.json"


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
        assert url == baidu_module.BOARD_URL
        return FakeResponse(self._payload)


def test_fetch_baidu_parses_items(monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    monkeypatch.setattr(baidu_module, "today_iso", lambda: "2026-08-11")
    items = baidu_module.fetch_baidu(FakeSession(payload))
    assert len(items) == 2
    assert items[0].topic == "某品牌秋冬新品"
    assert items[0].heat == 2345678
    assert items[0].source == "baidu"
    assert items[0].url.startswith("https://www.baidu.com")
    assert items[1].url == "https://www.baidu.com/s?wd=" + quote("普通新闻词")
