from collector.main import FETCHERS, notify_failure, run
from collector.models import HotspotItem


class FakeResponse:
    def raise_for_status(self):
        pass


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, timeout=None):
        self.calls.append(("get", url))
        return FakeResponse()

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(("post", url))
        return FakeResponse()


def _boom(session):
    raise RuntimeError("down")


def test_run_dry_run_prints_candidates(monkeypatch):
    item = HotspotItem("某女星同款穿搭", "weibo", 100, "https://example.com", "2026-08-11")
    monkeypatch.setitem(FETCHERS, "weibo", lambda session: [item])
    count = run(["weibo"], FakeSession(), "", "", "", "", dry_run=True)
    assert count == 0


def test_run_appends_only_fresh_items(monkeypatch):
    item = HotspotItem("某品牌新装", "baidu", 200, "https://example.com", "2026-08-11")
    monkeypatch.setitem(FETCHERS, "baidu", lambda session: [item])
    monkeypatch.setattr("collector.main.get_tenant_access_token", lambda *args: "tok")
    monkeypatch.setattr("collector.main.list_existing_keys", lambda *args: {"百度热搜:旧词"})
    monkeypatch.setattr("collector.main.append_records", lambda *args: 1)
    count = run(["baidu"], FakeSession(), "id", "secret", "app", "tbl")
    assert count == 1


def test_notify_failure_skips_empty_webhook():
    notify_failure("", RuntimeError("boom"), FakeSession())


def test_run_continues_after_source_failure(monkeypatch):
    monkeypatch.setitem(FETCHERS, "weibo", _boom)
    monkeypatch.setitem(
        FETCHERS,
        "baidu",
        lambda session: [HotspotItem("某品牌新装", "baidu", 200, "https://example.com", "2026-08-11")],
    )
    count = run(["weibo", "baidu"], FakeSession(), "", "", "", "", dry_run=True)
    assert count == 0


def test_run_raises_when_all_sources_fail(monkeypatch):
    monkeypatch.setitem(FETCHERS, "weibo", _boom)
    monkeypatch.setitem(FETCHERS, "baidu", _boom)
    try:
        run(["weibo", "baidu"], FakeSession(), "", "", "", "", dry_run=True)
    except RuntimeError as exc:
        assert "所有数据源均失败" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
