from collector.models import HotspotItem, heat_level, today_iso


def test_hotspot_item_fields():
    item = HotspotItem("某穿搭词", "weibo", 100, "https://example.com", "2026-08-11")
    assert item.topic == "某穿搭词"
    assert item.source == "weibo"
    assert item.heat == 100
    assert item.url == "https://example.com"
    assert item.fetched_at == "2026-08-11"


def test_heat_level_thresholds():
    assert heat_level(1_000_000) == "S"
    assert heat_level(500_000) == "A"
    assert heat_level(100_000) == "B"
    assert heat_level(99_999) == "C"


def test_today_iso_format():
    value = today_iso()
    parts = value.split("-")
    assert len(parts) == 3
    assert len(parts[0]) == 4
