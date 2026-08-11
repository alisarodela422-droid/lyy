# 懒阳阳小红书商务协作系统

懒阳阳（小红书穿搭博主）与商务的双人协作系统：飞书多维表格负责排期和灵感库，GitHub Actions 定时把免费公开榜单热词写入「热点主题」表。

## 模块

- 合作排期：寄样到货、拍摄、发布全流程跟踪，含提醒自动化。
- 灵感选题：热点主题、品牌库、灵感选题、艺人穿搭记录。
- 热点采集：微博热搜 + 百度热搜每日自动抓取，关键词粗筛后写入飞书。
- 灰豚数据：无 API，使用 `import-templates/` 下的 CSV 模板人工导入。

## 飞书配置

按 [docs/feishu-configuration.md](docs/feishu-configuration.md) 完成：

1. 创建多维表格「懒阳阳商务协作」和 4 张表：合作表、热点主题、品牌库、灵感选题。
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
- 脚本请求榜单时携带浏览器 User-Agent，如遇 403 可更新 `collector/main.py` 中的 `DEFAULT_HEADERS`。
- 灰豚数据付费版无 API，人工按模板导入。
