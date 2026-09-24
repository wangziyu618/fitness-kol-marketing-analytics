# Fitness Content × KOL Marketing Analytics

**运动健身垂类内容营销与 KOL 投放数据分析 · An end-to-end, reproducible data portfolio project**

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-GitHub%20Pages-0071e3)](https://wangziyu618.github.io/fitness-kol-marketing-analytics/)
[![Data](https://img.shields.io/badge/Data-Kaggle%20CC0-lightgrey)](https://www.kaggle.com/datasets/atharvasoundankar/viral-social-media-trends-and-engagement-analysis)

**Live dashboard · 在线看板 → https://wangziyu618.github.io/fitness-kol-marketing-analytics/**

---

## English

An independent data portfolio project analyzing **what drives engagement in fitness content & KOL marketing** across TikTok, Instagram, YouTube and Twitter — covering the full chain: **data acquisition → cleaning → multi-dimensional SQL analysis → interactive dashboard → budget strategy → engineering delivery**.

**Business questions answered**

1. **Platform** — which platform deserves the core budget? → Instagram leads fitness pooled ER (13.1%).
2. **Creator tier** — mega vs emerging creators? → median ER falls 39.5% → 7.6% across reach quartiles (5.2× gradient, replicated market-wide).
3. **Content format** — does format matter? → main effect is mild (~1.1pp), but platform × format interaction is large (Instagram Live 17.1% vs TikTok Live 7.1%).
4. **Timing** — when to publish? → Sunday 12.5% vs Monday 10.9%; no persistent monthly trend.
5. **Budget allocation** *(inference layer, explicitly marked)* — efficiency-based reallocation projects **+52.0%** expected engagements on a fixed $100K illustrative budget (sensitivity +15.8% ~ +67.1%).

**Data integrity practices**

- Single public dataset (CC0), SHA-256 fingerprinted; acquisition, field dictionary and caveats documented in [`data/raw/SOURCE.md`](data/raw/SOURCE.md).
- 363 physically impossible rows (interactions > views) excluded in a derived copy with full disclosure — raw files untouched.
- The unreliable original `Engagement_Level` label was audited and **not used**; all metrics are recomputed and reproducible.
- Inferential constructs (reach-tier proxy, budget model) are explicitly marked `*` throughout.

### Quickstart

```bash
pip install -r requirements.txt
python scripts/01_clean_data.py       # cleaning + feature engineering + quality report
python scripts/02_run_analysis.py     # runs analysis/queries.sql on SQLite + budget model
python scripts/03_build_dashboard.py  # builds single-file docs/index.html (works offline)
```

### Repository structure

```
├── analysis/queries.sql            # all 11 named analytical queries (SQLite)
├── data/raw/                       # untouched originals + SOURCE.md (provenance)
├── data/processed/                 # cleaned data, quality report, result CSVs
├── docs/index.html                 # single-file interactive dashboard (GitHub Pages)
├── report/STRATEGY_REPORT.md       # findings + budget playbook + limitations (中文)
├── scripts/                        # 01 clean → 02 analyze → 03 build dashboard
└── vendor/echarts-5.5.0.min.js     # inlined into the dashboard at build time
```

---

## 中文

一个独立的求职作品集项目：围绕**运动健身垂类的内容营销与 KOL 投放**，用单一公开数据集完成「数据获取与清洗 → 多维 SQL 分析 → 单文件交互式看板 → 预算策略建议 → 工程化交付」完整能力链，与任何实习经历无关。

**回答的五个业务问题**

1. **平台**：Instagram 领跑健身垂类（合并互动率 13.1%），TikTok 在本数据中未体现"天然高互动"；
2. **达人层级**：互动率随传播层级单调下降（39.5% → 7.6%，5.2 倍梯度，全量数据复现），预算应向中腰部倾斜；
3. **内容形式**：形式主效应温和（约 1.1pp），平台×形式交互显著（Instagram 直播 17.1% 为最佳单元）；
4. **发布时间**：周日（12.5%）显著优于周一（10.9%），月度无单边趋势；
5. **预算分配**（推断层`*`）：效率导向再分配预期互动量 +52.0%（敏感性 +15.8% ~ +67.1%），固定预算下的纯结构优化。

**数据诚信约定**

- 仅用一个公开数据集（CC0 许可），来源、字段口径、获取方式与 SHA-256 指纹完整记录于 `data/raw/SOURCE.md`；
- 363 条物理不可能记录（互动量>曝光量）在派生副本中剔除并全程可追溯，原始文件不改动；
- 原始 `Engagement_Level` 标签经校验不可靠，分析中不采用；全部指标可复算；
- 推断性结论（层级代理、预算模型）在仓库与看板中均以 `*` 显式标注。

**在线看板**：https://wangziyu618.github.io/fitness-kol-marketing-analytics/ （单文件、离线可用、仅悬停交互）
**策略报告**：[report/STRATEGY_REPORT.md](report/STRATEGY_REPORT.md) ｜ **复现步骤**：见上方 Quickstart（Python 3.10+，仅依赖 pandas）
