---
name: xirang-budget-analysis-field-dictionary
description: query_xirang_budget_analysis（预算分析看板，息壤版）字段含义，供传参前确认使用
---

# 预算分析看板-息壤版（query_xirang_budget_analysis）

漏斗位置：预算分析

看板信息：

| 项 | 值 |
|---|---|
| query_name | `query_xirang_budget_analysis` |
| 中文名 | 预算分析看板 |
| host | `https://preview-ds.ad.xiaomi.com` |
| 调用方式 | 走 `/api/v1/query/dashboard`，与其他看板一致，使用 `dashboard_query.py` |

用途：排查预算消耗、达限状态，按应用/账户/行业/区域/代理维度分析。

## 参数命名

只认下划线 canonical 字段名，无 alias。传 `appId` 直接报错。

## filters 过滤维度（三层）

filters 使用与现有看板一致的 flat dict 格式，value 支持三种类型：

| value 类型 | 示例 | operator |
|---|---|---|
| `str` | `"app_id": "1"` | 固定 IN(0) |
| `list[str]` | `"app_id": ["1", "2"]` | 固定 IN(0) |
| `dict` | `"core_id": {"operator": "not_in", "values": ["0"]}` | 按 dict 内 operator |

第一/二层固定，第三层支持 in / not_in。
**每层最多选一个维度，三层至少选一个维度。**

| 层级 | 可选维度 | 规则 |
|---|---|---|
| 第一层 | `app_id` / `campaign_id` / `customer_id` | 三选一，固定 IN |
| 第二层 | `industry_level1` / `industry_level2` | 二选一，固定 IN |
| 第三层 | `effect_region` / `agent_id` / `core_id` | 三选一，in / not_in |

合法示例：
```json
// app_id + industry_level1 + core_id：每层选一个 ✅
"filters": {
  "app_id": ["1"],
  "industry_level1": ["2", "3"],
  "core_id": {"operator": "not_in", "values": ["0"]}
}
```

非法示例：
```json
// 第一层选了 app_id + campaign_id 两个 ❌
"filters": {
  "app_id": ["1"],
  "campaign_id": ["123"]
}
```

## split.stat_type 参数

| 值 | 含义 |
|---|---|
| `"total"` | 合计（默认） |
| `"daily_avg"` | 日均 |

## split.group_by 参数（控制返回数据）

只返回指定 bucket 的数据，减少上下文污染。**不传则默认按过滤精度自动选择**。

| 值 | 含义 |
|---|---|
| `"application"` | 只返回应用预算 |
| `"customer"` | 只返回账户预算 |
| `"campaign"` | 只返回计划预算 |

**默认值规则（不传 group_by 时）：**

| 过滤含 | 默认 group_by |
|---|---|
| `campaign_id` | `campaign` |
| `customer_id` | `customer` |
| 其余（app_id / industry / region / agent / core） | `application` |

**精度匹配规则（显式传 group_by 时需匹配）：**

| 过滤精度 | 允许的 group_by |
|---|---|
| 含 `campaign_id` | `campaign` |
| 含 `customer_id` | `customer`、`campaign` |
| 其余 | `application`、`customer` |

传了不允许的 group_by 直接报错。

传了不允许的 group_by 直接报错。


## reach_limit（服务端默认 unlimited）

| 值 | 含义 |
|---|---|
| `"unlimited"` | 不限（默认） |
| `"reached"` | 达限 |
| `"not_reached"` | 未达限 |

## time 参数

复用通用 TimeParams 格式，与其他看板一致。
对比时 `compare=true` + `comparison_start_time`。

## 输出列

`application` 表（按应用汇总）和 `customer` 表（按账户下钻）：

| 列 | 中文含义 |
|---|---|
| `dt` | 时间 |
| `app_info` | 应用ID-名称 |
| `customer_id` | 账户ID（仅 customer 表） |
| `customer_budget` | 账户预算和/账户预算 |
| `fee_effect` | 消耗 |
| `customer_actual_balance` | 当日最多可用余额 |
| `install_fee_effect_rate` | emi定向已安装广告消耗占比 |
| `consume_rate` | 达限率 |

## 典型查询示例

```json
{
  "dashboard": "query_xirang_budget_analysis",
  "params": {
    "time": {
      "start_time": "2026-06-01T00:00:00+08:00",
      "end_time": "2026-06-02T00:00:00+08:00",
      "compare": false
    },
    "filters": {
      "app_id": ["1"],
      "core_id": {"operator": "not_in", "values": ["0"]}
    },
    "split": {
      "stat_type": "total"
    }
  }
}
```

## 注意事项

- 不走独立路由，和其他看板一样走 `/api/v1/query/dashboard` + `dashboard_query.py`。
- 无 alias，字段名必须为下划线 canonical 形式。
- `split.stat_type` 可选，默认 `"total"`。
- `reach_limit` 服务端默认 `"unlimited"`，暂不暴露。
- 合法枚举值见 `references/xirang_budget_analysis_enum_values.json`。
