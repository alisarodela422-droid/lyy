from __future__ import annotations

import requests

from collector.models import HotspotItem, heat_level

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
RECORDS_URL = (
    "https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
)

SOURCE_LABELS = {"weibo": "微博热搜", "baidu": "百度热搜", "douyin": "抖音热榜"}


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _raise_for_error(payload: dict, action: str) -> None:
    if payload.get("code") != 0:
        raise RuntimeError(f"{action} failed: {payload.get('msg', payload)}")


def get_tenant_access_token(
    app_id: str, app_secret: str, session: requests.Session
) -> str:
    resp = session.post(
        TOKEN_URL, json={"app_id": app_id, "app_secret": app_secret}, timeout=15
    )
    resp.raise_for_status()
    payload = resp.json()
    _raise_for_error(payload, "token")
    return payload["tenant_access_token"]


def list_existing_keys(
    app_token: str, table_id: str, access_token: str, session: requests.Session
) -> set[str]:
    keys: set[str] = set()
    page_token: str | None = None
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        resp = session.get(
            RECORDS_URL.format(app_token=app_token, table_id=table_id),
            params=params,
            headers=_headers(access_token),
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        _raise_for_error(payload, "list records")
        data = payload.get("data", {})
        for record in data.get("items", []):
            fields = record.get("fields", {})
            topic = fields.get("主题")
            source = fields.get("来源")
            if topic and source:
                keys.add(f"{source}:{topic}")
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
    return keys


def append_records(
    app_token: str,
    table_id: str,
    access_token: str,
    items: list[HotspotItem],
    session: requests.Session,
) -> int:
    created = 0
    for item in items:
        fields = {
            "主题": item.topic,
            "类型": "平台话题",
            "话题词 | Tag": [item.topic],
            "热度等级": heat_level(item.heat),
            "来源": SOURCE_LABELS[item.source],
            "参考链接": item.url,
            "状态": "灵感",
        }
        resp = session.post(
            RECORDS_URL.format(app_token=app_token, table_id=table_id),
            json={"fields": fields},
            headers=_headers(access_token),
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        _raise_for_error(payload, "append record")
        created += 1
    return created
