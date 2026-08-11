from __future__ import annotations

import argparse
import os
import sys

import requests

from collector.filter import filter_by_keywords
from collector.feishu import (
    SOURCE_LABELS,
    append_records,
    get_tenant_access_token,
    list_existing_keys,
)
from collector.sources.baidu import fetch_baidu
from collector.sources.weibo import fetch_weibo

FETCHERS = {"weibo": fetch_weibo, "baidu": fetch_baidu}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://weibo.com/",
}


def run(
    sources: list[str],
    session: requests.Session,
    app_id: str,
    app_secret: str,
    app_token: str,
    table_id: str,
    dry_run: bool = False,
) -> int:
    all_items = []
    errors = []
    for name in sources:
        try:
            all_items.extend(FETCHERS[name](session))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")
            print(f"跳过数据源 {name}: {exc}", file=sys.stderr)
    if not all_items and errors:
        raise RuntimeError("所有数据源均失败: " + "; ".join(errors))
    candidates = filter_by_keywords(all_items)
    if dry_run:
        for item in candidates:
            print(f"[{item.source}] {item.topic} ({item.heat})")
        return 0
    access_token = get_tenant_access_token(app_id, app_secret, session)
    existing = list_existing_keys(app_token, table_id, access_token, session)
    fresh = [
        item
        for item in candidates
        if f"{SOURCE_LABELS[item.source]}:{item.topic}" not in existing
    ]
    created = append_records(app_token, table_id, access_token, fresh, session)
    print(f"candidates={len(candidates)} fresh={len(fresh)} created={created}")
    return created


def notify_failure(webhook: str, error: Exception, session: requests.Session) -> None:
    if not webhook:
        return
    session.post(
        webhook,
        json={"msg_type": "text", "content": {"text": f"热点采集失败: {error}"}},
        timeout=15,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="采集公开榜单并写入飞书热点主题表")
    parser.add_argument("--sources", default="weibo,baidu", help="逗号分隔的数据源列表")
    parser.add_argument("--dry-run", action="store_true", help="只打印候选词，不写入飞书")
    args = parser.parse_args(argv)
    sources = [name.strip() for name in args.sources.split(",") if name.strip()]
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    try:
        if args.dry_run:
            run(sources, session, "", "", "", "", dry_run=True)
        else:
            run(
                sources,
                session,
                os.environ["FEISHU_APP_ID"],
                os.environ["FEISHU_APP_SECRET"],
                os.environ["FEISHU_APP_TOKEN"],
                os.environ["FEISHU_HOTSPOT_TABLE_ID"],
            )
    except Exception as exc:  # noqa: BLE001
        notify_failure(os.environ.get("FEISHU_WEBHOOK", ""), exc, session)
        print(f"采集失败: {exc}", file=sys.stderr)
        return 1
    return 0
