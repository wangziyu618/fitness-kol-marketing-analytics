# -*- coding: utf-8 -*-
"""
02_run_analysis.py
多维分析执行器 / Multi-dimensional analysis runner.

流程 Pipeline:
1. 将 posts_clean.csv 载入 SQLite 内存库，逐条执行 analysis/queries.sql 中的命名查询，
   结果导出至 data/processed/results/*.csv。
   Loads cleaned posts into in-memory SQLite, runs every named query in
   analysis/queries.sql, exports results to data/processed/results/*.csv.
2. 预算分配模型（推断层，显式标注）：基于公开报价基准估算各平台×形式单帖成本，
   对比「按发帖量铺开」与「按互动效率分配」两种预算方案的预期互动量。
   Budget allocation model (INFERENCE layer, explicitly marked): benchmark cost per
   post by platform×format from public rate guides; contrasts activity-proportional
   vs efficiency-proportional allocation at a fixed illustrative budget.

外部基准来源 External benchmark sources (详见 report/STRATEGY_REPORT.md):
- LaunchPointHQ sports & fitness influencer rate guide (2026):
  https://www.launchpointhq.com/guides/rates/how-much-do-sports-fitness-influencers-charge
- Influencer Marketing Hub influencer rate benchmarks.
所有成本数值为公开区间中点的说明性取值，非真实成交价格。
All cost figures are illustrative midpoints of published ranges, not actual transaction prices.
"""
from pathlib import Path
import json
import re
import sqlite3

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RESULTS = PROCESSED / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

TOTAL_BUDGET_USD = 100_000  # 说明性预算 / illustrative budget

# 单帖成本基准（USD，公开报价区间中点的说明性取值）
# Benchmark cost per sponsored post (USD; illustrative midpoints of published ranges)
COST_BENCHMARK = {
    # (Platform, Format_Group): cost_usd
    ("TikTok", "Short video"): 1800,
    ("TikTok", "Live stream"): 2000,
    ("TikTok", "Long-form video"): 1800,
    ("TikTok", "Image post"): 500,
    ("TikTok", "Text post"): 400,
    ("Instagram", "Short video"): 1500,
    ("Instagram", "Image post"): 800,
    ("Instagram", "Long-form video"): 1800,
    ("Instagram", "Live stream"): 2000,
    ("Instagram", "Text post"): 400,
    ("YouTube", "Long-form video"): 2500,
    ("YouTube", "Short video"): 800,
    ("YouTube", "Live stream"): 2200,
    ("YouTube", "Image post"): 500,
    ("YouTube", "Text post"): 400,
    ("Twitter", "Text post"): 300,
    ("Twitter", "Image post"): 350,
    ("Twitter", "Short video"): 700,
    ("Twitter", "Live stream"): 1500,
    ("Twitter", "Long-form video"): 900,
}
DEFAULT_COST = 1000  # 兜底（不应触发）/ fallback (should not trigger)


def load_queries(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"-- @name:\s*(\w+)", text)
    queries = {}
    for i in range(1, len(parts), 2):
        name, body = parts[i], parts[i + 1]
        body = re.sub(r"--[^\n]*", "", body).strip().rstrip(";")
        queries[name] = body
    return queries


def run_sql(df: pd.DataFrame) -> dict:
    conn = sqlite3.connect(":memory:")
    df.to_sql("posts", conn, index=False, if_exists="replace")
    out = {}
    for name, sql in load_queries(ROOT / "analysis" / "queries.sql").items():
        res = pd.read_sql_query(sql, conn)
        res.to_csv(RESULTS / f"{name}.csv", index=False, encoding="utf-8")
        out[name] = res
        print(f"  {name}: {len(res)} rows")
    conn.close()
    return out


def budget_model(cells: pd.DataFrame) -> tuple:
    """预算分配模型（推断层）/ Budget allocation model (inference layer)."""
    b = cells.copy()
    b["cost_per_post_usd"] = b.apply(
        lambda r: COST_BENCHMARK.get((r["Platform"], r["Format_Group"]), DEFAULT_COST), axis=1
    )
    # 效率 = 每千美元预期互动量 / efficiency = expected engagements per $1,000
    b["engagements_per_1k"] = b["avg_interactions_per_post"] / b["cost_per_post_usd"] * 1000

    # 方案A（现状代理）：预算 ∝ 发帖量 / Plan A (status-quo proxy): budget ∝ posting activity
    b["current_share"] = b["n_posts"] / b["n_posts"].sum()
    # 方案B（效率导向）：预算 ∝ 单位成本互动效率 / Plan B: budget ∝ engagement efficiency
    b["recommended_share"] = b["engagements_per_1k"] / b["engagements_per_1k"].sum()

    for plan in ["current", "recommended"]:
        b[f"{plan}_budget"] = b[f"{plan}_share"] * TOTAL_BUDGET_USD
        # 预期互动 = 预算可购帖数 × 帖均互动 / expected engagements = posts affordable × avg interactions
        b[f"{plan}_engagements"] = b[f"{plan}_budget"] / b["cost_per_post_usd"] * b["avg_interactions_per_post"]

    cur_eng, rec_eng = b["current_engagements"].sum(), b["recommended_engagements"].sum()
    summary = {
        "total_budget_usd": TOTAL_BUDGET_USD,
        "current_expected_engagements": round(cur_eng),
        "recommended_expected_engagements": round(rec_eng),
        "projected_lift_pct": round((rec_eng - cur_eng) / cur_eng * 100, 1),
        "assumption": (
            "成本为公开报价区间中点的说明性取值；预期互动=预算/单帖成本×帖均互动。"
            "Cost figures are illustrative midpoints of published rate ranges; "
            "expected engagements = budget / cost-per-post × avg interactions-per-post."
        ),
    }
    cols = [
        "Platform", "Format_Group", "n_posts", "pooled_er", "avg_views_per_post",
        "avg_interactions_per_post", "cost_per_post_usd", "engagements_per_1k",
        "current_share", "recommended_share", "current_budget", "recommended_budget",
        "current_engagements", "recommended_engagements",
    ]
    b[cols].round(4).to_csv(RESULTS / "budget_model.csv", index=False, encoding="utf-8")
    return b, summary


def main() -> None:
    df = pd.read_csv(PROCESSED / "posts_clean.csv")
    print(f"loaded posts_clean.csv: {len(df)} rows")
    out = run_sql(df)

    budget_df, budget_summary = budget_model(out["q10_efficiency_cells"])
    print(f"budget model: projected lift = +{budget_summary['projected_lift_pct']}%")

    fit = df[df["Is_Fitness"] == 1]
    summary = {
        "budget": budget_summary,
        "kpis": {
            "total_posts": int(len(df)),
            "fitness_posts": int(len(fit)),
            "date_min": str(df["Post_Date"].min())[:10],
            "date_max": str(df["Post_Date"].max())[:10],
            "fitness_pooled_er": round(float(fit["Interactions"].sum() / fit["Views"].sum()), 6),
            "fitness_median_er": round(float(fit["Engagement_Rate"].median()), 6),
            "market_pooled_er": round(float(df["Interactions"].sum() / df["Views"].sum()), 6),
            "best_platform_fitness": str(out["q02_platform_fitness"].iloc[0]["Platform"]),
            "best_format_fitness": str(out["q09_format_fitness"].iloc[0]["Format_Group"]),
            "best_dow_fitness": str(out["q07_dow"].iloc[0]["Day_Of_Week"]),
            "top_region_fitness": str(out["q08_region_platform"].iloc[0]["Region"]),
        },
    }
    (RESULTS / "analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote analysis_summary.json")


if __name__ == "__main__":
    main()
