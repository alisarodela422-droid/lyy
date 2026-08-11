from collector.filter import filter_by_keywords
from collector.models import HotspotItem


def _item(topic: str) -> HotspotItem:
    return HotspotItem(topic, "weibo", 1, "https://example.com", "2026-08-11")


def test_filters_topics_matching_any_keyword():
    items = [_item("某女星同款穿搭"), _item("普通新闻"), _item("秋冬大衣")]
    result = filter_by_keywords(items)
    assert [item.topic for item in result] == ["某女星同款穿搭", "秋冬大衣"]
