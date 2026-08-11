# -*- coding: utf-8 -*-
"""灰豚数据 CSV → 飞书多维表格 本地导入脚本
 
用法:
    python -m collector.huitun_import              # 扫描下载文件夹，列出 CSV
    python -m collector.huitun_import --watch      # 持续监控下载文件夹
    python -m collector.huitun_import --file path/to/xxx.csv   # 指定文件导入
 
前提:
    需要设置环境变量 FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN
    以及 FEISHU_HOTSPOT_TABLE_ID, FEISHU_BRAND_TABLE_ID
"""
 
from __future__ import annotations
 
import argparse
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path
 
import requests
 
 
# ─── 飞书 API ──────────────────────────────────────────
TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
RECORDS_URL = (
    "https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
)
 
 
def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
 
 
def _raise_for_error(payload: dict, action: str) -> None:
    if payload.get("code") != 0:
        raise RuntimeError(f"{action} failed [{payload.get('code')}]: {payload.get('msg', payload)}")
 
 
def get_tenant_access_token(app_id: str, app_secret: str, session: requests.Session) -> str:
    resp = session.post(
        TOKEN_URL, json={"app_id": app_id, "app_secret": app_secret}, timeout=15
    )
    resp.raise_for_status()
    payload = resp.json()
    _raise_for_error(payload, "获取飞书 token")
    return payload["tenant_access_token"]
 
 
def list_existing_records(
    app_token: str, table_id: str, access_token: str, session: requests.Session,
    key_field: str = "主题",
) -> list[dict]:
    """列出表中所有记录，返回 [{"id": record_id, "fields": {...}}, ...]"""
    records = []
    page_token = None
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
        _raise_for_error(payload, "读取飞书记录")
        data = payload.get("data", {})
        records.extend(data.get("items", []))
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
    return records
 
 
def create_record(
    app_token: str, table_id: str, access_token: str,
    fields: dict, session: requests.Session,
) -> bool:
    resp = session.post(
        RECORDS_URL.format(app_token=app_token, table_id=table_id),
        json={"fields": fields},
        headers=_headers(access_token),
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    _raise_for_error(payload, "写入飞书记录")
    return True
 
 
# ─── CSV 检测与解析 ────────────────────────────────────
 
HOTSPOT_HEADERS = {"主题", "热度", "来源", "话题"}
BRAND_HEADERS = {"品牌", "热度", "涨粉", "相关笔记", "是否适合"}
 
 
def guess_csv_type(headers: list[str]) -> str:
    """根据列名判断 CSV 类型: hotspot / brand / unknown"""
    header_set = {h.strip() for h in headers}
    hotspot_score = len(HOTSPOT_HEADERS & header_set)
    brand_score = len(BRAND_HEADERS & header_set)
    if hotspot_score >= 2 and hotspot_score >= brand_score:
        return "hotspot"
    if brand_score >= 2 and brand_score > hotspot_score:
        return "brand"
    return "unknown"
 
 
def parse_hotspot_csv(filepath: Path) -> list[dict]:
    """解析灰豚热点 CSV → 飞书热点主题表字段"""
    records = []
    with open(filepath, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 尝试从各种可能的列名中提取字段
            topic = (
                row.get("主题") or row.get("热搜词") or row.get("话题")
                or row.get("热点") or row.get("关键词") or row.get("keyword") or ""
            ).strip()
            if not topic:
                continue
 
            heat_raw = row.get("热度") or row.get("热度指数") or row.get("heat") or "0"
            source_raw = row.get("来源") or row.get("平台") or "灰豚"
            url = row.get("链接") or row.get("参考链接") or row.get("url") or ""
            tag_raw = row.get("标签") or row.get("话题词") or row.get("tag") or topic
 
            # 热度等级映射
            try:
                heat_val = int(float(heat_raw))
            except (ValueError, TypeError):
                heat_val = 0
 
            if heat_val >= 1000000:
                level = "S"
            elif heat_val >= 500000:
                level = "A"
            elif heat_val >= 100000:
                level = "B"
            else:
                level = "C"
 
            records.append({
                "主题": topic,
                "类型": "平台话题",
                "话题词 | Tag": [t.strip() for t in tag_raw.split(",") if t.strip()][:5],
                "热度等级": level,
                "来源": "灰豚",
                "参考链接": url,
                "状态": "灵感",
            })
    return records
 
 
def parse_brand_csv(filepath: Path) -> list[dict]:
    """解析灰豚品牌 CSV → 飞书品牌库表字段"""
    records = []
    with open(filepath, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            brand = (
                row.get("品牌") or row.get("品牌名称") or row.get("brand") or ""
            ).strip()
            if not brand:
                continue
 
            heat_raw = row.get("热度") or row.get("热度指数") or row.get("heat") or "0"
            notes_parts = []
            if row.get("涨粉情况"):
                notes_parts.append(f"涨粉: {row['涨粉情况']}")
            if row.get("相关笔记"):
                notes_parts.append(f"笔记: {row['相关笔记']}")
            is_suitable = row.get("是否适合中女风格") or row.get("适合中女") or ""
 
            try:
                heat_val = int(float(heat_raw))
            except (ValueError, TypeError):
                heat_val = 0
 
            if heat_val >= 1000000:
                level = "S"
            elif heat_val >= 500000:
                level = "A"
            elif heat_val >= 100000:
                level = "B"
            else:
                level = "C"
 
            records.append({
                "品牌": brand,
                "标签": ["中女"] if is_suitable in ("是", "yes", "Y", "1") else [],
                "等级": level,
                "合作状态": "未合作",
                "优先级": "中",
                "备注": "；".join(notes_parts) if notes_parts else "",
            })
    return records
 
 
# ─── 主逻辑 ────────────────────────────────────────────
 
def find_csv_files(folder: Path) -> list[Path]:
    """在文件夹中找 CSV 文件，按修改时间倒序"""
    csvs = sorted(
        folder.glob("*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return csvs
 
 
def import_file(
    filepath: Path,
    app_id: str, app_secret: str, app_token: str,
    hotspot_table_id: str, brand_table_id: str,
    session: requests.Session,
    dry_run: bool = False,
) -> dict:
    with open(filepath, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
 
    csv_type = guess_csv_type(headers)
    if csv_type == "unknown":
        return {"type": "unknown", "headers": headers, "records": [], "created": 0}
 
    if csv_type == "hotspot":
        records = parse_hotspot_csv(filepath)
        table_id = hotspot_table_id
        key_field = "主题"
    else:
        records = parse_brand_csv(filepath)
        table_id = brand_table_id
        key_field = "品牌"
 
    if not records:
        return {"type": csv_type, "headers": headers, "records": [], "created": 0}
 
    if dry_run:
        return {"type": csv_type, "headers": headers, "records": records, "created": 0}
 
    # 获取 token
    access_token = get_tenant_access_token(app_id, app_secret, session)
 
    # 获取已有记录做去重
    existing = list_existing_records(app_token, table_id, access_token, session)
    existing_keys = set()
    for r in existing:
        val = r.get("fields", {}).get(key_field, "")
        if val:
            existing_keys.add(str(val).strip())
 
    # 写入新记录
    created = 0
    skipped = 0
    for rec in records:
        key_val = str(rec.get(key_field, "")).strip()
        if key_val in existing_keys:
            skipped += 1
            continue
        create_record(app_token, table_id, access_token, rec, session)
        created += 1
        existing_keys.add(key_val)
 
    return {
        "type": csv_type,
        "headers": headers,
        "records": records,
        "created": created,
        "skipped": skipped,
    }
 
 
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="灰豚 CSV → 飞书多维表格导入工具",
    )
    parser.add_argument("--file", help="指定 CSV 文件路径")
    parser.add_argument("--folder", help="扫描的文件夹 (默认: 用户下载文件夹)")
    parser.add_argument("--watch", action="store_true", help="持续监控文件夹，有新文件自动导入")
    parser.add_argument("--dry-run", action="store_true", help="只解析不写入")
    args = parser.parse_args(argv)
 
    # 确定文件夹
    if args.file:
        folder = Path(args.file).parent
    elif args.folder:
        folder = Path(args.folder)
    else:
        # 默认：用户下载文件夹
        folder = Path.home() / "Downloads"
 
    if not folder.exists():
        print(f"❌ 文件夹不存在: {folder}")
        return 1
 
    # 环境变量
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    app_token = os.environ.get("FEISHU_APP_TOKEN", "")
    hotspot_table_id = os.environ.get("FEISHU_HOTSPOT_TABLE_ID", "")
    brand_table_id = os.environ.get("FEISHU_BRAND_TABLE_ID", "")
 
    if not all([app_id, app_secret, app_token]):
        if not args.dry_run:
            print("❌ 请先设置环境变量: FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN")
            print("   (dry-run 模式不需要飞书配置)")
            if not args.dry_run:
                return 1
 
    session = requests.Session()
 
    def process_file(filepath: Path) -> bool:
        print(f"\n{'─'*50}")
        print(f"📄 解析文件: {filepath.name}")
        print(f"   修改时间: {datetime.fromtimestamp(filepath.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
 
        result = import_file(
            filepath, app_id, app_secret, app_token,
            hotspot_table_id, brand_table_id,
            session, dry_run=args.dry_run,
        )
 
        if result["type"] == "unknown":
            print(f"⚠️  无法识别 CSV 类型")
            print(f"   检测到的列: {', '.join(result['headers'])}")
            print(f"   期望热点表包含: 主题/热搜词/话题 等列")
            print(f"   期望品牌表包含: 品牌/热度/涨粉 等列")
            return False
 
        print(f"   类型: {'🔥 热点数据' if result['type'] == 'hotspot' else '🏷️ 品牌数据'}")
        print(f"   解析到 {len(result['records'])} 条记录")
 
        if args.dry_run:
            for r in result["records"]:
                preview = {k: v for k, v in r.items() if v}
                print(f"      → {preview}")
        else:
            print(f"   ✅ 新增 {result['created']} 条，跳过重复 {result.get('skipped', 0)} 条")
 
        # 导入成功后移动文件
        if not args.dry_run and result['created'] > 0:
            imported_dir = folder / "已导入飞书"
            imported_dir.mkdir(exist_ok=True)
            new_path = imported_dir / filepath.name
            # 避免重名
            if new_path.exists():
                stem = filepath.stem
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_path = imported_dir / f"{stem}_{ts}.csv"
            filepath.rename(new_path)
            print(f"   📁 已移动到: {new_path}")
 
        return True
 
    # 指定文件模式
    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"❌ 文件不存在: {filepath}")
            return 1
        process_file(filepath)
        return 0
 
    # 扫描模式
    csv_files = find_csv_files(folder)
    csv_files = [f for f in csv_files if "已导入飞书" not in str(f)]
 
    if not csv_files:
        if args.watch:
            print(f"👀 监控文件夹: {folder}")
            print(f"   等待新 CSV 文件... (Ctrl+C 退出)")
            known = set()
            try:
                while True:
                    time.sleep(3)
                    current = set(find_csv_files(folder))
                    current = {f for f in current if "已导入飞书" not in str(f)}
                    new_files = current - known
                    for f in new_files:
                        if f.suffix.lower() == ".csv":
                            print(f"\n🆕 检测到新文件: {f.name}")
                            process_file(f)
                    known = current
            except KeyboardInterrupt:
                print("\n👋 已退出")
                return 0
        else:
            print(f"📂 文件夹: {folder}")
            print(f"   没有找到 CSV 文件")
            print(f"   请先在灰豚导出 CSV 到下载文件夹，然后重新运行")
            print(f"   或使用: python -m collector.huitun_import --watch 开启监控模式")
            return 0
 
    # 列表模式：让用户选择
    print(f"📂 文件夹: {folder}\n")
    print("找到以下 CSV 文件（按时间倒序）：")
    for i, f in enumerate(csv_files):
        ts = datetime.fromtimestamp(f.stat().st_mtime).strftime("%m-%d %H:%M")
        size_kb = f.stat().st_size / 1024
        print(f"  [{i+1}] {f.name}  ({ts}, {size_kb:.1f}KB)")
 
    print(f"\n输入序号导入对应文件，或输入 'a' 导入全部，Enter 导入最新的一个：")
 
    try:
        choice = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n👋 已取消")
        return 0
 
    if choice.lower() == "a":
        for f in csv_files:
            process_file(f)
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(csv_files):
            process_file(csv_files[idx])
        else:
            print(f"❌ 序号超出范围 (1-{len(csv_files)})")
            return 1
    elif choice == "" and csv_files:
        process_file(csv_files[0])
    else:
        print("👋 已取消")
    return 0
 
 
if __name__ == "__main__":
    raise SystemExit(main())
 
