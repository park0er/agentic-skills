---
name: emi-opt-records-field-dictionary
description: strategy_operation_query category=emi_opt_records（广告主相关操作）字段含义，供 agent 解读返回数据使用
---

# 广告主相关操作（strategy_operation_query / emi_opt_records）

category 值：`"emi_opt_records"`

**返回类型：两个列表**

用途：查看广告主/运营人员对广告计划的手动操作记录，以及系统自动执行的状态流转记录，判断操作变更是否导致了消耗下降。

## 调用参数
>查询必须输入`start_time`和`end_time`，如果用户没有明确表达，默认查当天数据

| 参数 | 必填 | 说明 |
|---|---|---|
| `start_time` | 是 | ISO 8601 +08:00 格式，如 `"2026-06-01T00:00:00+08:00"` |
| `end_time` | 是 | ISO 8601 +08:00 格式，如 `"2026-06-08T00:00:00+08:00"` |
| 六选一维度 key | 是 | `adId` / `adGroupId` / `campaignId` / `accountId` / `appId` / `adReportId` |
| `category` | 是 | 固定值 `"emi_opt_records"` |


## 字段说明

### emiOperationRecords（广告主操作记录）

记录广告主通过投放平台（EMI）执行的操作，包括修改预算、修改出价等。每条记录有 8 个字段：

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `operationTime` | 操作时间 | 格式 `"YYYY-MM-DD HH:MM:SS"`。**按时间排序可重建操作序列** |
| `operationType` | 操作类型 | 中文描述，常见值见下文枚举表 |
| `operationObject` | 操作对象 | 如 `"广告计划"`、`"广告"` |
| `objectId` | 对象 ID | 被操作的计划/广告 ID |
| `oldValue` | 旧值 | 多行文本，包含字段名和原值 |
| `newValue` | 新值 | 多行文本，包含字段名和新值 |
| `negative` | 是否负向操作 | `true` / `false`。**true = 可能导致消耗下降的操作** |
| `negativeOperation` | 负向操作类型 | 如 `"计划降价"`。`negative=false` 时为空 |

### systemTransitionRecords（系统状态流转记录）

记录系统自动触发的状态变更，如预算达限、预算恢复等。每条记录有 7 个字段：

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `operationTime` | 操作时间 | 格式 `"YYYY-MM-DD HH:MM:SS"` |
| `operationType` | 状态流转类型 | 如 `"修改计划预算状态"` |
| `operationObject` | 操作对象 | 如 `"广告计划"`、`"广告"` |
| `objectId` | 对象 ID | 被操作的计划/广告 ID |
| `oldValue` | 旧状态 | 如 `"推广计划预算有效"` |
| `newValue` | 新状态 | 如 `"推广计划预算达限"` |
| `negative` | 是否负向 | `true` / `false`。**true = 可能导致消耗下降的操作** |

## operationType 常见枚举

| operationType | 类别 | 说明 |
|---|---|---|
| `修改计划预算` | emiOperationRecords | 广告主修改了计划日预算。**上升 = 扩量，下降 = 可能的掉量原因** |
| `广告计划转化出价变更` | emiOperationRecords | 修改了转化出价。**上升 = 扩量，下降 = 可能的影响竞争力** |
| `修改计划预算状态` | systemTransitionRecords | 系统自动触发。`预算达限 → 预算有效`（恢复）/ `预算有效 → 预算达限`（限制） |

## 典型查询示例

```json
{
  "start_time": "2026-06-01T00:00:00+08:00",
  "end_time": "2026-06-08T23:59:59+08:00",
  "adId": "434918031",
  "category": "emi_opt_records"
}
```


## 使用要点

- **首要关注的信号**：`negative=true` 的记录。遍历所有 `emiOperationRecords` 和 `systemTransitionRecords`，筛选 `negative=true` 的条目
- **降价导致掉量**：`operationType="广告计划转化出价变更"` 且 `negative=true` → 出价降低导致竞价竞争力下降，eCPM 降低 → 消耗减少
- **降预算导致掉量**：`operationType="修改计划预算"` 且预算值下降 → 预算收缩导致可投放量被限制，广告更容易提前达线影响消耗
- **预算达限导致掉量**：`operationType="修改计划预算状态"` 且 `newValue` 含 `"达限"` → 预算耗尽后系统自动暂停，这是系统级负向信号
- **时间线分析**：按 `operationTime` 排序，找到距掉量时间点最近的操作，判断因果关系
