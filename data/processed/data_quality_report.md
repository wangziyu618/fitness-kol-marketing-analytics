# 数据质量报告 / Data Quality Report

## 文件指纹 / File fingerprints (SHA-256)
- `Viral_Social_Media_Trends.csv`: `447adde8e699d58b19cdfce98dd203ebea1fc46d891c3001cb0735a995d455eb`
- `Cleaned_Viral_Social_Media_Trends.csv`: `804a023688cd81f7b09e1cd7a9a4b60bf98765719574f8d71ca2e60731731088`

## 规模 / Shape: 原始 5000 行 → 清洗后 4637 行；#Fitness 子集 497 行
(raw 5000 rows → cleaned 4637 rows; #Fitness subset 497 rows)

## 检查与处理记录 / Checks & actions
- 两份原始文件指标完全一致，清洗版仅多出 `Post_Date` 字段；以清洗版为分析底表。
  Both raw files agree on all metrics; the cleaned file only adds `Post_Date` and is used as base.
- 缺失值：全字段缺失数为 0 / Missing values across all fields: 0
- 负值指标行数：0 / Rows with negative metrics: 0
- 剔除无效记录：Interactions > Views 共 363 行（7.26%） / Excluded 363 rows (7.26%) where interactions exceed views.
  - 按话题分布 / by hashtag: {'#Dance': 43, '#Challenge': 40, '#Fitness': 39, '#Tech': 38, '#Education': 37, '#Gaming': 36, '#Comedy': 36, '#Viral': 32, '#Music': 31, '#Fashion': 31}
  - 按平台分布 / by platform: {'Instagram': 107, 'TikTok': 92, 'Twitter': 89, 'YouTube': 75}
- 传播层级（按全量数据 Views 四分位 / reach tiers by dataset-wide Views quartiles）: T1 ≤ 1,482,566 | T2 ≤ 2,685,008 | T3 ≤ 3,857,161 | T4 > 3,857,161
- 原始 `Engagement_Level` 与按互动率三分位重算结果一致率仅 34.1%，判定该标签并非互动率的确定性函数；分析中不采用该字段，仅使用可复核的计算指标。
  Original `Engagement_Level` agrees with recomputed ER tertiles only 34.1% of the time; it is not used in analysis — only reproducible computed metrics are used.