# 懒阳阳小红书商务协作系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在飞书多维表格上搭建懒阳阳双人协作系统（合作排期 + 灵感选题 + 艺人穿搭），并用 GitHub Actions 定时抓取免费公开榜单写入热点主题表。

**Architecture:** 飞书多维表格承载 4 张数据表和全部视图，飞书自动化负责到货/拍摄/发布提醒；独立的 Python 采集器每天从微博和百度公开榜单抓取热词，按穿搭关键词粗筛后经飞书开放平台 API 写入「热点主题」表；灰豚数据无 API，走人工 CSV 导入。

**Tech Stack:** Python 3.12、requests、pytest、GitHub Actions、飞书开放平台 API、飞书多维表格/自动化。

## Global Constraints

- 飞书字段名、视图名、单选选项必须与设计文档一致：`docs/superpowers/specs/2026-08-11-lanyangyang-xhs-workflow-design.md`。
- 4 张表固定名称：`合作项目`、`热点主题`、`品牌库`、`灵感选题`。
- 「热点主题」表的单选选项：类型 = 季节趋势/平台话题/节日节点/艺人穿搭/品牌热点/其他；来源 = 微博热搜/抖音热榜/百度热搜/灰豚/人工；热度等级 = S/A/B/C；状态 = 灵感/待选/已采用/弃用。
- 采集脚本只允许使用 requests，不引入爬虫框架；代码标识符用英文，用户可见文案用中文。
- 任一数据源失败不影响其他数据源；抓取失败保留已有数据并通知共享群。
- 每个任务独立可测，代码任务遵循 TDD（先写失败测试，再实现）。

## File Structure

- `docs/feishu-configuration.md`：飞书全部手工配置步骤（任务 1）。
- `import-templates/brand_seed.csv`：品牌库种子数据（任务 1）。
- `import-templates/huitun_brand_import.csv`：灰豚品牌导入模板（任务 1）。
- `import-templates/huitun_hotspot_import.csv`：灰豚热点导入模板（任务 1）。
- `collector/models.py`：`HotspotItem` 数据类、`today_iso()`、`heat_level()`（任务 4）。
- `collector/filter.py`：关键词粗筛（任务 5）。
- `collector/sources/weibo.py`、`collector/sources/baidu.py`：两个数据源（任务 6、7）。
- `collector/feishu.py`：飞书 Bitable 客户端（任务 8）。
- `collector/main.py`：CLI 入口与失败通知（任务 9）。
- `.github/workflows/collect-hotspots.yml`：定时任务（任务 10）。
- `README.md`：项目说明与快速开始（任务 10）。
- `tests/`：每个代码模块一个测试文件，fixtures 放在 `tests/fixtures/`（任务 4-9）。

---

### Task 1: 飞书配置指南与导入模板

**Files:**
- Create: `docs/feishu-configuration.md`
- Create: `import-templates/brand_seed.csv`
- Create: `import-templates/huitun_brand_import.csv`
- Create: `import-templates/huitun_hotspot_import.csv`

**Interfaces:**
- Produces: 飞书字段名/选项名/视图名/自动化规则的唯一权威说明，供任务 2、3、8 使用。

- [ ] **Step 1: 创建 `docs/feishu-configuration.md`**

内容如下（完整文档，后续所有飞书手工操作都按此执行）：

````markdown
# 懒阳阳商务协作系统飞书配置指南

## 1. 前置条件

- 飞书免费团队版，商务与博主加入同一组织。
- 两人加入同一个共享群「懒阳阳工作群」。

## 2. 创建多维表格

1. 飞书云文档中新建「多维表格」，命名为「懒阳阳商务协作」。
2. 默认表格改名为「合作项目」。
3. 依次新增 3 张表：「热点主题」「品牌库」「灵感选题」。
4. 把多维表格共享给商务和博主，权限均为「可编辑」。

## 3. 创建 4 张表的字段

### 3.1 合作项目

| 字段名 | 类型 | 选项/说明 |
| --- | --- | --- |
| 品牌 | 文本 | 品牌名称 |
| 合作形式 | 单选 | 寄拍 / 置换 / 付费商单 / 自购 |
| 对接人 | 人员 | 品牌方对接人 |
| 联系方式 | 文本 | 微信或电话 |
| 寄样日期 | 日期 | 品牌寄出样品日期 |
| 预计到货 | 日期 | 预计到货日期 |
| 实际到货 | 日期 | 实际到货日期 |
| 拍摄日期 | 日期 | 拍摄档期 |
| 发布日期 | 日期 | 小红书发布截止日 |
| 平台 | 单选 | 小红书主号 / 小红书小号 / 其他 |
| 状态 | 单选 | 待寄样 / 在途 / 已到货 / 待拍摄 / 已拍摄 / 待发布 / 已发布 / 已取消 |
| 负责人 | 人员 | 商务或博主 |
| 样品清单 | 文本 | 样品明细 |
| 发布链接 | 链接 | 发布后的笔记链接 |
| 备注 | 文本 | 补充信息 |
| 创建人 | 人员 | 自动记录 |

### 3.2 热点主题

| 字段名 | 类型 | 选项/说明 |
| --- | --- | --- |
| 主题 | 文本 | 热点主题名称 |
| 类型 | 单选 | 季节趋势 / 平台话题 / 节日节点 / 艺人穿搭 / 品牌热点 / 其他 |
| 话题词 / Tag | 多选 | 可检索关键词 |
| 艺人 | 文本 | 仅艺人穿搭类型填写 |
| 场合 | 文本 | 综艺 / 街拍 / 红毯 / 活动 / 私服等 |
| 穿搭描述 | 文本 | 造型核心描述 |
| 关联品牌 | 关联 | 关联「品牌库」，可多个 |
| 热度等级 | 单选 | S / A / B / C |
| 有效期 | 日期 | 热点建议使用期限 |
| 适用季节 | 单选 | 春 / 夏 / 秋 / 冬 / 全年 |
| 来源 | 单选 | 微博热搜 / 抖音热榜 / 百度热搜 / 灰豚 / 人工 |
| 参考链接 | 链接 | 原帖或相关笔记 |
| 状态 | 单选 | 灵感 / 待选 / 已采用 / 弃用 |
| 创建人 | 人员 | 自动记录 |

### 3.3 品牌库

| 字段名 | 类型 | 选项/说明 |
| --- | --- | --- |
| 品牌名 | 文本 | 品牌名称 |
| 风格定位 | 多选 | 轻奢 / 设计师 / 通勤 / 中女 / 极简 / 新中式等 |
| 价格带 | 单选 | 300-800 / 800-1500 / 1500+ |
| 热度等级 | 单选 | S / A / B / C |
| 是否已合作 | 单选 | 未合作 / 已合作 / 合作中 |
| 试穿意向 | 单选 | 高 / 中 / 低 / 已邀约 |
| 官方主页 | 链接 | 品牌小红书或官网 |
| 参考笔记 | 链接 | 试穿参考 |
| 备注 | 文本 | 联系状态、渠道等 |

### 3.4 灵感选题

| 字段名 | 类型 | 选项/说明 |
| --- | --- | --- |
| 标题 | 文本 | 选题标题 |
| 核心卖点 | 文本 | 一句话卖点 |
| 风格标签 | 多选 | 通勤 / 约会 / 周末 / 新中式 / 小香风等 |
| 关联品牌 | 关联 | 关联「品牌库」，可多个 |
| 关联热点 | 关联 | 关联「热点主题」 |
| 来源链接 | 链接 | 灵感来源 |
| 状态 | 单选 | 灵感 / 待选 / 已采用 |
| 创作备注 | 文本 | 拍摄构思、搭配思路 |
| 创建人 | 人员 | 自动记录 |

## 4. 创建视图

「合作项目」表创建：

1. 默认表格视图重命名为「全部记录」。
2. 新建日历视图「拍摄日历」，日期字段选「拍摄日期」。
3. 新建日历视图「发布日历」，日期字段选「发布日期」。
4. 新建看板视图「状态看板」，分组字段选「状态」。
5. 新建甘特图视图「项目时间线」，开始日期选「寄样日期」，结束日期选「发布日期」。

## 5. 创建自动化规则

自动化 1（到货跟进）：

- 触发：定时，每天 09:00，数据表「合作项目」，筛选条件：状态 = 在途，实际到货 为空，预计到货 小于等于 今天 + 3 天。
- 操作：发送消息到「懒阳阳工作群」，内容：`【到货跟进】{品牌} 预计 {预计到货} 到货，请确认是否收到。`

自动化 2（拍摄提醒）：

- 触发：定时，每天 09:00，数据表「合作项目」，筛选条件：拍摄日期 = 明天。
- 操作：发送消息到「懒阳阳工作群」，内容：`【拍摄提醒】{品牌} 明天拍摄，请准备。`

自动化 3（发布提醒）：

- 触发：定时，每天 09:00，数据表「合作项目」，筛选条件：发布日期 = 明天。
- 操作：发送消息到「懒阳阳工作群」，内容：`【发布提醒】{品牌} 明天发布，请确认链接。`

自动化 4（变更通知）：

- 触发：记录更新时，数据表「合作项目」，筛选条件：状态 不为空。
- 操作：发送消息到「懒阳阳工作群」，内容：`【排期更新】{品牌} 的信息已更新，请查看。`

回退方案：如果当前飞书版本的「定时」触发不支持记录筛选，改为给「合作项目」增加公式字段「今日提醒」（拍摄日期 = 今天+1 或 发布日期 = 今天+1 或 到货逾期），并把自动化 1-3 的触发改成「记录更新时」+「今日提醒 = 是」。

## 6. 开放平台应用与 API 权限

1. 打开飞书开放平台 `open.feishu.cn`，创建企业自建应用「懒阳阳热点采集」。
2. 在「权限管理」添加「多维表格」读写权限（`bitable:app`），发布应用版本并通过审核。
3. 复制应用凭证：App ID、App Secret。
4. 打开「懒阳阳商务协作」多维表格，从浏览器地址栏取 `base/{app_token}` 中的 app_token。
5. 打开「热点主题」表，从地址栏 `?table={table_id}` 取 table_id。
6. 在「懒阳阳工作群」添加自定义机器人，复制 Webhook 地址。

## 7. 灰豚数据导入

1. 商务在灰豚查询品牌榜或笔记热度，按 `import-templates/huitun_brand_import.csv` 或 `import-templates/huitun_hotspot_import.csv` 整理数据。
2. 多维表格右上角「导入」选择 CSV，UTF-8 编码（带 BOM），导入到对应表。
3. 导入后人工检查「热度等级」「状态」等单选字段是否匹配选项。

## 8. 验收检查

- 两人在手机和电脑均可编辑查看。
- 5 个视图全部可打开。
- 4 条自动化生效（可用测试记录验证）。
- GitHub Actions 每日抓取结果写入「热点主题」。
- 灰豚 CSV 能成功导入。
````

- [ ] **Step 2: 创建品牌种子 CSV `import-templates/brand_seed.csv`**

```csv
品牌名,风格定位,价格带,热度等级,是否已合作,试穿意向,官方主页,参考笔记,备注
地素 D'zzit,设计师/中女,800-1500,B,未合作,高,,,示例种子数据，请按实际调整
Edition,设计师/通勤,800-1500,B,未合作,高,,,示例种子数据，请按实际调整
MO&Co.,通勤/中女,800-1500,B,未合作,中,,,示例种子数据，请按实际调整
ICICLE,极简/通勤,1500+,C,未合作,中,,,示例种子数据，请按实际调整
Laurèl,设计师/通勤,1500+,C,未合作,中,,,示例种子数据，请按实际调整
```

注意：种子品牌仅为占位示例，商务确认后替换为真实品牌池。

- [ ] **Step 3: 创建灰豚品牌导入模板 `import-templates/huitun_brand_import.csv`**

```csv
品牌,热度,涨粉情况,相关笔记,是否适合中女风格,备注
示例品牌A,1000000,周涨粉 5000,笔记数 300,是,
示例品牌B,500000,周涨粉 2000,笔记数 150,待评估,
```

- [ ] **Step 4: 创建灰豚热点导入模板 `import-templates/huitun_hotspot_import.csv`**

```csv
主题,类型,话题词 / Tag,热度等级,来源,参考链接,状态
示例热点主题,品牌热点,品牌名,热度B,灰豚,https://example.com,灵感
```

- [ ] **Step 5: 提交**

```bash
git add docs/feishu-configuration.md import-templates/
git commit -m "docs: add Feishu config guide and import templates"
```

### Task 2: 在飞书创建 4 张表与字段

**Files:** 无（外部飞书 UI 配置）。

**Interfaces:**
- Consumes: `docs/feishu-configuration.md` 第 3 节。

- [ ] **Step 1: 按配置指南第 3 节逐张表创建字段**

每张表创建后对照指南字段表逐行勾选核对，单选字段的选项必须与指南完全一致。

- [ ] **Step 2: 验证关联字段**

在「热点主题」的「关联品牌」字段点击，确认能选择「品牌库」的记录；「灵感选题」的「关联品牌」「关联热点」同理。

- [ ] **Step 3: 记录验收结果**

把「合作项目 / 热点主题 / 品牌库 / 灵感选题」4 张表字段核对结果截图或文字记录，供任务 11 验收使用。

### Task 3: 创建视图与自动化

**Files:** 无（外部飞书 UI 配置）。

**Interfaces:**
- Consumes: `docs/feishu-configuration.md` 第 4、5 节。

- [ ] **Step 1: 按配置指南第 4 节创建 5 个视图**

视图名：全部记录、拍摄日历、发布日历、状态看板、项目时间线。

- [ ] **Step 2: 按配置指南第 5 节创建 4 条自动化**

如遇定时触发不支持筛选，执行指南中的回退方案。

- [ ] **Step 3: 用测试记录验证自动化**

在「合作项目」新建一条记录：品牌=测试品牌，状态=在途，预计到货=昨天，实际到货留空，确认次日 09:00 收到到货提醒；再新建拍摄日期=明天、发布日期=明天的记录各一条，确认收到提醒。

### Task 4: 采集项目骨架与数据模型

**Files:**
- Create: `requirements.txt`
- Create: `collector/__init__.py`
- Create: `collector/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Produces: `HotspotItem(topic: str, source: str, heat: int, url: str, fetched_at: str)`；`today_iso() -> str`；`heat_level(heat: int) -> str`。

- [ ] **Step 1: 创建 `requirements.txt`**

```text
requests==2.32.3
pytest==8.3.3
```

- [ ] **Step 2: 创建 `collector/__init__.py`（空文件）**

- [ ] **Step 3: 写失败测试 `tests/test_models.py`**

```python
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
```

- [ ] **Step 4: 运行测试确认失败**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'collector'`

- [ ] **Step 5: 实现 `collector/models.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class HotspotItem:
    topic: str
    source: str
    heat: int
    url: str
    fetched_at: str


def today_iso() -> str:
    return date.today().isoformat()


def heat_level(heat: int) -> str:
    if heat >= 1_000_000:
        return "S"
    if heat >= 500_000:
        return "A"
    if heat >= 100_000:
        return "B"
    return "C"
```

- [ ] **Step 6: 运行测试确认通过**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS，3 passed

- [ ] **Step 7: 提交**

```bash
git add requirements.txt collector/__init__.py collector/models.py tests/test_models.py
git commit -m "feat: add hotspot data model"
```

### Task 5: 关键词过滤

**Files:**
- Create: `collector/filter.py`
- Create: `tests/test_filter.py`

**Interfaces:**
- Consumes: `HotspotItem`（任务 4）。
- Produces: `DEFAULT_KEYWORDS: list[str]`；`filter_by_keywords(items: Iterable[HotspotItem], keywords: Sequence[str] = DEFAULT_KEYWORDS) -> list[HotspotItem]`。

- [ ] **Step 1: 写失败测试 `tests/test_filter.py`**

```python
from collector.filter import filter_by_keywords
from collector.models import HotspotItem


def _item(topic: str) -> HotspotItem:
    return HotspotItem(topic, "weibo", 1, "https://example.com", "2026-08-11")


def test_filters_topics_matching_any_keyword():
    items = [_item("某女星同款穿搭"), _item("普通新闻"), _item("秋冬大衣")]
    result = filter_by_keywords(items)
    assert [item.topic for item in result] == ["某女星同款穿搭", "秋冬大衣"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_filter.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'collector.filter'`

- [ ] **Step 3: 实现 `collector/filter.py`**

```python
from __future__ import annotations

from collections.abc import Iterable, Sequence

from collector.models import HotspotItem

DEFAULT_KEYWORDS = [
    "穿搭", "女装", "造型", "同款", "街拍", "时尚",
    "艺人", "明星", "品牌", "连衣裙", "大衣", "风衣",
    "衬衫", "外套", "套装", "新中式", "小香风", "通勤", "中女",
]


def filter_by_keywords(
    items: Iterable[HotspotItem],
    keywords: Sequence[str] = DEFAULT_KEYWORDS,
) -> list[HotspotItem]:
    return [item for item in items if any(kw in item.topic for kw in keywords)]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_filter.py -v`
Expected: PASS，1 passed

- [ ] **Step 5: 提交**

```bash
git add collector/filter.py tests/test_filter.py
git commit -m "feat: add keyword filter"
```

### Task 6: 微博热搜源

**Files:**
- Create: `collector/sources/__init__.py`
- Create: `collector/sources/weibo.py`
- Create: `tests/fixtures/weibo_hot_search.json`
- Create: `tests/test_weibo.py`

**Interfaces:**
- Consumes: `HotspotItem`、`today_iso()`（任务 4）。
- Produces: `fetch_weibo(session: requests.Session) -> list[HotspotItem]`，source 固定为 `"weibo"`。

- [ ] **Step 1: 创建 `collector/sources/__init__.py`（空文件）和 fixture `tests/fixtures/weibo_hot_search.json`**

```json
{
  "ok": 1,
  "data": {
    "realtime": [
      {"word": "某女星同款穿搭", "num": 1234567},
      {"word": "普通新闻词", "num": 99999},
      {"word": "", "num": 1}
    ]
  }
}
```

- [ ] **Step 2: 写失败测试 `tests/test_weibo.py`**

```python
import json
from pathlib import Path

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
    assert "某女星同款穿搭" in items[0].url
    assert items[1].heat == 99999
```

- [ ] **Step 3: 运行测试确认失败**

Run: `python -m pytest tests/test_weibo.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'collector.sources.weibo'`

- [ ] **Step 4: 实现 `collector/sources/weibo.py`**

```python
from __future__ import annotations

from urllib.parse import quote

import requests

from collector.models import HotspotItem, today_iso

HOT_SEARCH_URL = "https://weibo.com/ajax/side/hotSearch"
SEARCH_URL_TEMPLATE = "https://s.weibo.com/weibo?q={}"


def fetch_weibo(session: requests.Session) -> list[HotspotItem]:
    resp = session.get(HOT_SEARCH_URL, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    items = []
    for entry in payload.get("data", {}).get("realtime", []):
        topic = entry.get("word")
        if not topic:
            continue
        items.append(
            HotspotItem(
                topic=topic,
                source="weibo",
                heat=int(entry.get("num") or 0),
                url=SEARCH_URL_TEMPLATE.format(quote(topic)),
                fetched_at=today_iso(),
            )
        )
    return items
```

- [ ] **Step 5: 运行测试确认通过**

Run: `python -m pytest tests/test_weibo.py -v`
Expected: PASS，1 passed

- [ ] **Step 6: 提交**

```bash
git add collector/sources/ collector/tests 2>/dev/null || git add collector/sources tests/fixtures tests/test_weibo.py
git commit -m "feat: add weibo hotspot source"
```

注意：在 Windows PowerShell 下直接执行 `git add collector/sources tests/fixtures/weibo_hot_search.json tests/test_weibo.py`。

### Task 7: 百度热搜源

**Files:**
- Create: `collector/sources/baidu.py`
- Create: `tests/fixtures/baidu_board.json`
- Create: `tests/test_baidu.py`

**Interfaces:**
- Consumes: `HotspotItem`、`today_iso()`（任务 4）。
- Produces: `fetch_baidu(session: requests.Session) -> list[HotspotItem]`，source 固定为 `"baidu"`。

- [ ] **Step 1: 创建 fixture `tests/fixtures/baidu_board.json`**

```json
{
  "success": true,
  "data": {
    "cards": [
      {
        "content": [
          {"word": "某品牌秋冬新品", "hotScore": 2345678, "url": "https://www.baidu.com/s?wd=某品牌秋冬新品"},
          {"word": "普通新闻词", "hotScore": 88888}
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: 写失败测试 `tests/test_baidu.py`**

```python
import json
from pathlib import Path

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
    assert items[1].url == "https://www.baidu.com/s?wd=普通新闻词"
```

- [ ] **Step 3: 运行测试确认失败**

Run: `python -m pytest tests/test_baidu.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'collector.sources.baidu'`

- [ ] **Step 4: 实现 `collector/sources/baidu.py`**

```python
from __future__ import annotations

from urllib.parse import quote

import requests

from collector.models import HotspotItem, today_iso

BOARD_URL = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
SEARCH_URL_TEMPLATE = "https://www.baidu.com/s?wd={}"


def fetch_baidu(session: requests.Session) -> list[HotspotItem]:
    resp = session.get(BOARD_URL, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    items = []
    for card in payload.get("data", {}).get("cards", []):
        for entry in card.get("content", []):
            topic = entry.get("word")
            if not topic:
                continue
            url = entry.get("url") or SEARCH_URL_TEMPLATE.format(quote(topic))
            items.append(
                HotspotItem(
                    topic=topic,
                    source="baidu",
                    heat=int(entry.get("hotScore") or 0),
                    url=url,
                    fetched_at=today_iso(),
                )
            )
    return items
```

- [ ] **Step 5: 运行测试确认通过**

Run: `python -m pytest tests/test_baidu.py -v`
Expected: PASS，1 passed

- [ ] **Step 6: 提交**

```bash
git add collector/sources/baidu.py tests/fixtures/baidu_board.json tests/test_baidu.py
git commit -m "feat: add baidu hotspot source"
```

### Task 8: 飞书 Bitable 客户端

**Files:**
- Create: `collector/feishu.py`
- Create: `tests/test_feishu.py`

**Interfaces:**
- Consumes: `HotspotItem`、`heat_level()`（任务 4）。
- Produces: `SOURCE_LABELS: dict[str, str]`；`get_tenant_access_token(app_id, app_secret, session) -> str`；`list_existing_keys(app_token, table_id, access_token, session) -> set[str]`；`append_records(app_token, table_id, access_token, items, session) -> int`。

- [ ] **Step 1: 写失败测试 `tests/test_feishu.py`**

```python
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
    assert body["fields"]["话题词 / Tag"] == ["某穿搭词"]
    assert body["fields"]["热度等级"] == "S"
    assert body["fields"]["来源"] == "微博热搜"
    assert body["fields"]["参考链接"] == "https://example.com"
    assert body["fields"]["状态"] == "灵感"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_feishu.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'collector.feishu'`

- [ ] **Step 3: 实现 `collector/feishu.py`**

```python
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
            "话题词 / Tag": [item.topic],
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_feishu.py -v`
Expected: PASS，3 passed

- [ ] **Step 5: 提交**

```bash
git add collector/feishu.py tests/test_feishu.py
git commit -m "feat: add Feishu Bitable client"
```

### Task 9: CLI 入口与失败通知

**Files:**
- Create: `collector/main.py`
- Create: `tests/test_main.py`

**Interfaces:**
- Consumes: `filter_by_keywords`（任务 5）、`fetch_weibo`/`fetch_baidu`（任务 6、7）、`SOURCE_LABELS`/`get_tenant_access_token`/`list_existing_keys`/`append_records`（任务 8）。
- Produces: `run(sources, session, app_id, app_secret, app_token, table_id, dry_run=False) -> int`；`main(argv=None) -> int`；`notify_failure(webhook, error, session) -> None`。

- [ ] **Step 1: 写失败测试 `tests/test_main.py`**

```python
from collector.main import FETCHERS, run
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
    from collector.main import notify_failure

    notify_failure("", RuntimeError("boom"), FakeSession())
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'collector.main'`

- [ ] **Step 3: 实现 `collector/main.py`**

```python
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
    for name in sources:
        all_items.extend(FETCHERS[name](session))
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_main.py -v`
Expected: PASS，3 passed

- [ ] **Step 5: 运行全部测试**

Run: `python -m pytest -v`
Expected: PASS，全部测试通过

- [ ] **Step 6: 提交**

```bash
git add collector/main.py tests/test_main.py
git commit -m "feat: add collector CLI"
```

### Task 10: GitHub Actions 工作流与 README

**Files:**
- Create: `.github/workflows/collect-hotspots.yml`
- Create: `README.md`

**Interfaces:**
- Consumes: `collector/main.py` 的环境变量：`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_APP_TOKEN`、`FEISHU_HOTSPOT_TABLE_ID`、`FEISHU_WEBHOOK`。

- [ ] **Step 1: 创建 `.github/workflows/collect-hotspots.yml`**

```yaml
name: collect-hotspots

on:
  schedule:
    - cron: '0 1 * * *'
  workflow_dispatch:

permissions:
  contents: read

jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run hotspot collector
        env:
          FEISHU_APP_ID: ${{ secrets.FEISHU_APP_ID }}
          FEISHU_APP_SECRET: ${{ secrets.FEISHU_APP_SECRET }}
          FEISHU_APP_TOKEN: ${{ secrets.FEISHU_APP_TOKEN }}
          FEISHU_HOTSPOT_TABLE_ID: ${{ secrets.FEISHU_HOTSPOT_TABLE_ID }}
          FEISHU_WEBHOOK: ${{ secrets.FEISHU_WEBHOOK }}
        run: python -m collector --sources weibo,baidu
```

说明：`0 1 * * *` 是 UTC 01:00，即北京时间每天 09:00。

- [ ] **Step 2: 创建 `README.md`**

````markdown
# 懒阳阳小红书商务协作系统

懒阳阳（小红书穿搭博主）与商务的双人协作系统：飞书多维表格负责排期和灵感库，GitHub Actions 定时把免费公开榜单热词写入「热点主题」表。

## 模块

- 合作排期：寄样到货、拍摄、发布全流程跟踪，含提醒自动化。
- 灵感选题：热点主题、品牌库、灵感选题、艺人穿搭记录。
- 热点采集：微博热搜 + 百度热搜每日自动抓取，关键词粗筛后写入飞书。
- 灰豚数据：无 API，使用 `import-templates/` 下的 CSV 模板人工导入。

## 飞书配置

按 [docs/feishu-configuration.md](docs/feishu-configuration.md) 完成：

1. 创建多维表格「懒阳阳商务协作」和 4 张表。
2. 创建 5 个视图和 4 条自动化。
3. 创建开放平台自建应用并配置多维表格权限。
4. 把 `import-templates/brand_seed.csv` 导入「品牌库」。

## GitHub Actions 配置

1. 把本仓库推送到 GitHub。
2. 在仓库 Settings > Secrets and variables > Actions 添加：
   - `FEISHU_APP_ID`
   - `FEISHU_APP_SECRET`
   - `FEISHU_APP_TOKEN`
   - `FEISHU_HOTSPOT_TABLE_ID`
   - `FEISHU_WEBHOOK`
3. Actions 页面手动运行一次 `collect-hotspots`，之后每天北京时间 09:00 自动运行。

## 本地开发

```bash
pip install -r requirements.txt
python -m pytest -v
python -m collector --sources weibo,baidu --dry-run
```

真实写入需要设置上述 5 个环境变量（Windows PowerShell）：

```powershell
$env:FEISHU_APP_ID = "cli_xxx"
$env:FEISHU_APP_SECRET = "xxx"
$env:FEISHU_APP_TOKEN = "xxx"
$env:FEISHU_HOTSPOT_TABLE_ID = "tblxxx"
$env:FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
python -m collector --sources weibo,baidu
```

## 艺人穿搭使用流程

1. 发现艺人热度穿搭，在「热点主题」新建记录，类型选「艺人穿搭」，填艺人、场合、穿搭描述、参考链接。
2. 商务判断品牌是否属于中女风格，关联「品牌库」。
3. 合适热点生成「灵感选题」，状态选「待选」。
4. 确定采用后进入「合作项目」排期。

## 数据源说明

- 微博/百度榜单为公开网页数据，页面结构变化时脚本需要人工修复。
- 灰豚数据付费版无 API，人工按模板导入。
````

- [ ] **Step 3: 提交**

```bash
git add .github/workflows/collect-hotspots.yml README.md
git commit -m "feat: add GitHub Actions workflow and README"
```

### Task 11: 端到端验证

**Files:** 无（联调）。

**Interfaces:**
- Consumes: 任务 1-10 的全部交付物。

- [ ] **Step 1: 本地测试**

Run: `python -m pytest -v`
Expected: PASS，全部测试通过。

- [ ] **Step 2: 本地 dry-run**

Run: `python -m collector --sources weibo,baidu --dry-run`
Expected: 打印若干候选词；如果微博或百度接口不可用，按错误信息调整对应源。

- [ ] **Step 3: 用户完成飞书配置**

按 `docs/feishu-configuration.md` 完成表、视图、自动化、开放平台应用和 GitHub Secrets 配置。

- [ ] **Step 4: 真实写入验证**

设置 5 个环境变量后运行 `python -m collector --sources weibo,baidu`，确认「热点主题」表出现新记录，且重复运行不会重复插入。

- [ ] **Step 5: GitHub Actions 手动触发**

在 Actions 页面手动运行 `collect-hotspots`，确认成功且飞书表有新记录；删除一条记录后再跑一次，确认再次写入。

- [ ] **Step 6: 自动化验收**

按任务 3 的测试记录验证 4 条自动化消息。

- [ ] **Step 7: 灰豚导入验收**

按 `docs/feishu-configuration.md` 第 7 节导入一个模板 CSV，确认单选/多选字段正确。

## Self-Review

- 规格覆盖：合作排期字段/视图/自动化对应任务 1-3；热点主题、品牌库、灵感选题、艺人穿搭字段对应任务 1-2；免费榜单采集对应任务 6-7；飞书写入对应任务 8-9；定时运行对应任务 10；灰豚人工导入对应任务 1、11。
- 类型一致性：`HotspotItem`、`today_iso`、`heat_level`、`fetch_weibo`、`fetch_baidu`、`SOURCE_LABELS`、`get_tenant_access_token`、`list_existing_keys`、`append_records`、`run`、`main`、`notify_failure` 在定义与调用处签名一致。
- 无占位符：所有代码和配置均为完整内容。
