-- ============================================================================
-- 多维分析查询集 / Multi-dimensional analysis queries (SQLite dialect)
-- 输入表 Input table: posts  (由 02_run_analysis.py 从 posts_clean.csv 载入)
-- 口径说明 Definitions:
--   pooled_er        = SUM(Interactions) * 1.0 / SUM(Views)   -- 合并互动率（行业口径）
--   median_er        = 中位数互动率（窗口函数实现）            -- median engagement rate
--   Is_Fitness = 1   表示 #Fitness 垂类子集                   -- fitness vertical subset
-- ============================================================================

-- @name: q01_overview
-- 全局概览：总量、垂类占比、时间跨度 / Global overview KPIs
SELECT
    COUNT(*)                                                        AS total_posts,
    SUM(Is_Fitness)                                                 AS fitness_posts,
    COUNT(DISTINCT Platform)                                        AS platforms,
    COUNT(DISTINCT Hashtag)                                         AS hashtags,
    MIN(Post_Date)                                                  AS date_min,
    MAX(Post_Date)                                                  AS date_max,
    SUM(Views)                                                      AS total_views,
    SUM(Interactions)                                               AS total_interactions,
    ROUND(SUM(Interactions) * 1.0 / SUM(Views), 6)                  AS pooled_er_all
FROM posts;

-- @name: q02_platform_fitness
-- 业务问题1·平台：#Fitness 垂类各平台表现（合并互动率 + 中位互动率 + 互动结构）
-- Q1 Platforms: fitness-vertical performance per platform
WITH f AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY Platform ORDER BY Engagement_Rate) AS rn,
           COUNT(*)     OVER (PARTITION BY Platform)                          AS cnt
    FROM posts WHERE Is_Fitness = 1
)
SELECT Platform,
       COUNT(*)                                             AS n_posts,
       SUM(Views)                                           AS total_views,
       SUM(Interactions)                                    AS total_interactions,
       ROUND(SUM(Interactions)*1.0/SUM(Views), 6)           AS pooled_er,
       ROUND(AVG(CASE WHEN rn IN ((cnt+1)/2, (cnt+2)/2) THEN Engagement_Rate END), 6) AS median_er,
       ROUND(SUM(Likes)*1.0/SUM(Interactions), 4)           AS like_share,
       ROUND(SUM(Shares)*1.0/SUM(Interactions), 4)          AS share_share,
       ROUND(SUM(Comments)*1.0/SUM(Interactions), 4)        AS comment_share
FROM f
GROUP BY Platform
ORDER BY pooled_er DESC;

-- @name: q03_vertical_benchmark
-- 垂类基准：#Fitness 与其余话题的合并互动率对比（市场背景）
-- Vertical benchmark: #Fitness vs other hashtags
SELECT Hashtag,
       COUNT(*)                                             AS n_posts,
       ROUND(SUM(Interactions)*1.0/SUM(Views), 6)           AS pooled_er,
       ROUND(AVG(Views), 0)                                 AS avg_views
FROM posts
GROUP BY Hashtag
ORDER BY pooled_er DESC;

-- @name: q04_tier_fitness
-- 业务问题2·达人层级（传播层级代理）：层级 × 互动效率（#Fitness 垂类）
-- Q2 Creator tier (reach-based proxy): tier × engagement efficiency, fitness vertical
WITH f AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY Reach_Tier ORDER BY Engagement_Rate) AS rn,
           COUNT(*)     OVER (PARTITION BY Reach_Tier)                          AS cnt
    FROM posts WHERE Is_Fitness = 1
)
SELECT Reach_Tier,
       COUNT(*)                                             AS n_posts,
       ROUND(AVG(Views), 0)                                 AS avg_views,
       ROUND(SUM(Interactions)*1.0/SUM(Views), 6)           AS pooled_er,
       ROUND(AVG(CASE WHEN rn IN ((cnt+1)/2, (cnt+2)/2) THEN Engagement_Rate END), 6) AS median_er,
       ROUND(SUM(Shares)*1.0/SUM(Views), 6)                 AS pooled_share_rate
FROM f
GROUP BY Reach_Tier
ORDER BY Reach_Tier;

-- @name: q04b_tier_all
-- 层级效应的市场级验证（全量数据）/ Market-wide validation of the tier effect
WITH a AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY Reach_Tier ORDER BY Engagement_Rate) AS rn,
           COUNT(*)     OVER (PARTITION BY Reach_Tier)                          AS cnt
    FROM posts
)
SELECT Reach_Tier,
       COUNT(*)                                             AS n_posts,
       ROUND(AVG(CASE WHEN rn IN ((cnt+1)/2, (cnt+2)/2) THEN Engagement_Rate END), 6) AS median_er
FROM a
GROUP BY Reach_Tier
ORDER BY Reach_Tier;

-- @name: q05_format_platform_heatmap
-- 业务问题3·内容形式：平台 × 形式 互动率热力图（#Fitness 垂类）
-- Q3 Content format: platform × format heatmap, fitness vertical
SELECT Platform,
       Format_Group,
       COUNT(*)                                             AS n_posts,
       ROUND(SUM(Interactions)*1.0/SUM(Views), 6)           AS pooled_er
FROM posts
WHERE Is_Fitness = 1
GROUP BY Platform, Format_Group
ORDER BY Platform, Format_Group;

-- @name: q06_monthly_trend
-- 业务问题4·发布时间：月度发帖量与互动率趋势（#Fitness 垂类，分平台）
-- Q4 Timing: monthly volume & ER trend by platform, fitness vertical
SELECT Post_Month,
       Platform,
       COUNT(*)                                             AS n_posts,
       ROUND(SUM(Interactions)*1.0/SUM(Views), 6)           AS pooled_er
FROM posts
WHERE Is_Fitness = 1
GROUP BY Post_Month, Platform
ORDER BY Post_Month;

-- @name: q07_dow
-- 业务问题4·发布时间：星期分布（#Fitness 垂类）
-- Q4 Timing: day-of-week pattern, fitness vertical
SELECT Day_Of_Week,
       COUNT(*)                                             AS n_posts,
       ROUND(SUM(Interactions)*1.0/SUM(Views), 6)           AS pooled_er,
       ROUND(AVG(Views), 0)                                 AS avg_views
FROM posts
WHERE Is_Fitness = 1
GROUP BY Day_Of_Week
ORDER BY pooled_er DESC;

-- @name: q08_region_platform
-- 国际市场：地区 × 平台 表现（#Fitness 垂类）——服务国际化 BD 视角
-- International view: region × platform, fitness vertical
SELECT Region,
       COUNT(*)                                             AS n_posts,
       ROUND(SUM(Interactions)*1.0/SUM(Views), 6)           AS pooled_er,
       ROUND(AVG(Views), 0)                                 AS avg_views
FROM posts
WHERE Is_Fitness = 1
GROUP BY Region
ORDER BY pooled_er DESC;

-- @name: q09_format_fitness
-- 内容形式整体表现（#Fitness 垂类）/ Overall format performance, fitness vertical
SELECT Format_Group,
       COUNT(*)                                             AS n_posts,
       ROUND(SUM(Interactions)*1.0/SUM(Views), 6)           AS pooled_er,
       ROUND(SUM(Shares)*1.0/SUM(Views), 6)                 AS pooled_share_rate
FROM posts
WHERE Is_Fitness = 1
GROUP BY Format_Group
ORDER BY pooled_er DESC;

-- @name: q10_efficiency_cells
-- 预算模型输入：平台 × 形式 效率单元（#Fitness 垂类）
-- Budget model input: platform × format efficiency cells, fitness vertical
SELECT Platform,
       Format_Group,
       COUNT(*)                                             AS n_posts,
       SUM(Views)                                           AS total_views,
       SUM(Interactions)                                    AS total_interactions,
       ROUND(SUM(Interactions)*1.0/SUM(Views), 6)           AS pooled_er,
       ROUND(AVG(Views), 0)                                 AS avg_views_per_post,
       ROUND(AVG(Interactions), 0)                          AS avg_interactions_per_post
FROM posts
WHERE Is_Fitness = 1
GROUP BY Platform, Format_Group
ORDER BY pooled_er DESC;

-- @name: q11_fitness_monthly_all
-- 垂类背景：全量数据月度趋势（#Fitness vs 其他话题）
-- Context: monthly trend, fitness vs non-fitness
SELECT Post_Month,
       Is_Fitness,
       COUNT(*)                                             AS n_posts,
       ROUND(SUM(Interactions)*1.0/SUM(Views), 6)           AS pooled_er
FROM posts
GROUP BY Post_Month, Is_Fitness
ORDER BY Post_Month;
