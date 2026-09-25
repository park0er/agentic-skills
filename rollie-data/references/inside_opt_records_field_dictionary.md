---
name: inside-opt-records-field-dictionary
description: strategy_operation_query category=inside_opt_records（配置记录相关）字段含义，供 agent 解读返回数据使用
---

# 配置记录相关（strategy_operation_query / inside_opt_records）

category 值：`"inside_opt_records"`

**返回类型：两个列表**

用途：查看 DMP 人群包使用记录（哪些人群包曾在历史上被应用到这个广告/计划上），以及内部运营工具的配置变更历史（谁在什么时候改了什么配置）。

## 调用参数
>查询必须输入`start_time`和`end_time`，如果用户没有明确表达，默认查当天数据

| 参数 | 必填 | 说明 |
|---|---|---|
| `start_time` | 是 | ISO 8601 +08:00 格式，如 `"2026-06-01T00:00:00+08:00"` |
| `end_time` | 是 | ISO 8601 +08:00 格式，如 `"2026-06-08T23:59:59+08:00"` |
| 六选一维度 key | 是 | `adId` / `adGroupId` / `campaignId` / `accountId` / `appId` / `adReportId` |
| `category` | 是 | 固定值 `"inside_opt_records"` |


## 字段说明

### dmpTagRecords（DMP 人群包使用记录）

记录该广告历史上绑定过的 DMP 人群包。DMP 人群包用于广告定向（圈定目标人群或排除特定人群），**人群包失效会导致定向范围异常变化**。每条记录有 8 个字段：

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `operateTime` | 操作时间 | 格式 `"YYYY-MM-DD HH:MM:SS"` |
| `platform` | 操作平台 | 如 `"PS策略平台"` |
| `dmpTagId` | 人群包 ID | DMP 人群包唯一标识 |
| `dmpTagName` | 人群包名称 | 如 `"抖音极速版IP+设备屏蔽.448641"`、`"抖音月活人群.112296"`。命名格式为 `"{描述}.{编号}"` |
| `isValid` | 是否有效 | `"生效"` / `"失效"`。**失效 = 人群包已过期** |
| `startTime` | 生效开始时间 | 格式 `"YYYY-MM-DD HH:MM:SS"` |
| `endTime` | 生效结束时间 | 格式 `"YYYY-MM-DD HH:MM:SS"`。过期后失效 |
| `didDeviceCount` | 设备数 | 人群包覆盖的设备数量。`-1` 表示未知。设备数越大说明人群包覆盖面越广，失效影响也越大 |

### insideOperationRecords（内部操作变更记录）

记录内部运营人员通过运营工具平台对该广告相关配置的修改历史——谁在什么时候改了什么。每条记录有 12 个字段：

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `operateTime` | 操作时间 | 格式 `"YYYY-MM-DD HH:MM:SS"` |
| `operator` | 操作人 | **操作人员的用户名**，如 `"geyang1"`。用于追溯操作责任人和沟通确认 |
| `operateType` | 操作类型 | 如 `"修改"`、`"新增"`、`"删除"` |
| `platform` | 操作平台 | 如 `"新运营工具平台"` |
| `operateDim` | 操作维度 | 如 `"账户"`、`"应用"`、`"广告计划"` |
| `operateValue` | 操作对象值 | 对应的账户/应用/计划 ID |
| `strategy` | 策略标识 | 被修改的策略唯一名 |
| `strategyCn` | 策略中文名 | 如 `"调整出价配置"` |
| `strategyKey` | 策略 Key | 如 `"ssp_ocpx_adjust_price-1462082"` |
| `oldValue` | 修改前的值 | **JSON string，需二次解析**。被修改字段的旧值 |
| `newValue` | 修改后的值 | **JSON string，需二次解析**。被修改字段的新值 |


## ⚠️ oldValue / newValue 的二次解析

`oldValue` 和 `newValue` 是 JSON string，需要先 `json.loads()` 才能访问内部字段。内部结构是与 `inside_curr_configs` 中 `newValue` 格式一致的 key-value 数组，包含 `id`、`configType`、相关维度 ID 等字段。对比 oldValue 和 newValue 中同名 key 的值变化即可定位具体修改了什么。

## 典型查询示例

```json
{
  "start_time": "2026-06-01T00:00:00+08:00",
  "end_time": "2026-06-08T23:59:59+08:00",
  "adId": "418883432",
  "category": "inside_opt_records"
}
```


## 使用要点

### DMP 人群包

- **核心信号**：检查 `isValid="失效"` 的人群包。如果大量人群包在掉量时间点附近过期 → 广告定向范围缩小，可触达用户减少
- **关注大覆盖面人群包**：`didDeviceCount` 较大（百万级）的人群包失效，影响远大于小包
- **人群包类型解读**：名称中含"屏蔽"字样的是排除包（用于过滤不想投放的用户），屏蔽包失效反而可能导致投放范围扩大（质量可能下降），而定向包（如"月活人群"）失效则会导致可投放人群缩小
- **注意**：`dmpTagRecords` 返回的是该广告历史上绑定过的所有人群包，不是当前生效的。过期很久的人群包（如 2019-2022）属于历史记录，与当前掉量无关

### 内部操作记录

- **按时间筛选**：筛选掉量时间点前后几天的变更记录
- **按操作人筛选**：如果多条变更集中在同一个人 → 可能是人工干预导致的。可以找操作人确认意图
- **对比 oldValue 和 newValue**：先 `json.loads()` 再逐个 key 对比，找出实际变化的字段。例如 `configType` 从 3 变为 1 可能意味着出价策略调整
- **与 `inside_curr_configs` 配合使用**：`inside_curr_configs` 看当前配置状态，`inside_opt_records` 看配置变更历史。一个定位"现在是什么样的"，一个定位"什么时候变的、谁变的"
