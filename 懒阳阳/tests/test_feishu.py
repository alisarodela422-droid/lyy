from collector.feishu import (
    RECORDS_URL,
    TOKEN_URL,
    append_records,
    get_tenant_access_token,
    list_existing_keys,
)
from collector.models import HotspotItem


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(("post", url, json))
        return FakeResponse(self.responses.pop(0))

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(("get", url, params))
        return FakeResponse(self.responses.pop(0))


def test_get_tenant_access_token():
    session = FakeSession([{"code": 0, "tenant_access_token": "tok"}])
    token = get_tenant_access_token("id", "secret", session)
    assert token == "tok"
    assert session.calls[0] == ("post", TOKEN_URL, {"app_id": "id", "app_secret": "secret"})


def test_list_existing_keys():
    payload = {
        "code": 0,
        "data": {
            "items": [
                {"fields": {"主题": "某词", "来源": "微博热搜"}},
                {"fields": {"主题": "另一词", "来源": "百度热搜"}},
            ],
            "has_more": False,
        },
    }
    session = FakeSession([payload])
    keys = list_existing_keys("app", "tbl", "tok", session)
    assert keys == {"微博热搜:某词", "百度热搜:另一词"}


def test_append_records_maps_fields():
    item = HotspotItem("某穿搭词", "weibo", 1500000, "https://example.com", "2026-08-11")
    session = FakeSession([{"code": 0, "data": {"record": {"record_id": "rec1"}}}])
    created = append_records("app", "tbl", "tok", [item], session)
    assert created == 1
    _, url, body = session.calls[0]
    assert url == RECORDS_URL.format(app_token="app", table_id="tbl")
    assert body["fields"]["主题"] == "某穿搭词"
    assert body["fields"]["类型"] == "平台话题"
    assert body["fields"]["话题词 | Tag"] == ["某穿搭词"]
    assert body["fields"]["热度等级"] == "S"
    assert body["fields"]["来源"] == "微博热搜"
    assert body["fields"]["参考链接"] == "https://example.com"
    assert body["fields"]["状态"] == "灵感"
