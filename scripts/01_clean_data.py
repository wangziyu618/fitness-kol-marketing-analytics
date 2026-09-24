# -*- coding: utf-8 -*-
"""
01_clean_data.py
数据清洗与特征工程
Data cleaning & feature engineering for the viral social media trends dataset.

输入 Input : data/raw/Viral_Social_Media_Trends.csv
             data/raw/Cleaned_Viral_Social_Media_Trends.csv
输出 Output: data/processed/posts_clean.csv        (全量清洗后数据 / cleaned full data)
             data/processed/posts_fitness.csv      (#Fitness 垂类子集 / fitness subset)
             data/processed/data_quality_report.md (数据质量报告 / data quality report)

原则 Principles:
- 不修改原始文件，所有修正发生在派生副本中
  Raw files are never modified; every fix happens in derived copies.
- 每一条剔除规则都可追溯（规则、数量、影响分解）
  Every exclusion rule is traceable (rule, count, breakdown).
"""
from pathlib import Path
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

F_RAW = RAW / "Viral_Social_Media_Trends.csv"
F_CLN = RAW / "Cleaned_Viral_Social_Media_Trends.csv"

TIER_LABELS = ["T1 Emerging reach", "T2 Growth reach", "T3 Established reach", "T4 Mega reach"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    log = []  # 质量报告行 / lines for the quality report

    # ---------- 1. 读取与一致性校验 / load & cross-file consistency ----------
    raw = pd.read_csv(F_RAW)
    cln = pd.read_csv(F_CLN)

    assert raw["Post_ID"].is_unique and cln["Post_ID"].is_unique, "Post_ID 存在重复 / duplicate Post_ID"
    merged = raw.merge(
        cln.drop(columns=["Post_Date"]), on="Post_ID", suffixes=("_r", "_c"), validate="one_to_one"
    )
    metric_cols = ["Platform", "Hashtag", "Content_Type", "Region", "Views", "Likes", "Shares", "Comments", "Engagement_Level"]
    consistent = all((merged[f"{c}_r"] == merged[f"{c}_c"]).all() for c in metric_cols)
    assert consistent, "两个原始文件指标不一致 / raw vs cleaned mismatch"
    assert len(merged) == len(raw) == len(cln), "行数不一致 / row count mismatch"
    log.append(f"- 两份原始文件指标完全一致，清洗版仅多出 `Post_Date` 字段；以清洗版为分析底表。")
    log.append(f"  Both raw files agree on all metrics; the cleaned file only adds `Post_Date` and is used as base.")

    df = cln.copy()

    # ---------- 2. 类型与缺失 / types & missingness ----------
    for c in ["Post_ID", "Platform", "Hashtag", "Content_Type", "Region", "Engagement_Level"]:
        df[c] = df[c].astype(str).str.strip()
    for c in ["Views", "Likes", "Shares", "Comments"]:
        df[c] = pd.to_numeric(df[c], errors="raise").astype("int64")
    df["Post_Date"] = pd.to_datetime(df["Post_Date"], format="%Y-%m-%d")

    missing = df.isna().sum()
    log.append(f"- 缺失值：全字段缺失数为 {int(missing.sum())} / Missing values across all fields: {int(missing.sum())}")
    neg = (df[["Views", "Likes", "Shares", "Comments"]] < 0).sum().sum()
    log.append(f"- 负值指标行数：{int(neg)} / Rows with negative metrics: {int(neg)}")

    # ---------- 3. 有效性规则：互动量不可超过曝光量 / validity rule ----------
    # 在所有平台口径下，点赞/分享/评论均发生在观看之后，因此 (Likes+Shares+Comments) > Views 的记录
    # 物理上不可能成立（合成数据的独立抽样伪影）。剔除并在报告中完全披露。
    # Engagements are a subset of views on every platform; rows violating this are impossible
    # (an artifact of independent sampling in synthetic data) and are excluded with full disclosure.
    df["Interactions"] = df["Likes"] + df["Shares"] + df["Comments"]
    invalid_mask = df["Interactions"] > df["Views"]
    n_invalid = int(invalid_mask.sum())
    log.append(
        f"- 剔除无效记录：Interactions > Views 共 {n_invalid} 行（{n_invalid / len(df) * 100:.2f}%）"
        f" / Excluded {n_invalid} rows ({n_invalid / len(df) * 100:.2f}%) where interactions exceed views."
    )
    by_tag = df.loc[invalid_mask, "Hashtag"].value_counts().to_dict()
    by_platform = df.loc[invalid_mask, "Platform"].value_counts().to_dict()
    log.append(f"  - 按话题分布 / by hashtag: {by_tag}")
    log.append(f"  - 按平台分布 / by platform: {by_platform}")
    df = df.loc[~invalid_mask].reset_index(drop=True)

    # ---------- 4. 特征工程 / feature engineering ----------
    df["Engagement_Rate"] = df["Interactions"] / df["Views"]
    df["Like_Rate"] = df["Likes"] / df["Views"]
    df["Share_Rate"] = df["Shares"] / df["Views"]
    df["Comment_Rate"] = df["Comments"] / df["Views"]

    df["Year"] = df["Post_Date"].dt.year
    df["Post_Month"] = df["Post_Date"].dt.strftime("%Y-%m")
    df["Post_Quarter"] = df["Post_Date"].dt.to_period("Q").astype(str)
    df["Day_Of_Week"] = df["Post_Date"].dt.day_name()

    df["Is_Fitness"] = (df["Hashtag"] == "#Fitness").astype(int)

    # 达人层级代理：数据无粉丝数字段，以帖子曝光量（Views）四分位数构造「传播层级」。
    # Influencer tier proxy: no follower field exists, so reach tiers are built from
    # dataset-wide Views quartiles. Explicitly an inference-level construct.
    q1, q2, q3 = df["Views"].quantile([0.25, 0.5, 0.75])
    df["Reach_Tier"] = pd.qcut(df["Views"], 4, labels=TIER_LABELS).astype(str)
    log.append(
        f"- 传播层级（按全量数据 Views 四分位 / reach tiers by dataset-wide Views quartiles）: "
        f"T1 ≤ {q1:,.0f} | T2 ≤ {q2:,.0f} | T3 ≤ {q3:,.0f} | T4 > {q3:,.0f}"
    )

    # 内容形式归组 / content-format grouping
    fmt_map = {
        "Video": "Long-form video", "Live Stream": "Live stream",
        "Shorts": "Short video", "Reel": "Short video",
        "Post": "Image post", "Tweet": "Text post",
    }
    df["Format_Group"] = df["Content_Type"].map(fmt_map)

    # ---------- 5. 与原始 Engagement_Level 的一致性检查（只报告，不使用） ----------
    er_q = df["Engagement_Rate"].quantile([1 / 3, 2 / 3]).values
    recomputed = pd.cut(
        df["Engagement_Rate"], [-float("inf"), er_q[0], er_q[1], float("inf")],
        labels=["Low", "Medium", "High"],
    )
    agreement = (recomputed.astype(str) == df["Engagement_Level"]).mean()
    log.append(
        f"- 原始 `Engagement_Level` 与按互动率三分位重算结果一致率仅 {agreement * 100:.1f}%，"
        f"判定该标签并非互动率的确定性函数；分析中不采用该字段，仅使用可复核的计算指标。"
    )
    log.append(
        f"  Original `Engagement_Level` agrees with recomputed ER tertiles only {agreement * 100:.1f}% of the time; "
        f"it is not used in analysis — only reproducible computed metrics are used."
    )

    # ---------- 6. 输出 / outputs ----------
    df.to_csv(OUT / "posts_clean.csv", index=False, encoding="utf-8")
    fit = df[df["Is_Fitness"] == 1].copy()
    fit.to_csv(OUT / "posts_fitness.csv", index=False, encoding="utf-8")

    header = [
        "# 数据质量报告 / Data Quality Report",
        "",
        "## 文件指纹 / File fingerprints (SHA-256)",
        f"- `Viral_Social_Media_Trends.csv`: `{sha256(F_RAW)}`",
        f"- `Cleaned_Viral_Social_Media_Trends.csv`: `{sha256(F_CLN)}`",
        "",
        f"## 规模 / Shape: 原始 {len(cln)} 行 → 清洗后 {len(df)} 行；#Fitness 子集 {len(fit)} 行",
        f"(raw {len(cln)} rows → cleaned {len(df)} rows; #Fitness subset {len(fit)} rows)",
        "",
        "## 检查与处理记录 / Checks & actions",
        *log,
    ]
    (OUT / "data_quality_report.md").write_text("\n".join(header), encoding="utf-8")

    print(f"cleaned rows: {len(df)} | fitness rows: {len(fit)} | excluded invalid: {n_invalid}")
    print(f"tier bounds: {q1:,.0f} / {q2:,.0f} / {q3:,.0f}")


if __name__ == "__main__":
    main()
