# 数据来源说明 / Data Source

## 数据集 Dataset

- **名称 Name**: Viral Social Media Trends & Engagement Analysis
- **作者 Author**: Atharva Soundankar (Kaggle)
- **链接 URL**: https://www.kaggle.com/datasets/atharvasoundankar/viral-social-media-trends-and-engagement-analysis
- **许可 License**: [CC0: Public Domain](https://creativecommons.org/publicdomain/zero/1.0/) — 可自由使用、修改、再发布，无需署名
- **获取方式 Acquisition**: Kaggle 公开下载端点（无需鉴权），获取日期 2026-09-24：
  ```
  curl -L -o dataset.zip "https://www.kaggle.com/api/v1/datasets/download/atharvasoundankar/viral-social-media-trends-and-engagement-analysis"
  ```

## 文件指纹 File fingerprints (SHA-256)

| 文件 | SHA-256 |
|---|---|
| `Cleaned_Viral_Social_Media_Trends.csv` (410,182 B) | `804A023688CD81F7B09E1CD7A9A4B60BF98765719574F8D71CA2E60731731088` |
| `Viral_Social_Media_Trends.csv` (355,172 B) | `447ADDE8E699D58B19CDFCE98DD203EBEA1FC46D891C3001CB0735A995D455EB` |

两文件指标完全一致；清洗版仅多出 `Post_Date` 列，本仓库以清洗版为分析底表。
Both files agree on all metrics; the cleaned file only adds `Post_Date` and is used as the analysis base.

## 字段口径 Field dictionary

| 字段 | 类型 | 口径 |
|---|---|---|
| Post_ID | string | 帖子唯一标识（Post_1 … Post_5000） |
| Post_Date | date | 发布日期，2022-01-01 – 2023-12-30，日粒度 |
| Platform | enum | TikTok / Instagram / Twitter / YouTube |
| Hashtag | enum | #Fitness #Education #Challenge #Comedy #Dance #Music #Tech #Fashion #Viral #Gaming |
| Content_Type | enum | Video / Shorts / Post / Tweet / Live Stream / Reel |
| Region | enum | USA / UK / Canada / Australia / Germany / India / Japan / Brazil |
| Views / Likes / Shares / Comments | int | 曝光 / 点赞 / 分享 / 评论量 |
| Engagement_Level | enum | High / Medium / Low（原始标签；经校验与互动率三分位一致率仅约 1/3，**分析中不采用**） |

## 已知注意事项 Known caveats

- 数据卡未披露采集方式，数值模式提示为模拟/样例数据；本项目结论描述数据集内部结构，不直接外推为市场真实值。
  The dataset card does not disclose collection methodology; value patterns suggest simulated data. Conclusions describe structure within this dataset, not market ground truth.
- 363 行（7.26%）存在 互动量 > 曝光量 的物理不可能值，已在派生副本中剔除并完整记录（见 `data/processed/data_quality_report.md`），原始文件未做任何修改。
- 无粉丝数 / 小时级时间 / 成本字段；达人层级以曝光四分位构造代理，成本模型基于公开报价基准（推断层，已显式标注）。
