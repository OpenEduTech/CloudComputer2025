# 行研雷达（Industry-Radar）

一个用于“持续巡检 + 增量识别 + 冲突仲裁 + 自动出报告”的行业研究智能体。

它把一次行业调研拆成流水线：
1) 全网采集（Tavily 搜索 + 网页/PDF 抓取与清洗）
2) 增量对比（LLM 从“旧快照 vs 新资讯”里提炼指标变化）
3) 冲突仲裁（官方 > 媒体 > 传闻）
4) 产出两类报告：
	 - JSON：写入 `data/<行业>/final_analysis_<时间戳>.json`
	 - Markdown：调用通义千问生成带 emoji + 红绿高亮的报告，写入 `report/<keyword><generated_at>.md`

---

## 目录结构（你最常用的）

```
codes/
	main.py                # 本地交互入口（命令行）
	trigger_layer.py       # 阿里云 FC 入口 handler
	orchestrator.py        # 流水线编排：采集→对比→仲裁→总结→存储
	scraper_layer.py       # 采集层：把 search_agent 输出转成 NewsItem
	search_agent/          # 搜索子系统：改写查询→搜索→评分→抓取→清洗→分块
	incremental_analysis.py# 增量对比 + 全局总结（LLM）
	conflict_resolution.py # 冲突仲裁（官方>媒体>传闻）
	storage_layer.py       # 存储层（本地文件模拟对象存储）
	report.py              # Markdown 报告生成（通义千问）
	models.py              # 数据模型与来源权重
	config.py              # 配置（输出模式、LLM 参数、条目上限等）

data/                    # 历史快照 & 最终 JSON 报告（按行业分目录）
report/                  # 生成的 Markdown 报告
```

示例输入结构：`codes/ex.json`（用于演示“最终结构长什么样”。）

---

## 快速开始（Windows / 本地）

### 1) 安装依赖

建议在虚拟环境里：

```bash
pip install -r requirements.txt
```

### 2) 配置 API Key（强烈建议用环境变量）

本项目涉及 3 类外部能力：

- `SILICONFLOW_API_KEY`：用于 `incremental_analysis.py` 调用 SiliconFlow / DeepSeek（做“增量识别”和“全局总结”）
- `TAVILY_API_KEY`：用于搜索
- `DASHSCOPE_API_KEY`：用于通义千问（搜索子系统里用 Tongyi；`report.py` 也会调用 Qwen 生成 Markdown）

PowerShell（当前窗口生效）：

```powershell
$env:SILICONFLOW_API_KEY = "你的Key"
$env:TAVILY_API_KEY = "你的Key"
$env:DASHSCOPE_API_KEY = "你的Key"
```

⚠️ 安全提醒：不要把 Key 写进仓库；如 Key 已泄露请立刻旋转/重置。

> 当前代码里存在“硬编码 key/默认 key”的历史遗留写法（尤其在 `codes/search_agent/search_agent.py` 与 `codes/report.py`）。
> 建议你后续把这些默认值移除，统一改为只从环境变量读取。

### 3) 运行一次行业调研（推荐入口）

```bash
python -u codes/main.py
```

运行后会：
- 在控制台打印：全局总结 + 指标明细 + 文章清单
- 写入 `data/<行业>/raw_snapshots_<时间戳>.json`
- 写入 `data/<行业>/final_analysis_<时间戳>.json`
- 写入 `report/<keyword><generated_at>.md`

如只想拿原始 JSON（不打印过程）：

```powershell
$env:OUTPUT_JSON = "1"
python -u codes/main.py
```

---

## 输出与数据格式

### 1) JSON（最终分析结果）

由 `storage_layer.py` 生成，结构接近 `codes/ex.json`，核心字段：
- `keyword` / `generated_at`
- `global_summary`
- `decisions[]`（每个指标一条：`field/status/old_value/value/change/arbitration/reason`）
- `sources[]`（文章来源清单）

### 2) Markdown（可发布报告）

由 `report.py` 调用通义千问生成，要求：
- 含 emoji
- 关键数据使用 HTML `<span style="color:...">` 做红/绿高亮
- 文件名固定：`report/<keyword><generated_at>.md`

---

## 可调配置（常用环境变量）

这些配置在 `codes/config.py`：

- `REPORT_MODE=compact|verbose`：全局总结/仲裁摘要输出策略
- `MAX_DECISIONS=8`：最终输出指标条数上限
- `MAX_EVIDENCE_PER_DECISION=2`：每条指标最多附带的证据条数（debug 模式）
- `INCLUDE_DEBUG_FIELDS=1`：在输出 JSON 中附加 `confidence/evidence/snippet/key_numbers`

---

## Serverless 部署（阿里云 FC）

入口函数：`codes/trigger_layer.handler`，配置见 `s.yaml`。

一般流程：
1) 安装 Serverless Devs（`s`）
2) `s deploy`
3) 在控制台/函数配置里设置环境变量（至少 `SILICONFLOW_API_KEY`；如要搜索与 Markdown 报告也建议配 `TAVILY_API_KEY`、`DASHSCOPE_API_KEY`）

---

## 文件职责速查

- `codes/orchestrator.py`：把所有步骤串起来，返回供展示/报告的 `dict`
- `codes/scraper_layer.py`：调用 search_agent 采集，并映射为统一模型
- `codes/incremental_analysis.py`：语义增量识别 + 全局总结（核心智能）
- `codes/conflict_resolution.py`：按来源权重做冲突仲裁
- `codes/storage_layer.py`：本地文件化存储（按行业分目录）
- `codes/report.py`：通义千问生成 Markdown 报告
