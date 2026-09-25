---
name: xirang-rta-diagnosis-field-dictionary
description: query_xirang_rta_diagnosis（RTA多维分析）字段含义，供传参前确认使用
---

# RTA多维分析看板-息壤版（query_xirang_rta_diagnosis）

漏斗位置：**RTA 链路**（系统发起 RTA 请求 → 外发广告主 → 广告主返回策略及出价系数 → 系统读取及缓存写入）

用途：排查 RTA 请求量、通过率、超时、缓存命中、出价系数等问题。一般搭配 `client_name`或 `token_name` 使用，常用指标为请求数、通过率、超时率、出价系数均值等。

---

## 一、维度字段

| 字段名 | 中文名 | 维度说明 | 枚举值说明 |
|---|---|---|---|
| `dt` | 时间, 时间维度 | 需配合 `time_granularity` 使用；见下方时间粒度编码表 | — |
| `client_name` | Client, 客户 | RTA视角的客户 | `bytedance`（字节跳动）、`dewu`（得物）等。 |
| `client_msg` | Client Msg, 客户响应信息 | client维度的响应信息，表示外发广告主后的返回状态 | `success`=外发成功、`not send`=没有外发广告主、`rate limit`=限流拦截、`async request`=异步调用、`drop by ratio`=按比例丢弃流量、`short circuit`=熔断限流、`drop by stress`=压测流量丢弃、`no valid userInfo`=无效设备号、`CLIENT INNER ERROR`=客户内部异常、`DataSyntaxException`=返回值核心字段为空、`JsonSyntaxException`=返回值非协议规范Json结构 |
| `ret_code` | Ret code, 状态码 | 外发广告主后返回的状态码汇总 | `0`=外发成功、`1`=客户侧异常、`2`=IO或内部异常、`4`=内部流量策略、`5`=网络超时异常 |
| `req_type` | 请求方式 | 同步请求或异步请求 | `0`=未知、`1`=同步请求、`2`=异步请求 |
| `token_name` | Token, RTA策略标识 | RTA 策略标识，每个 token 对应一条策略配置 | `dewu_xm_laxin`（得物小米拉新）、`dewu_xm_laxin2`（得物小米拉新2）等。 |
| `token_msg` | Token Msg, Token响应信息 | token维度的响应信息，表示 token 层面对请求的处理结果 | `drop`=流量丢弃、`success`=外发成功、`unknown`=未知、`hit cache`=命中有效缓存、`risk intercept`=风控拦截、`error hit cache`=请求异常命中缓存、`error no hit cache`=请求异常未命中缓存 |
| `did_type` | 外发设备类型 | 外发客户设备类型，优先级 OAID > IMEI > IPUA | `OAID`、`IMEI`、`IPUA` |
| `media_type` | 媒体, 媒体类型 | 媒体 | 完整清单见 `./enums/media_type_cn_mapping.md` |
| `tag_id` | 广告位, 广告位ID | 广告位 | `1.1.1.1`=小米视频-灵活广告位。完整清单见 `./enums/xirang_ad_effect_enum_tag_id.md` |
| `env` | 集群, 服务集群 | RTA 服务所在的集群 | `C3`=C3集群、`AKSRV`=AKSRV集群、`C4`=C4集群 |
| `rta_host` | 机器名, RTA机器 | RTA 服务的具体机器名，用于定位单机问题 | `c3-miui-ad-rta01.bj-1` 等 |
| `req_source` | 请求来源 | 请求来源，区分广告请求与自然量请求 | `AD`=广告请求、`NATURAL`=自然量请求 |
| `traffic_type` | 流量类型 | 标识请求是否为压测流量 | `prd`=生产流量、`stress`=压测流量（排查时通常排除压测数据） |



---

## 二、指标字段


| 字段名 | 中文名 | 公式说明 |
|---|---|---|
| `de_rta_req_token` | 引擎_RTA_请求数 | 引擎请求 RTA 的请求数 |
| `de_rta_ac_token` | 引擎_RTA_通过数 | 引擎请求 RTA 的通过数 |
| `de_rta_ac_rate_token` | 引擎_RTA_通过率 | `de_rta_ac_token / de_rta_req_token * 100`。引擎请求 RTA 的通过率 |
| `de_rta_boost_cnt` | 出价系数填充数 | 引擎请求 RTA 出价系数填充数 |
| `de_rta_boost_rate` | 出价系数填充率 | `de_rta_boost_cnt / de_rta_req_token * 100`。引擎请求 RTA 出价系数填充率 |
| `avg_de_rta_boost` | 出价系数均值 | `total_de_rta_boost / de_rta_boost_cnt`。引擎请求 RTA 出价系数均值 |
| `avg_de_rta_org_boost` | 原始出价系数均值 | `total_de_rta_org_boost / de_rta_boost_cnt`。引擎请求 RTA 原始出价系数均值 |
| `de_rta_exp_cnt` | 实验ID填充数 | 引擎请求 RTA 实验ID填充数 |
| `de_rta_exp_rate` | 实验ID填充率 | `de_rta_exp_cnt / de_rta_req_token * 100`。引擎请求 RTA 实验ID填充率 |
| `de_rta_hit_cache_rate` | 缓存命中率 | `de_rta_hit_cache_cnt / de_rta_req_token * 100`。引擎请求 RTA 缓存命中率 |
| `de_rta_err_cache_rate` | 异常缓存兜底命中率 | `de_rta_err_cache_cnt / de_rta_req_token * 100`。引擎请求 RTA 异常缓存兜底命中率 |
| `avg_de_rta_cache_time` | 缓存时长均值 | `total_de_rta_cache_time / de_rta_cache_time_cnt`。引擎请求 RTA 缓存时长均值 |
| `rta_cus_req_client` | RTA_Client_请求数 | RTA 请求客户 client 请求数。⚠️ 仅可搭配 client维使用 |
| `rta_cus_timeout_cnt_client` | RTA_Client_超时数 | RTA 请求客户 client 超时数。⚠️ 仅可搭配 client维度使用 |
| `rta_cus_timeout_rate_client` | Client真实超时率 | `rta_cus_timeout_cnt_client / rta_cus_req_client * 100`。RTA 请求客户 client 超时率。⚠️ 仅可搭配 client维度使用 |
| `rta_cus_req_token` | RTA_Token_请求数 | RTA 请求客户的请求数。 |
| `rta_cus_ac_token` | RTA_Token_通过数 | RTA 请求客户的通过数。  |
| `rta_cus_ac_rate_token` | RTA_Token_通过率 | `rta_cus_ac_token / rta_cus_req_token * 100`。RTA 请求客户的通过率。 |
| `rta_cus_timeout_cnt_token` | RTA_Token_超时数 | RTA 请求客户的超时数。 |
| `rta_cus_timeout_rate_token` | RTA_Token_超时率 | `rta_cus_timeout_cnt_token / rta_cus_req_token * 100`。RTA 请求客户的超时率。 |
| `avg_rta_cus_cache_time` | Api缓存时长均值 | `total_rta_cus_cache_time / rta_cus_cache_time_cnt`。RTA 请求客户缓存时长均值。 |





---

## 时间粒度编码（仅 `dt` 字段）

> `time_granularity` **必须与 `split.group_by = "dt"` 同时使用**，否则无效。

| 编码 | 含义 | dt 字段格式 | 建议时间范围 |
|---:|---|---|---|
| `60` | 按分钟 | `"YYYY-MM-DD HH:MM"` | ≤ 1小时 |
| `300` | 按5分钟 | `"YYYY-MM-DD HH:MM"` | ≤ 1天 |
| `3600` | 按小时 | `"YYYY-MM-DD HH:MM"` | ≤ 3天 |
| `86400` | 按天 | `"YYYY-MM-DD"` | ≤ 14天 |
| `86402` | 合计（默认） | 无，返回1行 | 任意 |

不传 `time_granularity` 时默认 `86402`（合计，整段1行），等价于不按时间分组，无法看趋势。`minTableGranularity` 为 60 秒，不应使用更细粒度查询。

---

## 三、典型查询示例

筛选指定 Token + 广告位，看当天按小时的引擎请求数、通过率、超时率、出价系数变化（带昨日对比）：

```json
{
  "time": {
    "start_time": "2026-06-04T00:00:00+08:00",
    "end_time": "2026-06-04T23:59:59+08:00",
    "compare": true,
    "comparison_start_time": "2026-06-03T00:00:00+08:00",
    "comparison_end_time": "2026-06-03T23:59:59+08:00"
  },
  "filters": { "tokenName": "dewu_xm_laxin", "tagId": "1.1.1.1" },
  "split": { "group_by": "dt", "time_granularity": 3600, "top": 24, "sort_by": "de_rta_req_token" },
  "measures": ["de_rta_req_token", "de_rta_ac_rate_token", "rta_cus_timeout_rate_token", "de_rta_boost_rate", "avg_de_rta_boost"]
}
```

---

## 使用注意事项

1. **核心下钻组合**：`token_name` × `tag_id` 定位是哪个RTA策略在哪个广告位下的数据情况。
2. **compare=true 必须带对比时间**：开启同环比（`compare: true`）时，必须同时传入 `comparison_start_time` 和 `comparison_end_time`，格式与 `start_time`/`end_time` 一致。
3. **缓存相关指标**：`de_rta_hit_cache_rate`（缓存命中率）和 `de_rta_err_cache_rate`（异常缓存兜底命中率）的分母都是 `de_rta_req_token`，两者互补可以反映缓存的健康度。
4. **`引擎_RTA_请求数`与`RTA_Token_请求数`的区别**：`引擎_RTA_请求数`是引擎请求rta都进行计数，命中缓存的也在内，不一定是实时真正下发给客户的。`RTA_Token_请求数`，不会有命中缓存的这部分请求的统计，实时确实下发给客户的。日常判断通过率一般使用`引擎_RTA_请求数`系列口径。
5. **`avg_de_rta_boost`有什么用**：客户在返回要不要请求的基础上，也可以针对该流量价值返回一个RTA出价系数。
