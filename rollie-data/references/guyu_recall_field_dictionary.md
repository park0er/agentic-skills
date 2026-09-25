---
name: guyu-recall-field-dictionary
description: query_guyu_recall（粗排）字段含义，供传参前确认使用
---

# 粗排看板（query_guyu_recall）

漏斗位置：④ 粗排

用途：排查广告在粗排阶段的拦截情况，评估模型打分（pctr/pcvr/pscore）是否异常下降。

## 支持的过滤参数

| 参数名 | 说明 |
|---|---|
| `adId` | 过滤到指定广告 |
| `campaignId` | 过滤到指定计划 |
| `tagId` | 过滤到指定广告位 |
| `searchQuery` | 搜索词|

## 维度（group_by 可选值）

| canonical_key | 后端字段名 | 中文含义 | 诊断用途 |
|---|---|---|---|
| `recallFilterReason` | `recallFilterReason` | 粗排过滤原因 | **最常用**，看哪种原因的过滤量同比变化最大 |
| `adId` | `adId` | 广告 ID | 按广告下钻 |
| `campaignId` | `campaignId` | 计划 ID | 按计划下钻 |
| `tagId` | `tagId` | 广告位 ID | 按广告位下钻 |
| `searchQuery` | `searchQuery` | 搜索词 | 按搜索词过滤/下钻排查搜索场景粗排过滤 |

## 指标（measures 可选值）

| canonical_key | 中文含义 | 诊断用途 |
|---|---|---|
| `count` | 进入粗排的总量 | 基数，判断流量规模是否本身缩减 |
| `pctr_avg` | 平均预估 CTR（×100000） | 模型对点击率的预估均值，下降说明模型认为广告点击吸引力变弱 |
| `pcvr_avg` | 平均预估 CVR（×100000） | 模型对转化率的预估均值 |
| `pscore_avg` | 平均综合评分 | 粗排综合排序分，明显下降说明广告在粗排竞争力整体下降 |

**注意：`pctr_avg` 和 `pcvr_avg` 的值已乘以 100000，比较时注意量级。**

## `recallFilterReason` 常见取值

| 取值 | 中文含义 |
|---|---|
| `PASS` | 通过粗排，未被过滤 |
| `LOW_PCTR` | 预估点击率过低被过滤 |
| `LOW_PSCORE` | 综合评分过低被过滤 |
| `BUDGET_LIMIT` | 预算限制 |
| `FREQ_LIMIT` | 频控限制 |
| `AD_ID_NOT_FOUND` | 广告ID不存在，可能是新建广告未获取信息 |
| `TOPN_CUT` | 竞争力不足-ecpm过低被截断 |
| `DISTINCT` | APPID内按ecpm去重过滤 |

## 典型查询示例

### 排查粗排过滤原因

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
  "split": { "group_by": "recallFilterReason" },
  "measures": ["count", "pscore_avg", "pctr_avg", "pcvr_avg"]
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
  "filters": { "adId": "400016661", "tagId": "1.24.4.12", "searchQuery": "抖音" },
  "split": { "group_by": "searchQuery", "top": 20 },
  "measures": ["count", "pscore_avg", "pctr_avg"]
}
```

## 诊断要点

- 粗排最重要的不是 pctr/pcvr 的绝对值，而是 **pscore_avg 的对比变化**
- `pscore_avg` 明显下降 → 广告在粗排阶段竞争力整体下滑，可能是出价降低或模型打分变差
- `count` 下降但 `recallFilterReason=none`维度下的`pscore_avg` 正常 → 上游流量减少导致，非粗排自身问题
- 搜索场景排查时，用 `group_by=searchQuery` 看 top 搜索词的 count/pscore_avg 分布，定位哪些搜索词的粗排竞争力下降
