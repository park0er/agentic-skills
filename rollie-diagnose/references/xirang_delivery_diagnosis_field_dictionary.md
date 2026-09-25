---
name: xirang-delivery-diagnosis-field-dictionary
description: query_xirang_delivery_diagnosis（召回+业务过滤，息壤版）字段含义，供传参前确认使用
---

# 召回与业务过滤看板-息壤版（query_xirang_delivery_diagnosis）

漏斗位置：③ 召回+业务过滤

用途：排查广告在召回和业务过滤环节的拦截情况，定位是哪个 `index_ad_lifecycle`（业务过滤节点）导致过滤量异常。

## ⚠️ 参数命名风格与其他看板不同

**此看板过滤参数使用下划线风格**

| 正确写法 | 错误写法（其他看板的风格，此处不能用）|
|---|---|
| `ad_id` | `adId` |
| `campaign_id` | `campaignId` |
| `tag_id` | `tagId` |


## 支持的过滤参数

| 参数名 | 说明 |
|---|---|
| `customer_id` | 过滤到指定账户（下划线） |
| `ad_id` | 过滤到指定广告（下划线） |
| `campaign_id` | 过滤到指定计划（下划线） |
| `tag_id` | 过滤到指定广告位（下划线） |
| `media_type` | 过滤到指定媒体类型 |

## 维度（group_by 可选值）

| canonical_key | 后端字段名 | 中文含义 | 诊断用途 |
|---|---|---|---|
| `index_ad_lifecycle` | `index_ad_lifecycle` | 业务过滤环节名称 | **最核心的 group_by**，看哪个 index_ad_lifecycle 过滤量异常增大。 |
| `campaign_id` | `campaign_id` | 计划 ID | 按计划下钻 |
| `ad_id` | `ad_id` | 广告 ID | 按广告下钻 |
| `tag_id` | `tag_id` | 广告位 ID | 按广告位下钻 |
| `media_type` | `media_type` | 媒体类型 | 按媒体类型下钻 |
| `dt` | `dt` | 时间 | 查看过滤量随时间的变化趋势；**必须与 `time_granularity` 配对使用**，单独传 `time_granularity` 无效 |

**注意：此看板不支持搜索词（query/keyword/search query）维度查询。**

## 指标（measures 可选值）

| canonical_key | 后端字段名 | 中文含义 | 诊断用途 |
|---|---|---|---|
| `index_filter_count` | `index_filter_count` | 过滤量 | **核心指标**，被该 index_ad_lifecycle 拦截的广告次数 |

## 时间粒度（time_granularity）

> ⚠️ `time_granularity` 必须与 `split.group_by = "dt"` 同时使用，单独传无效。

| time_granularity 值 | 含义 | dt 字段格式 | 建议时间范围 |
|---:|---|---|---|
| `300` | 按5分钟 | `"YYYY-MM-DD HH:MM"` | ≤ 1天 |
| `3600` | 按小时 | `"YYYY-MM-DD HH:MM"` | ≤ 3天 |
| `86400` | 按天 | `"YYYY-MM-DD"` | ≤ 14天 |
| `86401` | 日均（汇总均值） | 无，返回1行 | 任意 |
| `86402` | 合计（默认值） | 无，返回1行 | 任意 |
| `604800` | 按周 | `"YYYY-MM-DD"`（周起始日） | ≤ 30天 |
| `2592000` | 按月 | `"YYYY-MM"` | ≤ 90天 |

不传 `time_granularity` 时默认 `86402`（合计，整段1行），等价于不按时间分组，无法看趋势。

## 典型查询示例

按过滤环节分组：
```json
{
  "time": {
    "start_time": "2026-03-01T00:00:00+08:00",
    "end_time": "2026-03-01T08:00:00+08:00",
    "compare": true
  },
  "filters": { "ad_id": "400016661", "tag_id": "1.11.t.1" },
  "split": { "group_by": "index_ad_lifecycle" },
  "measures": ["index_filter_count"]
}
```

按小时看趋势（`group_by=dt` 必须搭配 `time_granularity`）：
```json
{
  "time": {
    "start_time": "2026-03-01T00:00:00+08:00",
    "end_time": "2026-03-01T23:59:59+08:00",
    "compare": true
  },
  "filters": { "ad_id": "400016661" },
  "split": { "group_by": "dt", "time_granularity": 3600 },
  "measures": ["index_filter_count"]
}
```

## 诊断要点

- 必须查两次：一次整体（不带 group_by）确认总过滤量，一次 `group_by=index_ad_lifecycle` 定位具体环节
- `index_ad_lifecycle` 过滤量同比大幅上升的那个节点即为问题所在
- 如果出现具体过滤码，调用 `--path /api/v1/query/filter-rule` 查询过滤码含义