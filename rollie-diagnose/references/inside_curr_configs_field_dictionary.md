---
name: inside-curr-configs-field-dictionary
description: strategy_operation_query category=inside_curr_configs（内部配置信息）字段含义，供 agent 解读返回数据使用
---

# 内部配置信息（strategy_operation_query / inside_curr_configs）

category 值：`"inside_curr_configs"`

**返回类型：列表，含递归 children**

用途：查看平台侧对该广告/计划/账户/应用施加的策略配置——包括拉黑配置、出价调整、流量控制等内部干预手段。排查平台策略是否抑制了广告投放。

## 调用参数
>查询必须输入`start_time`和`end_time`，如果用户没有明确表达，默认查当天数据

| 参数 | 必填 | 说明 |
|---|---|---|
| `start_time` | 是 | ISO 8601 +08:00 格式，如 `"2026-06-01T00:00:00+08:00"` |
| `end_time` | 是 | ISO 8601 +08:00 格式，如 `"2026-06-08T00:00:00+08:00"` |
| 六选一维度 key | 是 | `adId` / `adGroupId` / `campaignId` / `accountId` / `appId` / `adReportId` |
| `category` | 是 | 固定值 `"inside_curr_configs"` |


## 字段说明（insideCurrentConfigs）

每条记录有 14 个顶层字段，其中 `children` 是递归子配置数组，子项结构与顶层字段一致：

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `operateTime` | 配置生效时间 | 格式 `"YYYY-MM-DD HH:MM:SS"` |
| `platform` | 操作平台 | 如 `"新运营工具平台"`、`"PS策略平台"` |
| `operateDimId` | 配置维度 ID | 数字，枚举映射见下方"维度枚举"表 |
| `operateDim` | 配置维度 | 中文，如 `"账户"`、`"应用"`、`"广告计划"` |
| `operateValue` | 配置对象值 | 对应的账户/应用/计划 ID |
| `strategy` | 策略标识 | 策略唯一名，如 `"拉黑配置-abram_v2"`、`"调整出价配置-ssp_ocpx_adjust_price-1511472"` |
| `strategyCn` | 策略中文名 | 如 `"拉黑配置"`、`"调整出价配置"`。**诊断时主要关注此项** |
| `strategyKey` | 策略 Key | 如 `"abram_v2"`、`"ssp_ocpx_adjust_price-1511472"` |
| `newValue` | 配置详情 | **JSON string，需二次解析**。包含该策略的具体参数，如拉黑的实验 ID 列表、出价调整系数等 |
| `status` | 生效状态 | `"生效"` / `"失效"` / `"未知"`。诊断时重点关注"生效"状态的配置才是真正在起作用的 |
| `children` | 子配置列表 | **递归子配置数组**，每个子项的字段结构与本表顶层完全一致。一个顶层策略可能包含多个子策略（如拉黑配置下有多个子规则） |
| `key` | 唯一标识 | 格式为 `"平台#维度#ID#策略标识"`，如 `"新运营工具平台#账户#1511472#调整出价配置-..."` |

## 维度枚举（operateDimId ↔ operateDim）

| operateDimId | operateDim | operateValue 含义 |
|---|---|---|
| 1 | 广告 | 广告 ID |
| 2 | 广告组 | 广告组 ID |
| 3 | 广告计划 | 计划 ID（campaignId） |
| 4 | 账户 | 客户账户 ID（customerId） |
| 5 | 应用 | 应用 ID（appId） |

## strategyCn 常见枚举

| strategyCn | 说明 | 诊断关联 |
|---|---|---|
| `拉黑配置` | 对某维度下的广告/应用执行拉黑，阻止其参与竞价。子策略 `strategyKey` 如 `abram_v2` 表示特定拉黑规则 | **如果存在且 status 不是"禁用" → 投放被直接阻断，这是最强干预信号** |
| `调整出价配置` | 平台侧对出价做了干预调整（上调或下调）。`newValue` 中的 `configType` 字段表示调整类型 | 如果出价被下调 → 竞价竞争力下降 |
| `流量控制` | 对流量做定向控制 | 可能导致可触达流量范围缩小 |

## ⚠️ newValue 的二次解析

`newValue` 是 JSON string，不是 JSON object。agent 读取时需先 `json.loads()` 才能访问内部字段。内部常见字段：

| newValue 内部字段 | 含义 |
|---|---|
| `id` | 配置记录 ID |
| `customerId` / `campaignId` / `appId` / `adId` | 配置绑定的维度 ID |
| `configType` | 配置类型（1/2/3...） |
| `convType` / `deepConvType` | 关联的转化类型 |
| `keyType` | key 类型，3 表示按账户维度 |
| `queryKey` | 查询 key |

## 典型查询示例

```json
{
  "start_time": "2026-06-01T00:00:00+08:00",
  "end_time": "2026-06-08T23:59:59+08:00",
  "adId": "411787296",
  "category": "inside_curr_configs"
}
```


## 使用要点

- **先扫 `strategyCn` 找关键词**：按 `strategyCn` 分组，列出该广告关联的所有策略类型。出现"拉黑配置"且非禁用状态 → **这是最高优先级的异常信号**
- **看时间点**：按 `operateTime` 排序，找出掉量时间点前后新上或变更的配置
- **展开 children**：顶层记录的 `children` 可能包含更细粒度的子规则，需要递归遍历
- **二次解析 newValue**：先 `json.loads(newValue)` 再解读内部字段。如果解析后仍不清楚含义，不要自行猜测，给用户呈现原始内容
