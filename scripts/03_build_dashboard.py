# -*- coding: utf-8 -*-
"""
03_build_dashboard.py
单文件交互式看板构建器 / Single-file interactive dashboard builder.

读取 data/processed/results/*.csv 与 analysis_summary.json，
将 ECharts(内联) + 数据(内联) + 样式(内联) 打包为 docs/index.html，
双击即可离线打开；无工具栏、无框选缩放，仅保留悬停查看数值。
Reads analysis result CSVs + summary JSON, inlines ECharts, data and styles into
docs/index.html. Opens offline; hover tooltips only (no toolbox / no zoom / no brush).
"""
from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "processed" / "results"
OUT = ROOT / "docs"
OUT.mkdir(parents=True, exist_ok=True)
ECHARTS = ROOT / "vendor" / "echarts-5.5.0.min.js"

DOW_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
FORMAT_ORDER = ["Short video", "Image post", "Text post", "Long-form video", "Live stream"]
PLATFORM_ORDER = ["Instagram", "TikTok", "YouTube", "Twitter"]
TIER_ORDER = ["T1 Emerging reach", "T2 Growth reach", "T3 Established reach", "T4 Mega reach"]


def rcsv(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / f"{name}.csv")


def build_payload() -> dict:
    q02 = rcsv("q02_platform_fitness")
    q03 = rcsv("q03_vertical_benchmark")
    q04 = rcsv("q04_tier_fitness").set_index("Reach_Tier").reindex(TIER_ORDER).reset_index()
    q04b = rcsv("q04b_tier_all").set_index("Reach_Tier").reindex(TIER_ORDER).reset_index()
    q05 = rcsv("q05_format_platform_heatmap")
    q06 = rcsv("q06_monthly_trend")
    q07 = rcsv("q07_dow").set_index("Day_Of_Week").reindex(DOW_ORDER).reset_index()
    q08 = rcsv("q08_region_platform")
    q09 = rcsv("q09_format_fitness")
    budget = rcsv("budget_model")
    summary = json.loads((RESULTS / "analysis_summary.json").read_text(encoding="utf-8"))

    # 预算聚合到平台层 / aggregate budget to platform level
    bg = budget.groupby("Platform", as_index=False).agg(
        current_budget=("current_budget", "sum"),
        recommended_budget=("recommended_budget", "sum"),
        current_engagements=("current_engagements", "sum"),
        recommended_engagements=("recommended_engagements", "sum"),
    )
    bg["current_share"] = bg["current_budget"] / bg["current_budget"].sum() * 100
    bg["recommended_share"] = bg["recommended_budget"] / bg["recommended_budget"].sum() * 100
    bg["delta_pp"] = bg["recommended_share"] - bg["current_share"]
    bg = bg.sort_values("delta_pp")
    # 单元层 Top5 推荐 / top-5 recommended cells
    top_cells = budget.nlargest(5, "recommended_share")[
        ["Platform", "Format_Group", "recommended_share", "engagements_per_1k", "pooled_er"]
    ]

    months = sorted(q06["Post_Month"].unique())
    month_lines = {
        p: [
            round(float(q06[(q06.Platform == p) & (q06.Post_Month == m)]["pooled_er"].iloc[0] * 100), 2)
            if len(q06[(q06.Platform == p) & (q06.Post_Month == m)]) else None
            for m in months
        ]
        for p in PLATFORM_ORDER
    }
    month_counts = {
        p: [
            int(q06[(q06.Platform == p) & (q06.Post_Month == m)]["n_posts"].iloc[0])
            if len(q06[(q06.Platform == p) & (q06.Post_Month == m)]) else 0
            for m in months
        ]
        for p in PLATFORM_ORDER
    }

    heat = [
        [
            PLATFORM_ORDER.index(r["Platform"]),
            FORMAT_ORDER.index(r["Format_Group"]),
            round(float(r["pooled_er"]) * 100, 2),
            int(r["n_posts"]),
        ]
        for _, r in q05.iterrows()
    ]

    payload = {
        "kpi": summary["kpis"],
        "budget_summary": summary["budget"],
        "vertical": {
            "hashtags": q03["Hashtag"].tolist(),
            "pooled_er": (q03["pooled_er"] * 100).round(2).tolist(),
            "n_posts": q03["n_posts"].tolist(),
            "avg_views": q03["avg_views"].round(0).tolist(),
        },
        "platform": {
            "names": q02["Platform"].tolist(),
            "pooled_er": (q02["pooled_er"] * 100).round(2).tolist(),
            "median_er": (q02["median_er"] * 100).round(2).tolist(),
            "n_posts": q02["n_posts"].tolist(),
            "like_share": (q02["like_share"] * 100).round(1).tolist(),
            "share_share": (q02["share_share"] * 100).round(1).tolist(),
            "comment_share": (q02["comment_share"] * 100).round(1).tolist(),
        },
        "tier": {
            "names": [t.split(" ", 1)[1] for t in TIER_ORDER],
            "fitness_median_er": (q04["median_er"] * 100).round(2).tolist(),
            "market_median_er": (q04b["median_er"] * 100).round(2).tolist(),
            "n_posts": q04["n_posts"].tolist(),
            "avg_views": q04["avg_views"].round(0).tolist(),
            "share_rate": (q04["pooled_share_rate"] * 100).round(2).tolist(),
        },
        "heat": {"platforms": PLATFORM_ORDER, "formats": FORMAT_ORDER, "data": heat},
        "dow": {
            "names": DOW_ORDER,
            "pooled_er": (q07["pooled_er"] * 100).round(2).tolist(),
            "n_posts": q07["n_posts"].tolist(),
            "avg_views": q07["avg_views"].round(0).tolist(),
        },
        "monthly": {"months": months, "er": month_lines, "n": month_counts},
        "region": {
            "names": q08["Region"].tolist(),
            "pooled_er": (q08["pooled_er"] * 100).round(2).tolist(),
            "n_posts": q08["n_posts"].tolist(),
        },
        "format": {
            "names": q09["Format_Group"].tolist(),
            "pooled_er": (q09["pooled_er"] * 100).round(2).tolist(),
            "n_posts": q09["n_posts"].tolist(),
            "share_rate": (q09["pooled_share_rate"] * 100).round(2).tolist(),
        },
        "budget_platform": {
            "names": bg["Platform"].tolist(),
            "delta_pp": bg["delta_pp"].round(2).tolist(),
            "current_share": bg["current_share"].round(1).tolist(),
            "recommended_share": bg["recommended_share"].round(1).tolist(),
        },
        "budget_top_cells": {
            "labels": (top_cells["Platform"] + " · " + top_cells["Format_Group"]).tolist(),
            "share": (top_cells["recommended_share"] * 100).round(1).tolist(),
            "eff": top_cells["engagements_per_1k"].round(0).tolist(),
            "er": (top_cells["pooled_er"] * 100).round(2).tolist(),
        },
    }
    return payload


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fitness Content × KOL Marketing Analytics</title>
<style>
:root{
  --bg:#ffffff; --bg-soft:#f5f5f7; --ink:#1d1d1f; --ink-2:#6e6e73; --ink-3:#86868b;
  --line:#d2d2d7; --accent:#0071e3; --accent-soft:rgba(0,113,227,.08);
  --green:#34c759; --red:#ff3b30; --teal:#5ac8fa; --dark:#1d1d1f;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Inter,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  background:var(--bg); color:var(--ink); line-height:1.6;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1040px;margin:0 auto;padding:0 24px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

/* ---------- nav ---------- */
nav{border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(255,255,255,.85);backdrop-filter:saturate(180%) blur(12px);z-index:50}
nav .wrap{display:flex;align-items:center;justify-content:space-between;height:52px}
nav .brand{font-weight:600;font-size:14px;letter-spacing:.01em}
nav .links{font-size:12.5px;color:var(--ink-2)}
nav .links a{color:var(--ink-2);margin-left:20px}
nav .links a:hover{color:var(--ink)}

/* ---------- hero ---------- */
.hero{padding:84px 0 56px;border-bottom:1px solid var(--line)}
.kicker{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:600;margin-bottom:14px}
.hero h1{font-size:40px;line-height:1.15;font-weight:600;letter-spacing:-.02em;max-width:760px}
.hero .zh{font-size:17px;color:var(--ink-2);margin-top:14px;max-width:680px}
.hero .meta{margin-top:22px;font-size:12.5px;color:var(--ink-3)}
.hero .meta b{color:var(--ink-2);font-weight:600}

/* ---------- KPI ---------- */
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:var(--line);border-bottom:1px solid var(--line)}
.kpi{background:var(--bg);padding:26px 22px}
.kpi .v{font-size:27px;font-weight:600;letter-spacing:-.02em}
.kpi .l{font-size:12px;color:var(--ink-2);margin-top:4px}
.kpi .s{font-size:11px;color:var(--ink-3);margin-top:2px}

/* ---------- sections ---------- */
section{padding:64px 0;border-bottom:1px solid var(--line)}
section.soft{background:var(--bg-soft)}
.sec-head{margin-bottom:30px;max-width:720px}
.sec-num{font-size:12px;color:var(--accent);font-weight:600;letter-spacing:.1em;margin-bottom:8px}
.sec-head h2{font-size:26px;font-weight:600;letter-spacing:-.015em}
.sec-head .zh{color:var(--ink-2);font-size:14.5px;margin-top:8px}
.takeaway{margin-top:12px;font-size:13.5px;color:var(--ink);background:var(--accent-soft);border-left:2px solid var(--accent);padding:10px 14px;border-radius:0 8px 8px 0}
.takeaway .z{color:var(--ink-2);font-size:12.5px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.card{background:var(--bg);border:1px solid var(--line);border-radius:14px;padding:22px 22px 12px}
section.soft .card{background:#fff}
.card h3{font-size:14px;font-weight:600}
.card h3 .h3zh{font-size:12px;font-weight:400;color:var(--ink-3);margin-left:8px}
.finding h4 .h3zh{display:block;font-size:12.5px;font-weight:400;color:var(--ink-3);margin-top:3px;margin-left:0}
.card .sub{font-size:12px;color:var(--ink-3);margin-top:2px}
.chart{width:100%;height:340px;margin-top:6px}
.chart.tall{height:380px}
.src{font-size:11px;color:var(--ink-3);padding:6px 2px 8px;border-top:1px dashed var(--line);margin-top:4px}

/* ---------- callout & lists ---------- */
.callout{border:1px solid var(--line);border-radius:14px;padding:26px;display:flex;gap:36px;align-items:center;background:#fff}
.callout .big{font-size:44px;font-weight:600;letter-spacing:-.03em;color:var(--accent);white-space:nowrap}
.callout .txt{font-size:13.5px;color:var(--ink-2)}
.callout .txt b{color:var(--ink)}
ul.notes{margin-top:22px;font-size:12.5px;color:var(--ink-2);padding-left:18px}
ul.notes li{margin-bottom:5px}
table.mini{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:16px}
table.mini th{font-weight:600;text-align:left;color:var(--ink-2);border-bottom:1px solid var(--line);padding:7px 8px;font-size:11.5px}
table.mini td{border-bottom:1px solid #ebebef;padding:7px 8px}
table.mini tr:last-child td{border-bottom:none}

/* ---------- findings ---------- */
.findings{counter-reset:f;max-width:760px}
.finding{counter-increment:f;padding:20px 0;border-bottom:1px solid var(--line);display:flex;gap:18px}
.finding:last-child{border-bottom:none}
.finding::before{content:counter(f,decimal-leading-zero);font-size:13px;font-weight:600;color:var(--accent);margin-top:3px;font-variant-numeric:tabular-nums}
.finding h4{font-size:15px;font-weight:600;margin-bottom:4px}
.finding p{font-size:13.5px;color:var(--ink-2)}
.finding p b{color:var(--ink)}

/* ---------- footer ---------- */
footer{padding:48px 0 64px;font-size:12.5px;color:var(--ink-2)}
footer h4{font-size:13px;color:var(--ink);margin-bottom:8px}
footer .cols{display:grid;grid-template-columns:1fr 1fr 1fr;gap:32px}
footer p,footer li{font-size:12px;color:var(--ink-2)}
footer ul{padding-left:16px}
.badge{display:inline-block;font-size:10.5px;color:var(--ink-3);border:1px solid var(--line);border-radius:99px;padding:1px 9px;margin-left:8px;vertical-align:2px}

@media (max-width:860px){
  .kpis{grid-template-columns:repeat(2,1fr)}
  .grid2{grid-template-columns:1fr}
  .hero h1{font-size:30px}
  .callout{flex-direction:column;align-items:flex-start;gap:10px}
  footer .cols{grid-template-columns:1fr}
}
</style>
</head>
<body>

<nav>
  <div class="wrap">
    <div class="brand">Fitness × KOL Analytics</div>
    <div class="links">
      <a href="#platforms">Platforms 平台</a><a href="#tiers">Tiers 层级</a><a href="#timing">Timing 时间</a><a href="#budget">Budget 预算</a><a href="__REPO_URL__">GitHub ↗</a>
    </div>
  </div>
</nav>

<header class="hero">
  <div class="wrap">
    <div class="kicker">Data Portfolio · Content &amp; KOL Marketing Analytics</div>
    <h1>What actually drives engagement in fitness content marketing</h1>
    <p class="zh">运动健身垂类内容营销与 KOL 投放数据分析：4 个平台、10 个垂类、4,637 条有效爆款帖，回答平台选择、达人层级、内容形式、发布时间与预算分配五个业务问题。</p>
    <p class="meta">Dataset: <b>Viral Social Media Trends &amp; Engagement Analysis</b> (Kaggle, CC0) · 2022-01 – 2023-12 · Fitness vertical n = <b>497</b> · Analysis: SQL (SQLite) + Python · <span>推断性结论均以 * 标注 · Inferential results are marked with *</span></p>
  </div>
</header>

<div class="kpis">
  <div class="kpi"><div class="v" id="k1">–</div><div class="l">Fitness posts analysed</div><div class="s">#Fitness 垂类样本量</div></div>
  <div class="kpi"><div class="v" id="k2">–</div><div class="l">Fitness pooled engagement rate</div><div class="s">垂类合并互动率</div></div>
  <div class="kpi"><div class="v" id="k3">–</div><div class="l">Emerging-tier median ER</div><div class="s">T1 传播层级中位互动率</div></div>
  <div class="kpi"><div class="v" id="k4">–</div><div class="l">Best platform (fitness)</div><div class="s">垂类表现最佳平台</div></div>
  <div class="kpi"><div class="v" id="k5">–</div><div class="l">Projected budget lift *</div><div class="s">效率导向预算预期提升（推断）</div></div>
</div>

<!-- ============ 01 Overview ============ -->
<section id="overview">
  <div class="wrap">
    <div class="sec-head">
      <div class="sec-num">01 · CONTEXT</div>
      <h2>Fitness trades engagement efficiency for reach</h2>
      <p class="zh">市场背景：#Fitness 是全样本中帖子最多、平均曝光最高的垂类，但合并互动率在 10 个垂类中最低——健身内容以更低的互动效率换取更大的传播规模。</p>
      <div class="takeaway">#Fitness ranks 10/10 on pooled engagement rate (11.5%) while carrying the highest average views (2.79M) and the largest post count (n=497).<div class="z">垂类互动率排名第 10/10，但平均曝光第 1——投放策略必须靠结构与效率取胜，而非垂类天然红利。</div></div>
    </div>
    <div class="card">
      <h3>Pooled engagement rate by vertical<span class="h3zh">各垂类合并互动率</span></h3>
      <div class="sub">Interactions ÷ views, all posts per hashtag · 各话题合并互动率（互动量÷曝光量）</div>
      <div id="ch_vertical" class="chart"></div>
      <div class="src">Source 数据来源: q03_vertical_benchmark · n = 4,637 posts after data-quality filtering（经数据质量过滤后的有效帖子数）</div>
    </div>
  </div>
</section>

<!-- ============ 02 Platforms ============ -->
<section id="platforms" class="soft">
  <div class="wrap">
    <div class="sec-head">
      <div class="sec-num">02 · PLATFORMS</div>
      <h2>Instagram leads the fitness vertical on engagement</h2>
      <p class="zh">平台选择：Instagram 在健身垂类的合并互动率（13.1%）与中位互动率（13.0%）均居首；合并值与中位值高度一致，说明结论不受极端值影响。互动结构各平台相似，点赞占 75–79%。</p>
      <div class="takeaway">Instagram 13.1% &gt; YouTube 11.9% &gt; TikTok 11.0% &gt; Twitter/X 10.2% (pooled ER, fitness).<div class="z">垂类优先级：Instagram 为首选主阵地；TikTok 在本数据中未体现“天然高互动”优势。</div></div>
    </div>
    <div class="grid2">
      <div class="card">
        <h3>Engagement rate by platform<span class="h3zh">分平台互动率</span></h3>
        <div class="sub">Pooled vs median ER, #Fitness · 合并与中位互动率（#Fitness）</div>
        <div id="ch_platform" class="chart"></div>
        <div class="src">Source 数据来源: q02_platform_fitness</div>
      </div>
      <div class="card">
        <h3>Engagement composition<span class="h3zh">互动结构</span></h3>
        <div class="sub">Share of likes / shares / comments, #Fitness · 点赞/分享/评论占比（#Fitness）</div>
        <div id="ch_mix" class="chart"></div>
        <div class="src">Source 数据来源: q02_platform_fitness · Instagram has the highest share component (17.0%)（Instagram 分享占比最高 17.0%）</div>
      </div>
    </div>
  </div>
</section>

<!-- ============ 03 Tiers ============ -->
<section id="tiers">
  <div class="wrap">
    <div class="sec-head">
      <div class="sec-num">03 · CREATOR TIERS</div>
      <h2>Smaller reach, far stronger engagement — a 5× gradient</h2>
      <p class="zh">达人层级：以帖子曝光量四分位构造传播层级代理（T1≤1.48M，T4&gt;3.86M views）。健身垂类中 T1 中位互动率 39.5%，约为 T4（7.6%）的 5.2 倍；该梯度在全量数据中同样单调成立，非垂类偶然现象。</p>
      <div class="takeaway">Median ER falls monotonically from 39.5% (T1) to 7.6% (T4) in fitness; the same monotone pattern holds market-wide (35.9% → 7.4%).<div class="z">层级是全部维度中效应量最大的变量——预算应向中腰部创作者倾斜。</div></div>
    </div>
    <div class="grid2">
      <div class="card">
        <h3>Median engagement rate by reach tier<span class="h3zh">分层级中位互动率</span></h3>
        <div class="sub">Fitness vs market-wide · 健身垂类 vs 全市场</div>
        <div id="ch_tier" class="chart"></div>
        <div class="src">Source 数据来源: q04_tier_fitness, q04b_tier_all · Tier = dataset-wide views quartile (proxy construct *)（层级=全量曝光四分位代理构造）</div>
      </div>
      <div class="card">
        <h3>Share rate by tier<span class="h3zh">分层级分享率——病毒传播集中于底层</span></h3>
        <div class="sub">Shares ÷ views, #Fitness · 分享率（分享量÷曝光量，病毒传播代理）</div>
        <div id="ch_share" class="chart"></div>
        <div class="src">Source 数据来源: q04_tier_fitness · T1 share rate 5.6% vs T4 1.1%（T1 分享率为 T4 的近 5 倍）</div>
      </div>
    </div>
  </div>
</section>

<!-- ============ 04 Format ============ -->
<section id="format" class="soft">
  <div class="wrap">
    <div class="sec-head">
      <div class="sec-num">04 · CONTENT FORMAT</div>
      <h2>Format matters less than tier — but live streams break the pattern</h2>
      <p class="zh">内容形式：健身垂类整体形式间差异温和（长视频 12.2% 居首，区间约 1.1pp）；但平台×形式组合差异显著——Instagram 直播达 17.1%，而 TikTok 直播仅 7.1%，为全场最低。</p>
      <div class="takeaway">Format alone explains little (12.2% → 11.0%); the platform × format interaction is where the signal lives — Instagram Live 17.1% vs TikTok Live 7.1%.<div class="z">形式选择应“按平台定制”：直播押 Instagram，长视频押 TikTok/Instagram，短视频押 TikTok/YouTube。</div></div>
    </div>
    <div class="grid2">
      <div class="card">
        <h3>Platform × format engagement heatmap<span class="h3zh">平台×形式互动率热力图</span></h3>
        <div class="sub">Pooled ER %, #Fitness · 合并互动率热力图（颜色越深互动率越高）</div>
        <div id="ch_heat" class="chart tall"></div>
        <div class="src">Source 数据来源: q05_format_platform_heatmap · cell n = 14–51（每格样本量 14–51 帖）</div>
      </div>
      <div class="card">
        <h3>Format ranking, all platforms combined<span class="h3zh">形式整体排名</span></h3>
        <div class="sub">Pooled ER %, #Fitness · 全平台合并后的形式互动率排名</div>
        <div id="ch_format" class="chart tall"></div>
        <div class="src">Source 数据来源: q09_format_fitness</div>
      </div>
    </div>
  </div>
</section>

<!-- ============ 05 Timing ============ -->
<section id="timing">
  <div class="wrap">
    <div class="sec-head">
      <div class="sec-num">05 · TIMING</div>
      <h2>Sunday is the single best day to post fitness content</h2>
      <p class="zh">发布时间：星期维度的差异（周日 12.5% vs 周一 10.9%，约 1.6pp）大于形式维度。月度节奏上各平台围绕 8–16% 波动，无持续单边趋势，说明不存在“一劳永逸”的月份策略。</p>
      <div class="takeaway">Sunday 12.5% &gt; Friday 11.9% &gt; Wednesday 11.8%; Monday is the weakest (10.9%).<div class="z">执行建议：将重点内容排期至周日与周五，周一避免发布核心投放内容。</div></div>
    </div>
    <div class="grid2">
      <div class="card">
        <h3>Engagement rate by day of week<span class="h3zh">星期互动率</span></h3>
        <div class="sub">Pooled ER %, #Fitness · 按发布星期聚合的合并互动率</div>
        <div id="ch_dow" class="chart"></div>
        <div class="src">Source 数据来源: q07_dow · n = 56–86 per day（每日样本量 56–86 帖）</div>
      </div>
      <div class="card">
        <h3>Monthly engagement trend by platform<span class="h3zh">分平台月度互动率趋势</span></h3>
        <div class="sub">Pooled ER %, #Fitness, 2022-01 – 2023-12 · 月度合并互动率（24 个月）</div>
        <div id="ch_month" class="chart"></div>
        <div class="src">Source 数据来源: q06_monthly_trend · monthly n per platform = 1–11 (small cells, read as direction only)（单元格样本量小，仅作方向参考）</div>
      </div>
    </div>
  </div>
</section>

<!-- ============ 06 Budget ============ -->
<section id="budget" class="soft">
  <div class="wrap">
    <div class="sec-head">
      <div class="sec-num">06 · BUDGET ALLOCATION <span class="badge">Inference layer · 推断层</span></div>
      <h2>Reallocating by engagement efficiency projects +52% interactions</h2>
      <p class="zh">预算分配（推断性结论）：以公开报价区间中点估算单帖成本，对比「按发帖量铺开」与「按单位成本互动效率分配」两种方案。固定 10 万美元说明性预算下，效率导向方案预期互动量提升 52.0%。</p>
    </div>
    <div class="callout">
      <div class="big">+52.0%*</div>
      <div class="txt">
        <b>Projected engagements: 41.2M → 62.6M</b> on an identical $100K illustrative budget, purely by shifting spend from high-cost/low-efficiency cells (e.g. Instagram Shorts, YouTube long-form, TikTok Live) toward high-efficiency cells (text &amp; image posts on YouTube/Twitter, Instagram text/image).<br>
        同一预算下仅通过单元间再分配，预期互动量由 4,120 万提升至 6,260 万。所有成本为公开报价区间中点的说明性取值，结果为方向性推断，非真实成交预测。
      </div>
    </div>
    <div class="grid2" style="margin-top:24px">
      <div class="card">
        <h3>Budget reallocation by platform<span class="h3zh">分平台预算再分配</span></h3>
        <div class="sub">Δ share in percentage points (efficiency plan − activity plan) · 预算份额变化（效率方案 − 现状方案，右增左减）</div>
        <div id="ch_budget" class="chart"></div>
        <div class="src">Source 数据来源: budget_model.csv · cells aggregated to platform level（单元聚合至平台层）</div>
      </div>
      <div class="card">
        <h3>Top-5 recommended cells<span class="h3zh">推荐预算 Top-5 单元</span></h3>
        <div class="sub">Recommended budget share · 推荐预算份额最高的平台×形式单元</div>
        <div id="ch_cells" class="chart"></div>
        <div class="src">Source 数据来源: budget_model.csv · efficiency = expected engagements per $1K（效率=每千美元预期互动量）</div>
      </div>
    </div>
    <ul class="notes">
      <li><b>Assumptions · 假设</b>: cost per sponsored post = illustrative midpoints of published rate ranges (LaunchPointHQ sports/fitness rate guide; Influencer Marketing Hub benchmarks); expected engagements = budget ÷ cost-per-post × observed avg interactions-per-post. 成本假设见报告附表，均为说明性取值。</li>
      <li><b>Not causal · 非因果</b>: reallocation assumes observed per-post efficiency holds at scale; diminishing returns and audience overlap are not modelled. 再分配假设单元效率不随投放规模衰减，未建模受众重叠与边际递减。</li>
      <li>Current plan = budget proportional to observed posting activity (status-quo proxy). 现状方案以发帖量为代理。</li>
    </ul>
  </div>
</section>

<!-- ============ 07 Findings ============ -->
<section id="findings">
  <div class="wrap">
    <div class="sec-head">
      <div class="sec-num">07 · FINDINGS → ACTIONS</div>
      <h2>What I would tell a fitness brand</h2>
      <p class="zh">核心发现与可执行建议（完整推导见仓库内策略报告）。</p>
    </div>
    <div class="findings">
      <div class="finding"><div><h4>Anchor the plan on Instagram, use TikTok for efficient reach, not engagement<span class="h3zh">以 Instagram 为主阵地，TikTok 定位性价比曝光</span></h4><p>Instagram leads fitness ER (<b>13.1%</b> pooled). TikTok does not over-perform in this data (<b>11.0%</b>) despite its reputation — buy it for cheap reach, not interaction. <span style="color:var(--ink-3)">Instagram 互动率第一；TikTok 在本数据中互动一般，定位为"性价比曝光"而非互动引擎。</span></p></div></div>
      <div class="finding"><div><h4>Shift spend toward emerging creators — the strongest effect in the data<span class="h3zh">预算向中腰部创作者倾斜——全场最大效应</span></h4><p>T1 (≤1.48M views) median ER <b>39.5%</b> vs T4 <b>7.6%</b>; share rate <b>5.6%</b> vs <b>1.1%</b>. A portfolio of many emerging creators beats a few mega placements on engagement-per-dollar*. <span style="color:var(--ink-3)">同等预算下，多个中腰部达人组合的单位互动效率优于少数头部达人*。</span></p></div></div>
      <div class="finding"><div><h4>Customise format per platform; never buy TikTok Live in this vertical<span class="h3zh">形式按平台定制，本垂类不买 TikTok 直播</span></h4><p>Instagram Live <b>17.1%</b> is the single best cell; TikTok Live <b>7.1%</b> the worst. Long-form leads on TikTok (<b>13.4%</b>) and Instagram (<b>14.1%</b>). <span style="color:var(--ink-3)">直播押 Instagram，长视频押 TikTok，短视频组合投放。</span></p></div></div>
      <div class="finding"><div><h4>Schedule hero content on Sundays and Fridays<span class="h3zh">重点内容排期周日与周五</span></h4><p>Sunday pooled ER <b>12.5%</b>, Monday weakest <b>10.9%</b> — a ~1.6pp gap that exceeds the entire format effect. <span style="color:var(--ink-3)">周日与周一相差约 1.6 个百分点，超过形式维度全部差异；周一仅作常规更新。</span></p></div></div>
      <div class="finding"><div><h4>For international BD: the UK is the efficiency outlier worth prioritising<span class="h3zh">国际化 BD：英国是值得优先测试的效率市场</span></h4><p>UK leads all regions in fitness ER (<b>13.0%</b>) with above-average views; Brazil trails (<b>10.0%</b>) despite the highest reach. <span style="color:var(--ink-3)">英国互动效率居首且曝光高于均值；巴西曝光最高但互动垫底。</span></p></div></div>
    </div>
  </div>
</section>

<footer>
  <div class="wrap">
    <div class="cols">
      <div>
        <h4>Data &amp; provenance · 数据来源</h4>
        <p>“Viral Social Media Trends &amp; Engagement Analysis”, Atharva Soundankar, Kaggle, <b>CC0 Public Domain</b>. 5,000 posts, 2022-01-01 – 2023-12-30; 4,637 retained after excluding 363 rows with interactions &gt; views (impossible values, fully documented). SHA-256 fingerprints in <code>data/processed/data_quality_report.md</code>.<br>5,000 条爆款帖，剔除 363 条互动量&gt;曝光量的不可能记录后保留 4,637 条；原始文件指纹见仓库质量报告，全程可追溯。</p>
      </div>
      <div>
        <h4>Limitations · 局限性</h4>
        <ul>
          <li>Dataset card does not disclose collection methodology; value patterns suggest simulated data — conclusions describe structure within this dataset, not market ground truth. 数据采集方式未披露，结论仅反映数据内部结构。</li>
          <li>No follower counts → creator tiers are a reach-based proxy*. 无粉丝数，层级为曝光代理。</li>
          <li>Daily granularity only; no hour-level timing. 仅日级时间。</li>
          <li>Budget model uses published rate midpoints; not transactional prices*. 成本为报价基准中点。</li>
        </ul>
      </div>
      <div>
        <h4>Reproduce · 复现</h4>
        <p><code>python scripts/01_clean_data.py → 02_run_analysis.py → 03_build_dashboard.py</code><br>依次运行三个脚本即可从原始数据完整复现本看板。</p>
        <p style="margin-top:8px"><a href="__REPO_URL__">GitHub repository ↗</a><br><a href="__DATA_URL__">Dataset on Kaggle ↗</a></p>
      </div>
    </div>
    <p style="margin-top:32px;color:var(--ink-3)">* Inferential result — explicitly assumption-based, marked throughout the repo. · 推断性结论，基于显式假设。<br>Built as an independent data portfolio project · 独立求职作品集项目，与任何实习经历无关。</p>
  </div>
</footer>

<script>__ECHARTS__</script>
<script>
const D = __DATA_JSON__;
const ACCENT = "#0071e3", GRAY = "#86868b", LIGHT = "#d2d2d7", INK = "#1d1d1f", TEAL="#5ac8fa", GREEN="#34c759", RED="#ff3b30";
const FONT = '-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif';

const baseAxis = {
  axisLine:{lineStyle:{color:LIGHT}}, axisTick:{show:false},
  axisLabel:{color:"#6e6e73",fontSize:11,fontFamily:FONT},
  splitLine:{lineStyle:{color:"#f0f0f2"}}
};
const tip = {
  trigger:"item", backgroundColor:"rgba(255,255,255,.97)", borderColor:LIGHT, borderWidth:1,
  textStyle:{color:INK,fontSize:12,fontFamily:FONT}, padding:[8,12],
  extraCssText:"box-shadow:0 4px 16px rgba(0,0,0,.08);border-radius:10px;"
};
function mk(id,opt){ const el=document.getElementById(id); const c=echarts.init(el,null,{renderer:"canvas"}); c.setOption(opt); window.addEventListener("resize",()=>c.resize()); return c; }
const pct = v => v==null?"–":(+v).toFixed(1)+"%";
const fmtM = v => v>=1e6?(v/1e6).toFixed(1)+"M":v>=1e3?(v/1e3).toFixed(0)+"K":(""+v);

/* KPI */
document.getElementById("k1").textContent = D.kpi.fitness_posts;
document.getElementById("k2").textContent = (D.kpi.fitness_pooled_er*100).toFixed(1)+"%";
document.getElementById("k3").textContent = D.tier.fitness_median_er[0].toFixed(1)+"%";
document.getElementById("k4").textContent = D.kpi.best_platform_fitness;
document.getElementById("k5").textContent = "+"+D.budget_summary.projected_lift_pct+"%";

/* 01 vertical */
mk("ch_vertical",{
  tooltip:{...tip, formatter:p=>`<b>${p.name}</b><br/>Pooled ER 合并互动率: ${p.value}%<br/>Posts 帖子数: ${D.vertical.n_posts[p.dataIndex]}<br/>Avg views 平均曝光: ${fmtM(D.vertical.avg_views[p.dataIndex])}`},
  grid:{left:48,right:20,top:18,bottom:52},
  xAxis:{type:"category",data:D.vertical.hashtags,...baseAxis,axisLabel:{...baseAxis.axisLabel,rotate:28}},
  yAxis:{type:"value",...baseAxis,axisLabel:{...baseAxis.axisLabel,formatter:"{value}%"}},
  series:[{type:"bar",barWidth:"55%",data:D.vertical.pooled_er.map((v,i)=>({value:v,itemStyle:{color:D.vertical.hashtags[i]==="#Fitness"?ACCENT:"#c7c7cc",borderRadius:[5,5,0,0]}}))}]
});

/* 02 platform */
mk("ch_platform",{
  tooltip:{...tip,trigger:"axis",axisPointer:{type:"shadow"},formatter:ps=>`<b>${ps[0].name}</b><br/>`+ps.map(p=>`${p.marker} ${p.seriesName}: ${p.value}%`).join("<br/>")+`<br/>Posts 帖子数: ${D.platform.n_posts[ps[0].dataIndex]}`},
  legend:{top:0,right:0,icon:"roundRect",itemWidth:10,itemHeight:10,textStyle:{color:"#6e6e73",fontSize:11,fontFamily:FONT}},
  grid:{left:48,right:16,top:34,bottom:30},
  xAxis:{type:"category",data:D.platform.names,...baseAxis},
  yAxis:{type:"value",...baseAxis,axisLabel:{...baseAxis.axisLabel,formatter:"{value}%"}},
  series:[
    {name:"Pooled ER 合并互动率",type:"bar",barWidth:"30%",data:D.platform.pooled_er,itemStyle:{color:ACCENT,borderRadius:[4,4,0,0]}},
    {name:"Median ER 中位互动率",type:"bar",barWidth:"30%",data:D.platform.median_er,itemStyle:{color:"#c7c7cc",borderRadius:[4,4,0,0]}}
  ]
});

/* 02 mix */
mk("ch_mix",{
  tooltip:{...tip,formatter:p=>`<b>${p.name}</b><br/>${p.seriesName}: ${p.value}%`},
  legend:{top:0,right:0,icon:"roundRect",itemWidth:10,itemHeight:10,textStyle:{color:"#6e6e73",fontSize:11,fontFamily:FONT}},
  grid:{left:80,right:30,top:34,bottom:30},
  xAxis:{type:"value",max:100,...baseAxis,axisLabel:{...baseAxis.axisLabel,formatter:"{value}%"}},
  yAxis:{type:"category",data:D.platform.names.slice().reverse(),...baseAxis},
  series:[
    {name:"Likes 点赞",stack:"m",type:"bar",barWidth:22,data:D.platform.like_share.slice().reverse(),itemStyle:{color:ACCENT}},
    {name:"Shares 分享",stack:"m",type:"bar",data:D.platform.share_share.slice().reverse(),itemStyle:{color:TEAL}},
    {name:"Comments 评论",stack:"m",type:"bar",data:D.platform.comment_share.slice().reverse(),itemStyle:{color:"#c7c7cc",borderRadius:[0,4,4,0]}}
  ]
});

/* 03 tier */
mk("ch_tier",{
  tooltip:{...tip,trigger:"axis",axisPointer:{type:"shadow"},formatter:ps=>`<b>${D.tier.names[ps[0].dataIndex]}</b><br/>`+ps.map(p=>`${p.marker} ${p.seriesName}: ${p.value}%`).join("<br/>")+`<br/>Fitness n 垂类样本: ${D.tier.n_posts[ps[0].dataIndex]} · avg views 平均曝光: ${fmtM(D.tier.avg_views[ps[0].dataIndex])}`},
  legend:{top:0,right:0,icon:"roundRect",itemWidth:10,itemHeight:10,textStyle:{color:"#6e6e73",fontSize:11,fontFamily:FONT}},
  grid:{left:48,right:16,top:34,bottom:30},
  xAxis:{type:"category",data:D.tier.names,...baseAxis},
  yAxis:{type:"value",...baseAxis,axisLabel:{...baseAxis.axisLabel,formatter:"{value}%"}},
  series:[
    {name:"Fitness 健身垂类",type:"bar",barWidth:"30%",data:D.tier.fitness_median_er,itemStyle:{color:ACCENT,borderRadius:[4,4,0,0]}},
    {name:"Market-wide 全市场",type:"bar",barWidth:"30%",data:D.tier.market_median_er,itemStyle:{color:"#c7c7cc",borderRadius:[4,4,0,0]}}
  ]
});

/* 03 share rate */
mk("ch_share",{
  tooltip:{...tip,formatter:p=>`<b>${p.name}</b><br/>Share rate 分享率: ${p.value}%<br/>Fitness n 垂类样本: ${D.tier.n_posts[p.dataIndex]}`},
  grid:{left:48,right:16,top:18,bottom:30},
  xAxis:{type:"category",data:D.tier.names,...baseAxis},
  yAxis:{type:"value",...baseAxis,axisLabel:{...baseAxis.axisLabel,formatter:"{value}%"}},
  series:[{type:"line",smooth:true,symbol:"circle",symbolSize:8,data:D.tier.share_rate,
    lineStyle:{width:2.5,color:ACCENT},itemStyle:{color:ACCENT,borderColor:"#fff",borderWidth:2},
    areaStyle:{color:{type:"linear",x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:"rgba(0,113,227,.14)"},{offset:1,color:"rgba(0,113,227,0)"}]}}}]
});

/* 04 heatmap */
mk("ch_heat",{
  tooltip:{...tip,formatter:p=>`<b>${D.heat.platforms[p.value[0]]} · ${D.heat.formats[p.value[1]]}</b><br/>Pooled ER 合并互动率: ${p.value[2]}%<br/>Posts 帖子数: ${p.value[3]}`},
  grid:{left:96,right:20,top:10,bottom:56},
  xAxis:{type:"category",data:D.heat.platforms,...baseAxis,splitLine:{show:false}},
  yAxis:{type:"category",data:D.heat.formats,...baseAxis,splitLine:{show:false}},
  visualMap:{min:6,max:18,calculable:false,orient:"horizontal",left:"center",bottom:0,itemHeight:100,itemWidth:12,
    textStyle:{color:"#86868b",fontSize:10,fontFamily:FONT},inRange:{color:["#eef3fa","#9ec8f2",ACCENT]}},
  series:[{type:"heatmap",data:D.heat.data,
    label:{show:true,fontSize:11,fontFamily:FONT,color:INK,formatter:p=>p.value[2].toFixed(1)},
    itemStyle:{borderColor:"#fff",borderWidth:3,borderRadius:6},emphasis:{disabled:true}}]
});

/* 04 format ranking */
mk("ch_format",{
  tooltip:{...tip,formatter:p=>`<b>${p.name}</b><br/>Pooled ER 合并互动率: ${p.value}%<br/>Posts 帖子数: ${D.format.n_posts[p.dataIndex]}<br/>Share rate 分享率: ${D.format.share_rate[p.dataIndex]}%`},
  grid:{left:110,right:36,top:14,bottom:30},
  xAxis:{type:"value",...baseAxis,axisLabel:{...baseAxis.axisLabel,formatter:"{value}%"}},
  yAxis:{type:"category",data:D.format.names.slice().reverse(),...baseAxis},
  series:[{type:"bar",barWidth:18,data:D.format.pooled_er.slice().reverse().map((v,i)=>({value:v,itemStyle:{color:i===D.format.names.length-1?ACCENT:"#c7c7cc",borderRadius:[0,5,5,0]}})),
    label:{show:true,position:"right",fontSize:11,color:"#6e6e73",fontFamily:FONT,formatter:p=>p.value+"%"}}]
});

/* 05 dow */
mk("ch_dow",{
  tooltip:{...tip,formatter:p=>`<b>${p.name}</b><br/>Pooled ER 合并互动率: ${p.value}%<br/>Posts 帖子数: ${D.dow.n_posts[p.dataIndex]}<br/>Avg views 平均曝光: ${fmtM(D.dow.avg_views[p.dataIndex])}`},
  grid:{left:48,right:16,top:18,bottom:30},
  xAxis:{type:"category",data:D.dow.names.map(d=>d.slice(0,3)),...baseAxis},
  yAxis:{type:"value",min:10,max:13,...baseAxis,axisLabel:{...baseAxis.axisLabel,formatter:"{value}%"}},
  series:[{type:"bar",barWidth:"52%",data:D.dow.pooled_er.map((v,i)=>({value:v,itemStyle:{color:D.dow.names[i]==="Sunday"?ACCENT:(D.dow.names[i]==="Friday"?"#7fb8ef":"#c7c7cc"),borderRadius:[5,5,0,0]}}))}]
});

/* 05 monthly */
const PCOLORS = {Instagram:ACCENT,TikTok:INK,YouTube:RED,Twitter:TEAL};
mk("ch_month",{
  tooltip:{...tip,trigger:"axis",formatter:ps=>`<b>${ps[0].axisValue}</b><br/>`+ps.filter(p=>p.value!=null).map(p=>`${p.marker} ${p.seriesName}: ${p.value}% (n=${D.monthly.n[p.seriesName][p.dataIndex]})`).join("<br/>")},
  legend:{top:0,right:0,icon:"roundRect",itemWidth:10,itemHeight:10,textStyle:{color:"#6e6e73",fontSize:11,fontFamily:FONT}},
  grid:{left:48,right:16,top:34,bottom:42},
  xAxis:{type:"category",data:D.monthly.months,...baseAxis,axisLabel:{...baseAxis.axisLabel,interval:2,formatter:v=>v.slice(2)}},
  yAxis:{type:"value",...baseAxis,axisLabel:{...baseAxis.axisLabel,formatter:"{value}%"}},
  series:D.monthly.months.length?Object.keys(D.monthly.er).map(p=>({
    name:p,type:"line",smooth:true,symbol:"none",connectNulls:true,data:D.monthly.er[p],
    lineStyle:{width:2,color:PCOLORS[p]},itemStyle:{color:PCOLORS[p]}
  })):[]
});

/* 06 budget */
mk("ch_budget",{
  tooltip:{...tip,formatter:p=>{const i=p.dataIndex;return `<b>${p.name}</b><br/>Current share 当前份额: ${D.budget_platform.current_share[i]}%<br/>Recommended 推荐份额: ${D.budget_platform.recommended_share[i]}%<br/>Δ 变化 ${p.value>0?"+":""}${p.value} pp`;}},
  grid:{left:80,right:44,top:18,bottom:30},
  xAxis:{type:"value",...baseAxis,axisLabel:{...baseAxis.axisLabel,formatter:v=>(v>0?"+":"")+v+" pp"}},
  yAxis:{type:"category",data:D.budget_platform.names,...baseAxis},
  series:[{type:"bar",barWidth:18,data:D.budget_platform.delta_pp.map(v=>({value:v,itemStyle:{color:v>=0?ACCENT:"#c7c7cc",borderRadius:v>=0?[0,5,5,0]:[5,0,0,5]}})),
    label:{show:true,position:"right",fontSize:11,color:"#6e6e73",fontFamily:FONT,formatter:p=>(p.value>0?"+":"")+p.value}}]
});

/* 06 top cells */
mk("ch_cells",{
  tooltip:{...tip,formatter:p=>`<b>${p.name}</b><br/>Recommended share 推荐份额: ${p.value}%<br/>Efficiency 效率: ${fmtM(D.budget_top_cells.eff[p.dataIndex])} engagements / $1K（互动量/千美元）<br/>Observed pooled ER 观测合并互动率: ${D.budget_top_cells.er[p.dataIndex]}%`},
  grid:{left:170,right:44,top:18,bottom:30},
  xAxis:{type:"value",...baseAxis,axisLabel:{...baseAxis.axisLabel,formatter:"{value}%"}},
  yAxis:{type:"category",data:D.budget_top_cells.labels.slice().reverse(),...baseAxis,axisLabel:{...baseAxis.axisLabel,fontSize:11}},
  series:[{type:"bar",barWidth:18,data:D.budget_top_cells.share.slice().reverse(),itemStyle:{color:ACCENT,borderRadius:[0,5,5,0]},
    label:{show:true,position:"right",fontSize:11,color:"#6e6e73",fontFamily:FONT,formatter:p=>p.value+"%"}}]
});
</script>
</body>
</html>
"""


def main() -> None:
    payload = build_payload()
    echarts_js = ECHARTS.read_text(encoding="utf-8")
    html = (
        TEMPLATE
        .replace("__ECHARTS__", echarts_js)
        .replace("__DATA_JSON__", json.dumps(payload, ensure_ascii=False))
        .replace("__REPO_URL__", "https://github.com/wangziyu618/fitness-kol-marketing-analytics")
        .replace("__DATA_URL__", "https://www.kaggle.com/datasets/atharvasoundankar/viral-social-media-trends-and-engagement-analysis")
    )
    out = OUT / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
