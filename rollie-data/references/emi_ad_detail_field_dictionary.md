---
name: emi-ad-detail-field-dictionary
description: strategy_operation_query category=emi_ad_detail（广告信息）字段含义，供 agent 解读返回数据使用
---

# 广告信息（strategy_operation_query / emi_ad_detail）

category 值：`"emi_ad_detail"`

**返回类型：dict，单条广告详情**（非列表）

用途：查看广告投放状态、出价、预算、定向配置等基础信息，确认广告本身是否被修改、暂停或配置异常。

## ⚠️ 重要约束

- **此 category 仅支持 `adId` 维度**，传入其他维度 key（campaignId/accountId 等）会直接报错
- 返回是 dict，不是 list，没有 group_by / measures 概念
- 查询必须输入`start_time`和`end_time`，如果用户没有明确表达，默认查当天数据

## 调用参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `start_time` | 是 | ISO 8601 +08:00 格式，如 `"2026-06-01T00:00:00+08:00"` |
| `end_time` | 是 | ISO 8601 +08:00 格式，如 `"2026-06-08T00:00:00+08:00"` |
| `adId` | 是 | 广告 ID，**此 category 仅支持 adId** |
| `category` | 是 | 固定值 `"emi_ad_detail"` |

## 属性字段（emiAdDimensionDetail）

### 广告身份

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `adId` | 广告 ID | 查询的广告 ID |
| `adName` | 广告名称 | 广告主自定义的广告名 |
| `campaignId` | 计划 ID | 所属推广计划 ID |
| `campaignName` | 计划名称 | 所属推广计划名称 |
| `adReportId` | adReportId | 所属的 adReportId |
| `source` | 创建方式 | 如 `"ICON扩展创建"`、`"API创建"` 等 |

### 投放状态

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `adDeliveryStatus` | 投放状态 | 如 `"投放中"`、`"暂停"`。**掉量诊断时首要检查**：若为非投放中状态说明广告已被暂停 |
| `campaignDeliveryStatus` | 计划投放状态 | 如 `"投放中"`、`"暂停"`。计划暂停会导致其下所有广告停止投放 |
| `creativeUnDeliveryReason` | 广告未投放原因 | 列表，如果非空说明广告层面有未投放的问题 |
| `campaignUnDeliveryReason` | 计划未投放原因 | 列表，如果非空说明计划层面有未投放的问题 |

### 出价类型

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `billingTypeAndBid` | 出价类型 | 计费模式为 cpc/cpd/ocpd/ocpc 之一，包含出价金额。如 `"oCPD:16.32元/下载"` |

### 转化目标

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `convTypeAndPrice` | 浅层转化目标及出价 | 如 `"10018-自定义关键行为：16.32元 关键行为名称：APP使用时长 阈值：900 单位：second"` |
| `deepConvTypeAndPrice` | 深层转化目标及出价 | **部分广告可能无此字段**。如 `"3-自定义留存：38%"` |

### 智投出价

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `bid` | 智投最大出价-浅层 | 实际生效的浅层出价。如 `"16.32元"`。当开启智投时，该字段有值 |
| `deepBid` | 智投最大出价-深层 | 实际生效的深层出价。如 `"38.00%"` 或 `"0.00元"`。当开启智投时，该字段有值 |

### 应用信息

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `appId` | 应用 ID | 推广应用的唯一标识 |
| `appName` | 应用名称 | 如 `"抖音极速版(com.ss.android.ugc.aweme.lite)"`，格式为 `"{appName}({packageName})"`，已合并包名 |
| `packageName` | 应用包名 | Android package name，如 `"com.ss.android.ugc.aweme.lite"`。 |

### 账户信息

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `customerId` | 账户 ID | 广告主账户 ID |
| `customerName` | 账户名称 | 广告主公司名称 |
| `customerDayBudgetAndRemain` | 账户日预算与余额 | 如 `"140000.0元/天 (余额1190190.81元)"`。**余额不足或预算达限**会导致停止投放 |

### 流量定向

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `platformDirection` | 流量定向 | 如 `"流量范围：商店\n流量优选：开启中\n版位：商店推荐富媒体"`，多行文本 |
| `userDirection` | 用户定向 | 如 `"自定义人群：不限"`，描述人群定向规则 |
| `wordDirection` | 词定向 | 关键词定向配置，通常为空 |

### 素材与版位

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `materialUrl` | 素材 | 视频或图片素材 URL |
| `materialType` | 素材规格（MT） | 如 `"11-应用信息"` |
| `displayType` | 版位（DT） | 如 `"34-富媒体广告"` |
| `materialTrafficRange` | 适用流量 | 如 `"全媒体范围"` |
| `placementTypeName` | 广告类型（PT） | 如 `"0-非PT广告"` |

### 流量与智投

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `trafficMode` | 是否流量优选广告 | 如 `"开启中"` |
| `autoOptimize` | 自动优化广告 | 如 `"1-开启"`，表示系统是否在做自动优化调整 |
| `incrementalDailyStatus` | 是否智投 | 如 `"0-未生效"`，包含智投状态展示信息 |
| `incrementalEffectivePeriod` | 智投周期 | **仅智投广告有此字段，非智投广告不返回**。格式如 `"2025-12-01~长期"` |

### 其他

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `rtaToken` | RTA Token | **部分广告可能无此字段**。RTA策略标识，用于实时竞价干预 |


## 典型查询示例

```json
{
  "start_time": "2026-06-01T00:00:00+08:00",
  "end_time": "2026-06-08T23:59:59+08:00",
  "adId": "434918031",
  "category": "emi_ad_detail"
}
```


## 使用要点

- **检查投放状态**：`adDeliveryStatus` 和 `campaignDeliveryStatus` 是否为 `"投放中"`。若不是 → 广告/计划已被暂停，会导致广告无法消耗
- **检查出价**：`bid`（智投最大出价-浅层）/ `deepBid`（智投最大出价-深层）是否存在，若智投出价低于目标出价，可能导致竞价竞争力下降，影响消耗。反之会帮助提高消耗
- **检查定向**：`platformDirection` 和 `userDirection` 如果存在定向，会影响广告的可投放流量范围。定向较窄会导致可投放流量减少
- **检查智投**：如果广告开启了智投（`incrementalDailyStatus` 不为"0-未生效"），关注 `incrementalEffectivePeriod` 智投周期是否到期
- **检查 RTA**：如果 `rtaToken` 存在，RTA 策略也可能影响参竞率
