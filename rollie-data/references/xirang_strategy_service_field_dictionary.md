# 息壤策略服务看板字段字典

> 对应 server dashboard: `query_xirang_strategy_service`
>
> 息壤正式环境看板: `boardId=28`
>
- 默认指标: `count`
- 时间粒度: 支持 `300`(5分钟)、`3600`(小时)、`86400`(天)、`86402`(合计)

## 推荐查询

```json
{
  "dashboard": "query_xirang_strategy_service",
  "params": {
    "time": {
      "start_time": "2026-07-01T00:00:00+08:00",
      "end_time": "2026-07-02T00:00:00+08:00",
      "compare": false
    },
    "filters": {
      "campaign_id": "401190526"
    },
    "split": {
      "group_by": "tag_id",
      "top": 20,
      "sort_by": "count"
    },
    "measures": [
      "count",
      "avg_p_price_strategy",
      "avg_p_priceratio_strategy"
    ]
  }
}
```

## 维度


### 时间与流量

| 字段 | 中文名 | 说明 |
| --- | --- | --- |
| `dt` | 时间 | 默认选中 |
| `tag_id` | 广告位 |  |
| `media_type` | 媒体 |  |
| `env` | 集群 |  |
| `explayer22` | 实验层22层 |  |
| `explayer30` | 实验层30层 |  |
| `explayer31` | 实验层31层 |  |
| `explayer37` | 实验层37层 |  |
| `explayer39` | 实验层39层 |  |
| `explayer40` | 实验层40层 |  |
| `dsp_level2` | 二级DSP |  |
| `is_discard` | 是否无效 | `true`=无效/被过滤、`false`=有效/通过 |
| `data_source` | 数据来源 |  |

### 广告对象
| 字段 | 中文名 | 说明 |
| --- | --- | --- |
| `ad_id` | adId |  |
| `fresh_ad` | 是否新广告 | `true`=是新广告、`false`=非新广告、`unknown`=未知（息壤返回字符串） |
| `campaign_id` | 广告计划 |  |
| `app_id` | 应用ID |  |
| `customer_id` | 效果广告主账户 |  |
| `incremental_status` | 增量智投状态 |  |
| `fixed_price_source` | fixedPriceSource | 枚举值：`OTHER`、`PRICE_CAP`、`NO_CVR_FIX_BID`、`FIX_BID` |
| `price_ratio_source` | priceRatio类型 | 组合值（逗号拼接），基础因子：`BY_CONFIG`、`CUSTOMER_INCREMENTAL_DELIVERY`、`MINBOUND_QUANTILE`、`TAGIDECPM_QUANTILE`、`TYPE_16`、`TYPE_17`、`TYPE_20`、`QUALITY_SCORE`、`KEYWORD`、`INCREMENTAL_DELIVERY`、`unknown` |
| `price_origin_source` | priceOriginSource | 组合值（逗号拼接），基础因子：`FLOW`、`MPC`、`RISK`、`RISK_DEEP`、`TARGET_CPA`、`NO_CVR_DEFAULT`、`unknown` |
| `deep_target_conv_type` | 深层目标转化类型 |  |
| `billing_type` | 计费类型 |  |
| `sfilter_reason` | 过滤类型 | 息壤返回英文代码（非数字码），枚举映射见 `enums/ocpx_strategy_enum_s_filer_reason.md` |
| `target_conv_type` | 目标转化类型 |  |
| `key_action_type` | 关键行为类型 |  |
| `is_auto_optimize` | 是否自动优化 | `true`=是、`unknown`=未知 |
| `fresh_ad` | 是否新广告 | `true`=是新广告、`false`=非新广告、`unknown`=未知（息壤返回字符串） |

## 指标

> 默认指标：`count`

| 字段 | 中文名 | 说明 |
| --- | --- | --- |
| `count` | count | 请求*广告维度总记录数 |
| `avg_pcvrfix_strategy` | 平均pcvrFix |  |
| `avg_pltvfix_strategy` | 平均pLtvFix |  |
| `avg_pctr_strategy` | 平均pctr |  |
| `avg_pdeepltvfix_strategy` | 平均pdeepltvFix |  |
| `avg_bonus_strategy` | 平均补贴 |  |
| `avg_deep_pid_strategy` | 平均deepPid | 公式=总计deepPid/count，分母统一为count |
| `avg_price_weight_strategy` | 平均priceWeight |  |
| `avg_p_deep_price_strategy` | 平均pDeepPrice |  |
| `avg_deep_target_cpa_ratio_strategy` | 平均运营深层出价系数 |  |
| `avg_flow_bid_strategy` | 平均流控出价 |  |
| `avg_filter_cof_strategy` | 平均filterCof |  |
| `avg_deep_target_cpa_strategy` | 平均深层目标出价 |  |
| `avg_p_priceratio_strategy` | 平均pPriceRatio |  |
| `avg_combine_bid_strategy` | 平均combineBid |  |
| `avg_risk_bid_strategy` | 平均风控出价 |  |
| `avg_p_price_strategy` | 平均pPrice |  |
| `avg_target_cpa_ratio_strategy` | 平均运营出价系数 |  |
| `avg_p_shallowprice_strategy` | 平均pShallowPrice |  |
| `avg_targetcpa_strategy` | 平均目标出价 |  |
| `avg_is_customer_incremental_strategy` | 平均账户增量提价比例 |  |
| `avg_cold_boot_qvalue_strategy` | 平均冷启动QValue | 用户计算冷启动补贴 |
| `avg_cold_boot_avgecpm_strategy` | 平均冷启动AvgEcpm | 用户计算冷启动补贴 |
| `avg_cold_boot_pvalue_strategy` | 平均冷启动PValue | 用户计算冷启动补贴 |
| `avg_first_weight_x10w_strategy` | 平均firstWeightX10w |  |
| `avg_second_weight_x10w_strategy` | 平均secondWeightX10w |  |

## 诊断要点

### ⚠️ pPrice 波动幅度 >10% 必看

> **`avg_p_price_strategy` 由 `avg_pcvrfix_strategy` × `avg_risk_bid_strategy` × `avg_p_priceratio_strategy` 共同决定**因此 pPrice 波动时重点看哪个指标也在波动，帮助进一步定位原因。

1. `avg_pcvrfix_strategy`（平均pcvrFix）：与预估有关，如果下降可能与当前人群变化有关，若出现骤降，需要询问产研团队是否是模型问题
2. `avg_risk_bid_strategy`（平均风控出价）：该指标下降与三方面有关
   - 客户自身出价 `avg_targetcpa_strategy`（平均目标出价）降低
   - 广告超成本被调价系统打压
   - `incremental_status`（增量智投状态）账户增量模式发生变化，可以看下 `incremental_status` 的 count 分布是否有变化
3. `avg_p_priceratio_strategy`（平均pPriceRatio）：
   - 同比大幅下降 → 系统或运营配置了打压系数，导致竞争力下降
   - 同比大幅上升 → 系统或运营配置了提升系数，会提高竞争力，但可能导致超成本风控压价

