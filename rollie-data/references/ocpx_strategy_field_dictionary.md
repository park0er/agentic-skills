---
name: ocpx-strategy-field-dictionary
description: query_ocpx_strategy（OCPX策略）字段含义，供传参前确认使用
---

# OCPX 策略看板（query_ocpx_strategy）

漏斗位置：⑦ OCPX 策略

用途：排查 OCPX 策略层面的拦截原因和调价行为，是精排出现 `OCPX_STRATEGY_FILTER` 后的必查项。

## 支持的过滤参数

| 参数名 | 说明 |
|---|---|
| `adId` | 过滤到指定广告 |
| `campaignId` | 过滤到指定计划 |
| `tagId` | 过滤到指定广告位 |

## 维度（group_by 可选值）

| canonical_key | 后端字段名 | 中文含义 | 诊断用途 |
|---|---|---|---|
| `sFilerReason` | `sFilerReason` | OCPX 策略二级过滤原因（数字码） | **精排发现 OCPX_STRATEGY_FILTER 时必须用此 group_by 二级下钻**。⚠️ **用法及真实含义映射必须先读取** `./enums/ocpx_strategy_enum_s_filer_reason.md` |
| `adId` | `adId` | 广告 ID | 按广告下钻 |
| `campaignId` | `campaignId` | 计划 ID | 按计划下钻 |
| `tagId` | `tagId` | 广告位 ID | 按广告位下钻 |
| `convType` | `convType` | 目标转化类型 | 按目标转化类型下钻 |
| `deepconvType` | `deepconvType` | 深层目标转化类型 | 按深层目标转化类型下钻 |
| `incrementalStatus` | `incrementalStatus` | 账户增量模式 | 按账户增量模式下钻，枚举值：0=未开启，1=增量模式，2=日常模式 |

**注意：此看板不支持搜索词（query/keyword/search query）维度查询。**

## 指标（measures 可选值）

| canonical_key | 后端字段名 | 中文含义 | 诊断用途 |
|---|---|---|---|
| `count` | `count` | 进入 OCPX 策略的总量 | 基数 |
| `price` | `price` / `total` | 调价侧最终price | price水平是否合理，同比明显下降说明出价策略变化 |
| `priceRatio` | `priceRatio` / `total` | 出价系数 | `> 1` 表示系统或运营提高了出价系数，`< 1` 表示系统或运营压低了出价系数 |
| `ctr` | `ctr` / `total` | 预估点击率 | 模型对该段广告的点击预估水平 |
| `cvr` | `cvr` / `total` | 原始浅层预估转化率 | 模型对该段广告的浅层转化预估水平 |
| `cvrFixed` | `cvrFixed` / `total` | 校准后浅层预估转化率 | 经校准后的浅层转化预估水平，**系统最终使用该指标**，`cvrFixed` / `cvr` >1 表示提高预估校准，<1 表示降低预估校准 |
| `deepCvr` | `deepCvr` / `total` | 预估深层转化率 | 深层转化目标的模型预估水平 |
| `deepCvrFixed` | `deepCvrFixed` / `total` | 校准后预估深层转化率 | 经校准后的深层转化预估水平，**系统最终使用该指标**，`deepCvrFixed` / `deepCvr` >1 表示提高预估校准，<1 表示降低预估校准 |
| `riskBid` | `riskBid` / `total` | 风控出价 | 调价系统输出的风控出价 |
| `targetCpa` | `targetCpa` / `total` | 广告主浅层目标出价 | 广告主设置的目标成本 |
| `targetCpaRatio` | `targetCpaRatio` / `total` | 广告主浅层目标出价系数 | `> 1` 表示运营提高了浅层目标出价系数，`< 1` 表示运营压低了浅层目标出价系数 |
| `deepTargetCpa` | `deepTargetCpa` / `total` | 广告主深层目标出价 | 深层转化的目标成本 |
| `deepTargetCpaRatio` | `deepTargetCpaRatio` / `total` | 广告主深层目标出价系数 | `> 1` 表示运营提高了深层目标出价系数，`< 1` 表示运营压低了深层目标出价系数 |

## 典型查询示例

```json
{
  "time": {
    "start_time": "2026-03-02T00:00:00+08:00",
    "end_time": "2026-03-02T08:00:00+08:00",
    "compare": true,
    "comparison_start_time": "2026-03-01T00:00:00+08:00",
    "comparison_end_time": "2026-03-01T23:59:59+08:00"
  },
  "filters": { "adId": "400016661", "tagId": "1.11.t.1" },
  "measures": ["count", "price", "priceRatio", "targetCpa"]
}
```

二级下钻（精排发现 OCPX_STRATEGY_FILTER 异常时）：

```json
{
  "time": {
    "start_time": "2026-03-02T00:00:00+08:00",
    "end_time": "2026-03-02T08:00:00+08:00",
    "compare": true,
    "comparison_start_time": "2026-03-01T00:00:00+08:00",
    "comparison_end_time": "2026-03-01T23:59:59+08:00"
  },
  "filters": { "adId": "400016661", "tagId": "1.11.t.1" },
  "split": { "group_by": "sFilerReason" },
  "measures": ["count", "price", "priceRatio", "targetCpa"]
}
```
## 诊断要点

### ⚠️price波动幅度>10%必看

> **`price=cvrFixed x riskBid x priceRatio`** ,因此price波动时重点看哪个指标也在波动，帮助进一步定位原因

1. `cvrFixed`：与预估有关，如果下降可能与当前人群变化有关，若出现骤降，需要询问产研团队是否是模型问题
2. `riskBid`:该指标下降与三方面有关 1）客户自身出价`targetCpa`降低；2）广告超成本被调价系统打压；3）`incrementalStatus`账户增量模式发生变化，可以看下`incrementalStatus`count数是否有变化
3. `priceRatio`：
   - `priceRatio` 同比大幅下降（压低出价系数）→ 系统或运营配置了打压系数，导致竞争力下降
   - `priceRatio` 同比大幅上升（压低出价系数）→ 系统或运营配置了提升系数，会提高竞争力，但可能导致超成本风控压价
    