---
name: xirang-adx-diagnosis-field-dictionary
description: query_xirang_adx_diagnosis（ADX链路多维分析，息壤版）字段含义，供传参前确认使用
---

# ADX链路多维分析看板-息壤版（query_xirang_adx_diagnosis）

漏斗位置：**ADX竞价链路**（外部DSP填充→参竞→竞胜→下发）

用途：分析ADX竞价环节的外部DSP填充、参竞、竞胜漏斗，了解分媒体/分广告位过滤原因。一般搭配 `tag_id` × `dsp_level2` 进行数据下钻，常用指标为填充率、参竞率（=填充率）、竞胜率、广告条数、过滤原因等。

---

## 一、维度字段

| 字段名 | 中文名 | 枚举值 / 外接引用 |
|---|---|---|
| `dt` | 时间, 时间维度 | 需配合 `time_granularity` 使用；见下方时间粒度编码表 |
| `media_type` | 媒体, 媒体类型 | ⚠️ **中文映射必须先读取** `./enums/media_type_cn_mapping.md` |
| `tag_id` | 广告位, 广告位ID | ⚠️ **中文映射必须先读取** `./enums/xirang_ad_effect_enum_tag_id.md` |
| `app_id` | 应用ID, 应用, **客户** | ⚠️ **中文映射必须先读取** `./enums/top_appid_cn_mapping.md`。⚠️ **"客户"在本系统中专指 app_id，不是 customer_id** |
| `if_accurate_pair` | query命中精准词表 | `0`=非精准搜索、`1`=精准搜索。由 adpm 维护的精准词表判定 |
| `adx_host` | 机器, ADX机器 | 按ADX机器下钻 |
| `env` | 集群, 服务集群 | `C3`=C3、`AKSRV`=AKSRV、`unknown`=unknown |
| `physical_dsp` | 物理DSP | 如 `xiaomi`、`deV2`、`deAppStore`。媒体直接对接的外部DSP |
| `dsp_level2` | 二级DSP | 如 `xiaomi.ocpa`。**核心维度**，物理DSP下面的二级DSP，搭配 `tag_id` 做交叉下钻 |
| `deal_id` | 品牌合约ID | 品牌广告信息，类似效果广告的计划ID。如 `SSP-MI-deal-1005716` |
| `template_id` | 返回广告模板 | 按广告模板下钻，模板清单见 [ADX模板管理](https://admin-ssp.ad.xiaomi.com/#/metadata/template) |
| `ua_id` | 联盟应用Id, uaid | 如 `1002496` |
| `up_id` | 联盟广告位, upid | 如 `15000001` |
| `style` | 联盟广告样式 | 联盟广告样式维度 |
| `developerid` | 联盟开发者ID | 联盟开发者维度 |
| `sourcename` | 联盟渠道来源名称 | 联盟渠道维度 |
| `accessmode` | 联盟接入方式 | 联盟接入方式维度 |
| `bid_floor_type` | 底价类型 | ADX 生效的底价策略类型 |
| `fee_bid_type` | ADX扣费类型 | 扣费方式类型 |
| `adx_reason` | 过滤原因 | **核心维度**，查看各过滤原因分布，枚举见 `./enums/xirang_adx_diagnosis_enum_adx_reason.md` |
| `adx_status` | ADX状态 | `NOAD`=无广告返回、`WIN`=竞胜、`BID_FAIL`=竞败、`AD_FILTER`=广告被过滤、`NO_REQ`=无请求、`REQ_FAIL`=请求失败 |
| `agent_type` | 联盟代理类型 | 枚举值：`0`=非代理、`1`=ssp代理、`2`=单应用代理、`3`=团队账号 |

**注意：此看板不支持搜索词（query/keyword/search query）维度查询。**

> **核心下钻组合**：`tag_id` × `dsp_level2` 是分析 ADX 漏斗最常用的下钻方式，用于定位是哪个广告位在哪个 DSP 上出了问题。

---

## 二、指标字段

| 字段名 | 中文名 | 类型 | 公式说明 |
|---|---|---|---|
| `adx_request` | ADX请求数 | raw | 当前期内ADX发起的请求总量。⚠️ 仅支持搭配 `tag_id`/`physical_dsp`/`deal_id` 维度使用，其他维度数值无意义 |
| `adx_fill` | ADX填充数 | raw | 外部DSP返回广告的数量（参竞数） |
| `adx_fill_rate` | ADX填充率 | derived | `adx_fill / adx_request`。可能超过100%，符合预期（一次请求可填充多条广告） |
| `adx_win` | ADX竞胜数 | raw | 竞价成功下发的广告数 |
| `adx_win_rate` | ADX竞胜率 | derived | `adx_win * 100 / adx_request`。可能超过100%，符合预期 |
| `adx_rtb_fill` | ADX实时竞价填充数 | raw | RTB模式下DSP返回的广告数 |
| `adx_avg_bid_ecpm` | 平均ADX实时竞价ecpm | derived | `adx_rtb_fill 的 ecpm 总和 / adx_rtb_fill 数量 / 100000` |
| `adx_media_request` | ADX媒体请求数 | raw | 媒体打给DSP的请求数。⚠️ 仅支持搭配 `tag_id`/`physical_dsp`/`deal_id` 维度使用，其他维度数值无意义 |
| `adx_only_effect_timeout` | ADX超时数_仅效果dsp | raw | 仅效果DSP维度的超时次数 |
| `adx_include_brand_timeout` | ADX超时数_有品牌dsp | raw | 包含品牌DSP维度的超时次数 |
| `adx_only_effect_timeout_rate` | ADX超时率_仅效果dsp | derived | `adx_only_effect_timeout / adx_request` |
| `adx_include_brand_timeout_rate` | ADX超时率_有品牌dsp | derived | `adx_include_brand_timeout / adx_request` |

> **填充率/竞胜率注意**：这两个比率的分母是 `adx_request`（请求数），分子是填充数/竞胜数。由于一次请求可以对应多条填充/竞胜，比率可能超过 100%，这是正常行为，不表示数据异常。

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
| `604800` | 按周 | `"YYYY-MM-DD"`（周起始日） | ≤ 30天 |

不传 `time_granularity` 时默认 `86402`（合计，整段1行），等价于不按时间分组，无法看趋势。`minTableGranularity` 为 60 秒，不应使用更细粒度查询。

---

## 三、典型查询示例

### 示例1：按广告位 × 二级DSP 交叉下钻（最常用）

定位哪个广告位在哪个 DSP 上填充/竞胜出了问题：

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": false
  },
  "split": { "group_by": ["tag_id", "dsp_level2"], "top": 100, "sort_by": "adx_request" },
  "measures": ["adx_request", "adx_fill", "adx_fill_rate", "adx_win", "adx_win_rate"]
}
```

### 示例2：按过滤原因查看过滤分布

查看 ADX 链路中各过滤原因的量级分布，定位主要过滤项：

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": false
  },
  "split": { "group_by": "adx_reason", "top": 50, "sort_by": "adx_request" },
  "measures": ["adx_request", "adx_fill", "adx_win"]
}
```

### 示例3：按媒体下钻看各媒体 ADX 漏斗

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": false
  },
  "split": { "group_by": "media_type", "top": 20, "sort_by": "adx_request" },
  "measures": ["adx_request", "adx_fill", "adx_fill_rate", "adx_win", "adx_win_rate"]
}
```

### 示例4：锁定特定广告位，下钻二级DSP + 过滤原因

先锁定问题广告位，再逐 DSP 查看各过滤原因分布：

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": false
  },
  "filters": { "tagId": "1.11.t.1" },
  "split": { "group_by": ["dsp_level2", "adx_reason"], "top": 100, "sort_by": "adx_request" },
  "measures": ["adx_request", "adx_fill", "adx_win"]
}
```

### 示例5：按小时看 ADX 漏斗趋势（带同环比）

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-01T23:59:59+08:00",
    "compare": true,
    "comparison_start_time": "2026-05-31T00:00:00+08:00",
    "comparison_end_time": "2026-05-31T23:59:59+08:00"
  },
  "split": { "group_by": "dt", "time_granularity": 3600, "top": 24, "sort_by": "adx_request" },
  "measures": ["adx_request", "adx_fill", "adx_fill_rate", "adx_win", "adx_win_rate"]
}
```

### 示例6：按物理DSP过滤，查看超时情况（带同环比）

排查某个 DSP 的超时问题：

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": true,
    "comparison_start_time": "2026-05-31T00:00:00+08:00",
    "comparison_end_time": "2026-05-31T23:59:59+08:00"
  },
  "filters": { "physicalDsp": "xiaomi" },
  "split": { "group_by": "tag_id", "top": 50, "sort_by": "adx_request" },
  "measures": ["adx_request", "adx_only_effect_timeout", "adx_only_effect_timeout_rate"]
}
```

---

## 使用注意事项

1. **`adx_request` 维度限制**：该指标只支持搭配 `tag_id`、`physical_dsp`、`deal_id` 维度使用。如果用其他维度（如 `adx_reason`、`dsp_level2`）分组，请求数值可能无业务意义。
2. **比率可能超过100%**：`adx_fill_rate` 和 `adx_win_rate` 可能超过100%，因为一次请求可以对应多条填充/竞胜，属于正常行为。
3. **过滤原因枚举**：`adx_reason` 返回的是英文代码（如 `NOAD`、`TimeoutException`、`LOW_PRICE`），中文含义查阅 `./enums/xirang_adx_diagnosis_enum_adx_reason.md`。
4. **compare=true 必须带对比时间**：开启同环比（`compare: true`）时，必须同时传入 `comparison_start_time` 和 `comparison_end_time`，格式与 `start_time`/`end_time` 一致。
5. **品牌合约过滤**：如需按品牌合约维度过滤，使用 `deal_id`（或 alias `dealId`）。
