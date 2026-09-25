---
name: emi-diagnosis-field-dictionary
description: query_emi_diagnosis（广告下发）字段含义，供传参前确认使用
---

# 广告下发看板（query_emi_diagnosis）

漏斗位置：② 广告下发

用途：排查广告是否被拉黑、下发链路是否受到预算或控制评分压制。

## 支持的过滤参数

| 参数名 | 说明 |
|---|---|
| `adId` | 过滤到指定广告 |
| `campaignId` | 过滤到指定计划 |

**注意：此看板不支持 tagId 过滤。**
**注意：此看板不支持搜索词（query/keyword/search query）维度查询。**

## 维度（group_by 可选值）

| canonical_key | 中文含义 | 诊断用途 |
|---|---|---|
| `adId` | 广告 ID | 按广告下钻，找具体哪个广告异常 |
| `campaignId` | 计划 ID | 按计划下钻 |

## 指标（measures 可选值）

| canonical_key | 中文含义 | 诊断用途 |
|---|---|---|
| `count` | 记录条数 | 原始日志条数 |
| `delivery` | 下发数 | 广告进入投放流程的次数，核心指标 |
| `budgetDelivery` | 预算限制下发数 | 被预算控制拦截的次数，高则说明预算不足或消耗过快 |
| `controlScore` | 控制评分| 综合投放控制系数，值越高说明投放越被压制 |

## 典型查询示例

```json
{
  "time": {
    "start_time": "2026-03-01T00:00:00+08:00",
    "end_time": "2026-03-01T08:00:00+08:00",
    "compare": true
  },
  "filters": { "adId": "400016661" },
  "split": { "group_by": "adId" },
  "measures": ["count", "delivery", "budgetDelivery", "controlScore"]
}
```

## 诊断要点

- `delivery` 同比大幅下降 → 下发量明显减少，问题在此环节
- `budgetDelivery` 同比明显上升 → 预算消耗加速或预算不足导致投放受限，建议检查预算设置
- `controlScore` 同比明显升高（尤其 > 正常基线的 20%+）→ 系统对该广告的投放施加了更强的控制，可能触发了某种保护机制
- 三项指标均正常 → 此环节无异常，继续查下游召回
