---
name: guyu-stat-field-dictionary
description: query_guyu_stat（精排）字段含义，供传参前确认使用
---

# 精排看板（query_guyu_stat）

漏斗位置：⑤ 精排

用途：排查广告在精排阶段的拦截和模型打分情况，重点关注 OCPX 策略过滤和 PCOC 偏离。

## 支持的过滤参数

| 参数名 | 说明 |
|---|---|
| `adId` | 过滤到指定广告 |
| `campaignId` | 过滤到指定计划 |
| `tagId` | 过滤到指定广告位 |
| `keyword` | 搜索词 |

## 维度（group_by 可选值）

| canonical_key | 后端字段名 | 中文含义 | 诊断用途 |
|---|---|---|---|
| `filterReason` | `filterReason` | 精排过滤原因 | **最常用**，看哪种原因的过滤量同比变化最大 |
| `adId` | `adId` | 广告 ID | 按广告下钻 |
| `campaignId` | `campaignId` | 计划 ID | 按计划下钻 |
| `tagId` | `tagId` | 广告位 ID | 按广告位下钻 |
| `keyword` | `keyword` | 搜索词 | 按搜索词过滤/下钻排查搜索场景精排拦截 |

## 指标（measures 可选值）

| canonical_key | 后端字段名 | 中文含义 | 诊断用途 |
|---|---|---|---|
| `count` | `total` | 进入精排的总量 | 基数 |
| `pctr` | `pCtr` | 预估 CTR 总和 | 除以 count 得均值，反映点击率预估 |
| `pcvr` | `pCvr` | 预估 CVR 总和 | 用于计算 PCOC，判断模型是否高估或低估 |
| `pdeepcvr` | `pDeepCvr` | 预估深层 CVR 总和 | 深层转化目标（如 ROI 目标）时使用 |

## `filterReason` 重要取值

| 取值 | 中文含义 | 处置方式 |
|---|---|---|
| `OCPX_STRATEGY_FILTER` | 被 OCPX 策略拦截 | **必须立刻补查 `query_ocpx_strategy`，这是铁律** |
| `LOW_BID` | 出价低被过滤 | 建议广告主提高出价 |
| `QUOTA_LIMIT` | 配额限制 | 系统配额问题，L2 跟进 |
| `PASS` | 通过精排 | 正常 |

## 典型查询示例

### 排查精排过滤原因

```json
{
  "time": {
    "start_time": "2026-03-01T00:00:00+08:00",
    "end_time": "2026-03-01T08:00:00+08:00",
    "compare": true,
    "comparison_start_time": "2026-02-28T00:00:00+08:00",
    "comparison_end_time": "2026-02-28T08:00:00+08:00"
  },
  "filters": { "adId": "400016661", "tagId": "1.11.t.1" },
  "split": { "group_by": "filterReason" },
  "measures": ["count", "pctr", "pcvr", "pdeepcvr"]
}
```

### 搜索词维度下钻

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": true,
    "comparison_start_time": "2026-05-31T00:00:00+08:00",
    "comparison_end_time": "2026-06-01T00:00:00+08:00"
  },
  "filters": { "adId": "400016661", "tagId": "1.24.4.12", "keyword": "抖音" },
  "split": { "group_by": "keyword", "top": 20 },
  "measures": ["count", "pctr", "pcvr"]
}
```

## 诊断要点

- 看到 `OCPX_STRATEGY_FILTER` 同比增大 → **必须补查 `query_ocpx_strategy`（with `group_by=sFilerReason`）**，不能跳过
- `pcvr` 均值同比明显下降 → 模型对该广告的转化预估变差，精排竞争力下降
- 搜索场景排查时，先用 `group_by=keyword` 看 top 搜索词的 count 分布，再针对异常搜索词加 `filters={"keyword":"xxx"}` 缩小范围
