---
name: xirang-pre-ranking-field-dictionary
description: query_xirang_pre_ranking（粗排链路多维分析）字段含义，供传参前确认使用
---

# 粗排链路多维分析看板-息壤版（query_xirang_pre_ranking）

漏斗位置：**④ 粗排(息壤)**（广告进入粗排模型打分，按 pscore 排序截断）

用途：排查粗排阶段请求量变化与 pscore 分布异常。常用 `count` 指标配合 `media_type`、`tag_id`、`recall_filter_reason`、`recall_channel_name` 等维度下钻分析。

---

## 一、维度字段

| 字段名 | 中文名 | 维度说明 | 枚举值说明 |
|---|---|---|---|
| `dt` | 时间, 时间维度 | 需配合 `time_granularity` 使用；见下方时间粒度编码表 | — |
| `media_type` | 媒体, 媒体类型 | 媒体 | 完整清单见 `./enums/media_type_cn_mapping.md` |
| `tag_id` | 广告位, 广告位ID | 广告位 | `1.1.1.1`=小米视频-灵活广告位。完整清单见 `./enums/xirang_ad_effect_enum_tag_id.md` |
| `env` | 集群, 服务集群 | 粗排服务所在集群 | `guyu-recall-union-did-exp-gpu` 等，用于区分线上集群和实验集群 |
| `recall_expid` | 粗排实验ID | 粗排层实验 ID，按 `tag_id` 粒度 | 数字 ID，如 `2363986` |
| `chunfen_expids` | 召回层主实验ID | 上游召回层主实验 ID | 数字 ID |
| `chunfen_expids2` | 召回层辅实验ID | 上游召回层辅实验 ID | 数字 ID，如 `2248861` |
| `dsp` | 二级DSP | 二级 DSP 标识 | DSP 名称字符串 |
| `app_id` | 应用ID, App ID | 小米开放平台注册的应用标识 | 数字 ID，如 `666593` |
| `billing_type` | 计费类型 | 广告计费方式 | `3`=CPD |
| `ad_id` | 广告ID, 创意ID | 广告创意标识 | 数字 ID，如 `410512828` |
| `target_conv_type` | 目标转化类型 | 广告投放目标转化类型 | `2`=下载 |
| `recall_filter_reason` | 粗排过滤原因 | 粗排阶段广告被过滤的原因 | `TOPN_CUT`=截断丢弃、其他待确认 |
| `fresh_ad` | 是否新广告 | 是否新广告标识 | `0`=否、`1`=是 |
| `is_discard` | 是否被过滤 | 粗排阶段是否被过滤丢弃 | `0`=未过滤、`1`=被过滤 |
| `recall_channel_name` | 召回通路来源 | 广告召回通道来源 | `ann`=向量召回(ANN)、其他待确认 |
| `campaign_id` | 广告计划, 推广计划ID | 广告计划的唯一标识 | 数字 ID，如 `401100570` |
| `deep_target_conv_type` | 深层目标转化类型 | 深层转化目标类型 | `0`=无 |
| `search_keyword` | 搜索词 | 搜索广告场景的搜索词 | 字符串 |

---

## 二、指标字段

| 字段名 | 中文名 | 公式说明 |
|---|---|---|
| `count` | 请求数 | 进入粗排的请求总数 |
| `sum_pscore_recall` | 总计pscore_粗排 | pscore 求和值 |
| `avg_pscore_recall` | 平均pscore_粗排 | `sum_pscore_recall / count`。进入粗排请求的平均 pscore |

---

## 三、时间粒度

息壤看板支持的时间粒度编码（通过 `time_granularity` 参数传入）：

| 编码 | 含义 |
|---|---|
| `86402` | 合计（默认） |
| `86400` | 天 |
| `3600` | 小时 |
| `300` | 5 分钟 |

---

## 四、调用示例

```bash
# 默认查询（汇总）
bash scripts/query/dashboard_query.sh \
  --params '{"dashboard":"query_xirang_pre_ranking","time":{"start_time":"2026-06-07T00:00:00+08:00","end_time":"2026-06-08T00:00:00+08:00","compare":false}}' \
  --session-id <session_id>

# 按媒体分组
bash scripts/query/dashboard_query.sh \
  --params '{"dashboard":"query_xirang_pre_ranking","time":{"start_time":"2026-06-07T00:00:00+08:00","end_time":"2026-06-08T00:00:00+08:00","compare":false},"split":{"group_by":"media_type","top":10}}' \
  --session-id <session_id>

# 按粗排过滤原因下钻
bash scripts/query/dashboard_query.sh \
  --params '{"dashboard":"query_xirang_pre_ranking","time":{"start_time":"2026-06-07T00:00:00+08:00","end_time":"2026-06-08T00:00:00+08:00","compare":false},"split":{"group_by":"recall_filter_reason","top":10}}' \
  --session-id <session_id>
```
