# -*- coding: utf-8 -*-
"""飞书合作表定时提醒脚本

每天定时运行，查询合作表，找出当天要拍摄、当天要发布的品牌，
通过群机器人 webhook 推送到「懒阳阳工作群」。

自动探测表名和字段名，无需手填表 ID 和字段名。
需要的环境变量：
    FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_APP_TOKEN
    FEISHU_WEBHOOK          群机器人 webhook 地址
可选：
    FEISHU_DAYS_AHEAD       提前几天提醒，默认 0（当天）
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

import requests


TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
TABLES_URL = "https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
FIELDS_URL = "https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
RECORDS_URL = "https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _check(payload: dict, action: str) -> None:
    if payload.get("code") != 0:
        raise RuntimeError(f"{action} failed [{payload.get('code')}]: {payload.get('msg', payload)}")


def get_token(app_id: str, app_secret: str, session: requests.Session) -> str:
    r = session.post(TOKEN_URL, json={"app_id": app_id, "app_secret": app_secret}, timeout=15)
    r.raise_for_status()
    p = r.json()
    _check(p, "获取 token")
    return p["tenant_access_token"]


def find_table_id(app_token: str, token: str, session: requests.Session, keyword: str) -> str | None:
    r = session.get(TABLES_URL.format(app_token=app_token), params={"page_size": 100}, headers=_headers(token), timeout=15)
    r.raise_for_status()
    p = r.json()
    _check(p, "列出数据表")
    for t in p.get("data", {}).get("items", []):
        if keyword in (t.get("name") or ""):
            return t.get("table_id")
    return None


def list_fields(app_token: str, table_id: str, token: str, session: requests.Session) -> list[dict]:
    r = session.get(FIELDS_URL.format(app_token=app_token, table_id=table_id), params={"page_size": 100}, headers=_headers(token), timeout=15)
    r.raise_for_status()
    p = r.json()
    _check(p, "列出字段")
    items = p.get("data", {}).get("items", [])
    return [{"name": f.get("field_name"), "type": f.get("type")} for f in items]


def list_records(app_token: str, table_id: str, token: str, session: requests.Session) -> list[dict]:
    records = []
    page_token = None
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        r = session.get(RECORDS_URL.format(app_token=app_token, table_id=table_id), params=params, headers=_headers(token), timeout=15)
        r.raise_for_status()
        p = r.json()
        _check(p, "读取记录")
        data = p.get("data", {})
        records.extend(data.get("items", []))
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
    return records


def parse_date(value) -> datetime | None:
    """解析日期字段值，兼容毫秒时间戳和常见文本格式"""
    if value is None:
        return None
    # 毫秒时间戳（日期字段类型返回整数）
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000)
        except (ValueError, OSError):
            return None
    # 文本格式
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                pass
        # 带时间的 ISO 格式
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return None


def find_field(fields: list[dict], predicate) -> str | None:
    for f in fields:
        if predicate(f.get("name", "")):
            return f["name"]
    return None


def get_text(value) -> str:
    """把字段值转成文本（兼容数组、文本、数字）"""
    if value is None:
        return ""
    if isinstance(value, list):
        parts = []
        for v in value:
            if isinstance(v, dict):
                parts.append(v.get("text", v.get("name", str(v))))
            else:
                parts.append(str(v))
        return " ".join(parts)
    if isinstance(value, dict):
        return value.get("text", value.get("name", str(value)))
    return str(value)


def send_webhook(webhook: str, text: str, session: requests.Session) -> None:
    if not webhook:
        print("[提示] 未配置 FEISHU_WEBHOOK，跳过推送，消息内容如下：")
        print(text)
        return
    r = session.post(webhook, json={"msg_type": "text", "content": {"text": text}}, timeout=15)
    r.raise_for_status()
    p = r.json()
    if p.get("code") != 0 and p.get("StatusCode") not in (0, None):
        raise RuntimeError(f"推送失败: {p}")


def main() -> int:
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    app_token = os.environ.get("FEISHU_APP_TOKEN", "")
    webhook = os.environ.get("FEISHU_WEBHOOK", "")
    days_ahead = int(os.environ.get("FEISHU_DAYS_AHEAD", "0"))

    if not all([app_id, app_secret, app_token]):
        print("[错误] 缺少环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_APP_TOKEN")
        return 1

    session = requests.Session()
    token = get_token(app_id, app_secret, session)

    # 自动找合作表
    table_id = find_table_id(app_token, token, session, "合作")
    if not table_id:
        print("[错误] 找不到名称含「合作」的表")
        return 1
    print(f"[定位] 合作表 ID: {table_id}")

    # 列出字段，自动探测
    fields = list_fields(app_token, table_id, token, session)
    shoot_field = find_field(fields, lambda n: "拍摄" in n and "日期" in n) or find_field(fields, lambda n: "拍摄" in n)
    publish_field = find_field(fields, lambda n: "发布" in n and "日期" in n)
    brand_field = find_field(fields, lambda n: "品牌" in n)
    print(f"[字段] 拍摄日期={shoot_field} 发布日期={publish_field} 品牌={brand_field}")

    if not shoot_field and not publish_field:
        print("[错误] 找不到「拍摄日期」或「发布日期」字段")
        return 1

    # 读取所有记录
    records = list_records(app_token, table_id, token, session)

    # 目标日期
    target = datetime.now() + timedelta(days=days_ahead)
    target_date = target.date()

    to_shoot = []
    to_publish = []
    for r in records:
        f = r.get("fields", {})
        brand = get_text(f.get(brand_field)) if brand_field else "（未填品牌）"

        if shoot_field:
            d = parse_date(f.get(shoot_field))
            if d and d.date() == target_date:
                to_shoot.append(brand)

        if publish_field:
            d = parse_date(f.get(publish_field))
            if d and d.date() == target_date:
                to_publish.append(brand)

    # 组装消息
    lines = []
    if to_shoot:
        if days_ahead > 0:
            lines.append(f"【拍摄提醒】{days_ahead} 天后（{target_date}）要拍摄 {len(to_shoot)} 个品牌：")
        else:
            lines.append(f"【拍摄提醒】今天（{target_date}）要拍摄 {len(to_shoot)} 个品牌：")
        for b in to_shoot:
            lines.append(f"  - {b}")
    if to_publish:
        if days_ahead > 0:
            lines.append(f"【发布提醒】{days_ahead} 天后（{target_date}）要发布 {len(to_publish)} 个品牌：")
        else:
            lines.append(f"【发布提醒】今天（{target_date}）要发布 {len(to_publish)} 个品牌：")
        for b in to_publish:
            lines.append(f"  - {b}")

    if not lines:
        print(f"[结果] {target_date} 无拍摄/发布任务，不推送")
        return 0

    text = "\n".join(lines)
    print(f"[结果] {target_date} 有 {len(to_shoot)} 个拍摄、{len(to_publish)} 个发布任务")
    print("[推送] 发送到工作群：")
    print(text)

    send_webhook(webhook, text, session)
    print("[完成] 推送成功")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
