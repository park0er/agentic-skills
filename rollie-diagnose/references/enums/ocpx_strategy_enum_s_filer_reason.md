---
name: ocpx-strategy-enum-s-filer-reason
description: query_ocpx_strategy 的 sFilerReason 数字码 → 英文代码 + 说明映射。
---

# sFilerReason 枚举（OCPX 策略服务看板）

> 字段 `sFilerReason` 在后端响应中返回**数字码**，此文档提供**英文代码和说明**用于提升分析和报告的可读性。

| sFilerReason（数字码） | 英文代码 | 说明 |
|---:|---|---|
| `0` | `NONE` | 不过滤 |
| `1` | `NO_STRATEGY_AD_INFO` | noStrategyAdInfoFiltered |
| `2` | `MIN_DEEP_CVR` | minDeepCvrFiltered |
| `3` | `BUDGET_PACING` | budgetPacingFiltered |
| `5` | `UNKNOWN_ERROR` | 未知异常 |
| `6` | `MO_SCORE` | 模型没打分，且未走兜底逻辑 |
| `7` | `GUYU_GATEWAY_FILTER` | 上游发过来就 discard 了 |
| `8` | `PRICE_CHECK` | PriceCheckValidator 价格校验过滤 |
| `10` | `NO_TARGET_CPA` | emi 下发的目标成本不合法 |
| `11` | `MIN_DEEP_CVR_V2` | 次留双出价中，预估值小于目标成本 X 倍，过滤 |
| `12` | `USER_DUP_VIEW_APP` | 用户重复曝光 app，过滤 |
| `13` | `WRONG_PRE_VALUE` | 新版兜底策略异常值过滤 |

## ⚠️ 使用约定

- 查询结果中 `sFilerReason` 字段返回的是整数（如 `1`、`2`）
- **字典内数字码**：Agent分析及输出报告时引用表格里的英文代码和说明，不做语义改写。
- **字典外数字码**：可能是新过滤项，词典还未收录，只报数字码 + 量级 + 同比，**不要编造含义**
- 如某个数字码的过滤量同比异常增大，建议写入报告并标注"需 L2/L3 同学跟进数字码 XXXX"

