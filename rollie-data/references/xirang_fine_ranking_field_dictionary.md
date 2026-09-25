---
name: xirang-fine-ranking-field-dictionary
description: query_xirang_fine_ranking（精排链路多维分析）字段含义，供传参前确认使用
---

# 精排链路多维分析看板-息壤版（query_xirang_fine_ranking）

漏斗位置：**⑥ 精排(息壤)**（广告进入精排模型，按 pctr/pcvr/pltv 等打分排序）

用途：排查精排阶段请求量变化与模型打分分布异常。常用 `count` 指标配合 `media_type`、`tag_id`、`filter_reason`、`rank_adsource` 等维度下钻分析。

---

## 一、维度字段

| 字段名 | 中文名 | 维度说明 | 枚举值说明 |
|---|---|---|---|
| `dt` | 时间, 时间维度 | 需配合 `time_granularity` 使用；见下方时间粒度编码表 | — |
| `media_type` | 媒体, 媒体类型 | 媒体 | 完整清单见 `./enums/media_type_cn_mapping.md` |
| `tag_id` | 广告位, 广告位ID | 广告位 | 完整清单见 `./enums/xirang_ad_effect_enum_tag_id.md` |
| `adengine_expids` | 引擎实验ID | 精排引擎层实验 ID | 数字 ID |
| `chunfen_expids2` | 召回层辅实验ID | 上游召回层辅实验 ID | 数字 ID |
| `cvr_expid` | 精排CVR实验ID | 精排 CVR 模型实验 ID | 数字 ID |
| `adjust_ctr_expid` | 校准-精排CTR实验ID | 校准层 CTR 实验 ID | 数字 ID |
| `recall_expid` | 粗排实验ID | 上游粗排层实验 ID | 数字 ID |
| `ctr_expid` | 精排CTR实验ID | 精排 CTR 模型实验 ID | 数字 ID |
| `chunfen_expids` | 召回层主实验ID | 上游召回层主实验 ID | 数字 ID |
| `adjust_cvr_expid` | 校准-精排CVR实验ID | 校准层 CVR 实验 ID | 数字 ID |
| `env` | 集群, 服务集群 | 精排服务所在集群 | 用于区分线上集群和实验集群 |
| `dsp` | 二级DSP | 二级 DSP 标识 | DSP 名称字符串 |
| `app_id` | 应用ID, App ID | 小米开放平台注册的应用标识 | 数字 ID |
| `billing_type` | 计费类型 | 广告计费方式 | `3`=CPD |
| `ad_id` | 广告ID, 创意ID | 广告创意标识 | 数字 ID |
| `campaign_id` | 广告计划, 推广计划ID | 广告计划的唯一标识 | 数字 ID |
| `target_conv_type` | 目标转化类型 | 广告投放目标转化类型 | — |
| `deep_target_conv_type` | 深层目标转化类型 | 深层转化目标类型 | — |
| `fresh_ad` | 是否新广告 | 是否新广告标识 | `0`=否、`1`=是 |
| `search_keyword` | 搜索词 | 搜索广告场景的搜索词 | 字符串 |
| `is_discard` | 是否被过滤 | 精排阶段是否被过滤丢弃 | `0`=未过滤、`1`=被过滤 |
| `filter_reason` | 过滤原因 | 精排阶段广告被过滤的原因 | 待确认枚举值 |
| `rank_adsource` | 粗排通路来源 | 粗排通路来源标识 | 待确认枚举值 |
| `recall_channel_name` | 召回通路来源 | 广告召回通道来源 | `ann`=向量召回(ANN) 等 |

---

## 二、指标字段

### 请求数

| 字段名 | 中文名 | 公式说明 |
|---|---|---|
| `count` | 请求数 | 进入精排的请求总数 |

### CTR 相关

| 字段名 | 中文名 | 公式说明 |
|---|---|---|
| `avg_pctr_rank` | 平均pctr_精排 | 精排 pCTR 均值 |
| `avg_pctrraw_rank` | 平均原始pctr_精排 | 精排原始 pCTR 均值 |
| `avg_pcvr1_rank` | 平均pcvr1_精排 | 精排 pCVR1 均值 |
| `avg_pcvr2_rank` | 平均pcvr2_精排 | 精排 pCVR2 均值 |
| `avg_pcvr1fix_rankl` | 平均pcvr1fix_精排 | 精排 pCVR1 校准后均值 |
| `avg_pcvr2fix_rank` | 平均pcvr2fix_精排 | 精排 pCVR2 校准后均值 |

### CVR 相关

| 字段名 | 中文名 | 公式说明 |
|---|---|---|
| `avg_pcvr_rank` | 平均pcvr_精排 | 精排 pCVR 均值 |
| `avg_pcvrfix_rank` | 平均pcvrfix_精排 | 精排 pCVR 校准后均值 |
| `avg_pdeepcvr_rank` | 平均pdeepcvr_精排 | 精排 pDeepCVR 均值 |
| `avg_pdeepcvrfix_rank` | 平均pdeepcvrfix_精排 | 精排 pDeepCVR 校准后均值 |

### LTV 相关

| 字段名 | 中文名 | 公式说明 |
|---|---|---|
| `sum_pltv_rank` | 总计pltv_精排 | pLTV 求和 |
| `sum_pdeepltv_rank` | 总计pdeepltv_精排 | pDeepLTV 求和 |
| `sum_pltvfix_rank` | 总计pltvfix_精排 | pLTV 校准后求和 |
| `sum_pdeepltvfix_rank` | 总计pdeepltvfix_精排 | pDeepLTV 校准后求和 |
| `avg_pltv_rank` | 平均pltv_精排 | pLTV 均值 |
| `avg_pltvfix_rank` | 平均pltvfix_精排 | pLTV 校准后均值 |
| `avg_pdeepltv_rank` | 平均pdeepltv_精排 | pDeepLTV 均值 |
| `avg_pdeepltvfix_rankl` | 平均pdeepltvfix_精排 | pDeepLTV 校准后均值 |

### 出价相关

| 字段名 | 中文名 | 公式说明 |
|---|---|---|
| `avg_pbidprice_rank` | 平均pbidprice_精排 | 精排 bid price 均值 |
| `avg_pecpm_rank` | 平均pecpm_精排 | 精排 eCPM 均值 |
| `avg_pocpa_rank` | 平均pocpa_精排 | 精排 oCPA 均值 |
| `avg_rtacoef_rank` | 平均rtacoef_精排 | 精排 RTA 系数均值 |

---

## 三、时间粒度

息壤看板支持的时间粒度编码（通过 `time_granularity` 参数传入）：

| 编码 | 含义 |
|---|---|
| `86402` | 合计（默认） |
| `86400` | 天 |
| `3600` | 小时 |
| `300` | 5 分钟 |

---

## 四、调用示例

```bash
# 默认查询（汇总）
bash scripts/query/dashboard_query.sh \
  --params '{"dashboard":"query_xirang_fine_ranking","time":{"start_time":"2026-06-07T00:00:00+08:00","end_time":"2026-06-08T00:00:00+08:00","compare":false}}' \
  --session-id <session_id>

# 按媒体分组
bash scripts/query/dashboard_query.sh \
  --params '{"dashboard":"query_xirang_fine_ranking","time":{"start_time":"2026-06-07T00:00:00+08:00","end_time":"2026-06-08T00:00:00+08:00","compare":false},"split":{"group_by":"media_type","top":10}}' \
  --session-id <session_id>

# 按过滤原因下钻
bash scripts/query/dashboard_query.sh \
  --params '{"dashboard":"query_xirang_fine_ranking","time":{"start_time":"2026-06-07T00:00:00+08:00","end_time":"2026-06-08T00:00:00+08:00","compare":false},"split":{"group_by":"filter_reason","top":10}}' \
  --session-id <session_id>
```
