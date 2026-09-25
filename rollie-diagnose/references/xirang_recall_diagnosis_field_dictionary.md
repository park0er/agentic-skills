---
name: xirang-recall-diagnosis-field-dictionary
description: query_xirang_recall_diagnosis（召回链路多维分析，息壤版）字段含义与查询方法
---

# 召回链路多维分析看板-息壤版（query_xirang_recall_diagnosis）

漏斗位置：召回链路

用途：排查召回链路过滤原因，按流量/应用/客户/广告/引擎链路等维度下钻分析。

如需理解召回链路架构和业务逻辑，请参考：
→ references/guides/xirang_recall_diagnosis_guide.md

## 典型查询示例

### 示例一：查看某个广告位的召回总量

进入召回环节的总量，漏斗最顶端。只勾 `passMerge = -100`。

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": true,
    "compare_start_time": "2026-05-31T00:00:00+08:00",
    "compare_end_time": "2026-06-01T00:00:00+08:00"
  },
  "filters": { "ad_id": "400498383", "tag_id": "1.24.4.12", "passMerge": "-100" },
  "measures": ["recall_filter_count"]
}
```

### 示例二：按召回通路分组查看各通路效果

出召回通路层的量，即真正送出、即将进 merge 的候选量。必须同时勾 `passMerge = -100` 和 `recall_ad_lifecycle = passIndex`。

**注意**：一个请求可能同时在多条 pipeline 中通过，会有重复计数的情况，所以必须按 pipeline 分组才能定位问题。

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": true,
    "compare_start_time": "2026-05-31T00:00:00+08:00",
    "compare_end_time": "2026-06-01T00:00:00+08:00"
  },
  "filters": { "ad_id": "400498383", "tag_id": "1.24.4.12", "passMerge": "-100", "recall_ad_lifecycle": "passIndex" },
  "split": { "group_by": "recall_pipeline", "top": 50, "sort_by": "recall_filter_count" },
  "measures": ["recall_filter_count"]
}
```

### 示例三：查看真正出 merge 层的量

出 merge 层的量（首次 merge）。只勾 `passMerge = 1`。

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": true,
    "compare_start_time": "2026-05-31T00:00:00+08:00",
    "compare_end_time": "2026-06-01T00:00:00+08:00"
  },
  "filters": { "ad_id": "400498383", "tag_id": "1.24.4.12", "passMerge": "1" },
  "measures": ["recall_filter_count"]
}
```

### 示例四：查看被 merge 层过滤的量

进了 merge 但没出来 —— merge 环节的损耗。可选 `recall_ad_lifecycle = dropmerge` 或 `passMerge = 0`，两种勾法等价。

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": true,
    "compare_start_time": "2026-05-31T00:00:00+08:00",
    "compare_end_time": "2026-06-01T00:00:00+08:00"
  },
  "filters": { "ad_id": "400498383", "tag_id": "1.24.4.12", "recall_ad_lifecycle": "dropmerge" },
  "measures": ["recall_filter_count"]
}
```

## 指标（measures 可选值）

| 字段名 | 中文含义 | 说明 |
|---|---|---|
| `recall_filter_count` | 召回过滤数 | 当 `recall_ad_lifecycle = passIndex` 时含义是"通过"，其余场景都是"过滤" |

## 维度（group_by / filters 可选值）

| 字段名 | 中文含义 | 说明 |
|---|---|---|
| `dt` | 时间 | 时间维度，配合 `time_granularity` 使用 |
| `media_type` | 媒体类型 | 流量来源 |
| `tag_id` | 广告位ID | 广告位标识 |
| `recall_exp_id` | 召回实验ID | 召回实验标识 |
| `app_id` | 应用ID | 应用标识 |
| `customer_id` | 广告主账户ID | 效果广告主账户 |
| `oper_level1_industry` | 运营一级行业 | 运营一级自定义行业 |
| `oper_level2_industry` | 运营二级行业 | 运营二级自定义行业 |
| `ad_id` | 广告创意ID | 广告创意标识 |
| `campaign_id` | 广告计划ID | 广告计划标识 |
| `target_conv_type` | 目标转化类型 | 转化目标类型 |
| `deep_target_conv_type` | 深层目标转化类型 | 深层转化目标类型 |
| `rta_token` | RTA Token | RTA标识 |
| `recall_ad_lifecycle` | 召回生命周期状态 | 枚举值：`passIndex`=主路通过，`dropmerge`=被merge层过滤，其他值=各通路内过滤项名称 |
| `recall_pipeline` | 召回通路类型 | 枚举值：`white`=白名单通路，`ae`=ecp通路，`ann`=模型通路，`fresh`=新鲜度通路，`ee`=提价通路，其他=业务自定义通路 |
| `passMerge` | merge层状态标识 | 枚举值：`-100`=召回日志，`0`=被merge过滤，`1`=首次merge通过，`2`=二次merge |

**注意：此看板不支持搜索词（query/keyword/search query）维度查询。**

## 时间粒度（time_granularity）

`time_granularity` 必须与 `split.group_by = "dt"` 同时使用，单独传无效。

| time_granularity 值 | 含义 |
|---:|---|
| `300` | 按5分钟 |
| `3600` | 按小时 |
| `86400` | 按天 |
| `86402` | 合计（默认） |
| `604800` | 按周 |

## 注意事项

1. **当前看板无法查看业务过滤/TopN环节**，这些只能在引擎全链路看板查看
2. **当前看板无法深入分析 merge 层内部的具体策略执行情况**，只能看到输入和输出
3. **搜索位置没有 merge 层**，因此看搜索位置时只会有 `passMerge = -100 / 0`
