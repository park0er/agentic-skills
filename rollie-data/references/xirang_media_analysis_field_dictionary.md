---
name: xirang-media-analysis-field-dictionary
description: query_xirang_media_analysis 字段词典——媒体多维分析看板（boardId=17），维度 29 个，指标 80 个，默认指标 fee_effect。
---

# 媒体多维分析看板 字段词典（query_xirang_media_analysis）

漏斗位置：**媒体多维分析**（boardId=17，息壤正式环境）

用途：按媒体、广告位、DSP、联盟应用/广告位/开发者、设备和用户维度查看请求、填充、曝光、点击、收入、转化和系统预估指标，排查媒体侧流量质量和收益变化。

- 默认维度: `dt`；默认指标: `fee_effect`
- 时间粒度: 支持 `86402`(合计)、`86401`(日均)、`86400`(按天)、`604800`(按周)、`2592000`(按月)

## 推荐查询

```json
{
  "dashboard": "query_xirang_media_analysis",
  "params": {
    "time": {
      "start_time": "2026-07-08T00:00:00+08:00",
      "end_time": "2026-07-09T00:00:00+08:00",
      "compare": false
    },
    "filters": {
      "media_type": "1"
    },
    "split": {
      "group_by": "tag_id",
      "top": 50,
      "sort_by": "fee_effect"
    },
    "measures": [
      "fee_effect",
      "query",
      "valid_query",
      "view",
      "click"
    ]
  }
}
```

## 维度

### 时间

| 字段 | 中文名 | 说明 |
|---|---|---|
| `dt` | 时间 | 默认选中；支持时间粒度: 86402, 86401, 86400, 604800, 2592000 |

### 流量

| 字段 | 中文名 | 说明 |
|---|---|---|
| `media_type` | 媒体 |  |
| `tag_id` | 广告位 |  |
| `ad_form_id` | 广告位形式 | `1`=信息流、`3`=开屏、`5`=文字链、`7`=情景、`9`=非标 |
| `tag_status` | 广告位状态 | `0`=活跃、`1`=关闭、`2`=废弃 |
| `union_sdk_version` | 米盟SDK版本 |  |

### DSP

| 字段 | 中文名 | 说明 |
|---|---|---|
| `dsp_level1` | 一级dsp | `dsp`=DSP、`brand`=品牌、`effect`=效果 |
| `dsp_level2` | 二级DSP |  |

### 应用

| 字段 | 中文名 | 说明 |
|---|---|---|
| `app_id` | 应用ID |  |

### 计划

| 字段 | 中文名 | 说明 |
|---|---|---|
| `target_conv_type` | 目标转化类型 |  |
| `deep_target_conv_type` | 深层目标转化类型 |  |

### 联盟

| 字段 | 中文名 | 说明 |
|---|---|---|
| `ua_id` | 联盟应用Id | 如 `1002496` |
| `up_id` | 联盟广告位 | 如 `15000001` |
| `union_style_id` | 联盟广告样式 | 如 `1` |
| `union_developer_id` | 联盟开发者Id | 如 `4228` |
| `union_category_name` | 联盟行业名称 | 如`新闻` |
| `union_source_name` | 联盟渠道来源名称 | 如`游戏`、`第三方APP`、`快应用`、`快游戏` |
| `union_access_model` | 联盟接入方式 | `0`=SDK、`1`=API、`3`=系统开屏、`5`=系统开屏、`6`=JS-SDK |
| `union_is_api_bidding` | 是否bidding | `0`=否、`1`=是、`-999`=unknown |
| `u_traffic_type` | 是否联盟冷启流量 | `0`=未判断流量、`1`=常规流量、`2`=冷启动流量 |
| `agent_type` | 联盟代理类型 | `0`=非代理、`1`=ssp代理、`2`=单应用代理、`3`=团队账号 |
| `quick_app_version` | 快应用框架版本 |  |

### 用户

| 字段 | 中文名 | 说明 |
|---|---|---|
| `spu_price_bucket` | spu价位分桶 |  |
| `sku_price_bucket` | sku价位分桶 |  |
| `series_name` | 机型名称 |  |
| `device_age` | 机龄代号 |  |
| `device_type` | 设备类型 | `平板`=平板、`手机`=手机、`unknown`=unknown |
| `is_personalized_closed` | 是否关闭个性化开关 | `true`=是、`false`=否 |
| `client_version` | 客户端版本 |  |

## 指标

### 行为链路

| 字段 | 中文名 | 说明 |
|---|---|---|
| `query` | 请求数 |  |
| `raw_query` | 原始请求数 |  |
| `valid_query` | 有效请求数 |  |
| `delivery` | 有广告下发的请求数 |  |
| `ad_delivery` | 广告下发数 |  |
| `drop_query` | drop请求数 |  |
| `view` | 计费曝光 |  |
| `fill` | 有广告下发的请求数（填充数） |  |
| `click` | 计费点击 |  |
| `ad_delivery_new` | 广告实际下发数 |  |
| `raw_start_download` | 原始开始下载 |  |
| `start_download` | 开始下载 |  |
| `cancel_download` | 取消下载 |  |
| `download_success` | 下载成功 |  |
| `install_success` | 安装成功 |  |
| `landing_page_view` | 落地页曝光 |  |
| `landing_page_click` | 落地页点击 |  |
| `video_start` | 视频播放开始 |  |
| `video_fail` | 视频启播失败 |  |
| `video_finish` | 视频播放完成 |  |
| `dislike` | 负反馈数 |  |
| `delivery_query_rate` | 填充率 |  |
| `avg_ad_delivery` | 平均广告下发数 |  |
| `ad_delivery_view_rate` | 下发原始曝光率 |  |
| `ctr_view_bill` | CTR_曝光计费率 | 计费数 / 计费曝光 |
| `cvr_click_download` | 点击下载率 | 开始下载 / 计费点击 |
| `cvr_bill_conv_z` | CVR_计费转化率(Z） | 目标转化数(Z) / 计费数 |
| `avg_target_cpa_view` | 平均目标出价_曝光 | 总计目标出价_曝光 / 计费曝光 |
| `avg_deep_target_cpa_view` | 平均深层目标出价_曝光 | 合计深层目标出价_曝光 / 计费曝光 |
| `cvr_view_download` | 曝光下载率 | 开始下载 / 计费曝光 |
| `download_cancel_rate` | 取消下载率 |  |
| `download_success_rate` | 下载成功率 |  |
| `Install_success_rate` | 安装成功率 |  |
| `activesuccess_rate` | 激活成功率 |  |
| `deeplink_success_start` | DP开始调起_DP调起成功率 |  |
| `deeplink_start_click` | 计费点击_DP开始调起率 |  |
| `landing_page_ctr` | 落地页点击率 |  |
| `video_start_rate` | 开始播放率 |  |
| `video_faile_rate` | 视频播放失败率 |  |
| `dislike_view_rate` | 负反馈率 |  |
| `video_finish_rate` | 播放完成率 |  |
| `click_filter_rate` | 点击作弊过滤比例 | (原始点击 - 计费点击) / 原始点击 |
| `view_filter_rate` | 曝光作弊过滤比例 | (原始曝光 - 计费曝光) / 原始曝光 |
| `view_success_rate` | 曝光成功率 |  |
| `dev_win_num` | 开发者竞胜数 |  |
| `dev_win_num_rate` | 开发者竞胜率 |  |
| `valid_query_rate` | 请求承接率 |  |
| `drop_query_rate` | drop率 |  |
| `delivery_valid_query_rate` | 有效填充率 |  |
| `win_delivery_rate` | 竞胜率 |  |

### 收入相关

| 字段 | 中文名 | 说明 |
|---|---|---|
| `fee_effect` | emi效果收入 | 默认选中；emi现金+返券+现金Back+充值 |
| `fee_dsp_rtb` | 外部DSPRtb收入 |  |
| `ecpm` | 实际eCPM | 1000 × (emi效果+品牌+外部Dsp) / 计费曝光 |
| `cpd` | CPD | (emi效果+品牌+外部Dsp) / 开始下载 |
| `cpc` | CPC | (emi效果+品牌+外部Dsp) / 计费点击 |
| `raw_fee_total` | 总收入 | emi效果+品牌+外部Dsp |
| `rpm` | rpm |  |
| `dev_fee` | 开发者收入 |  |
| `avg_dev_pecpm_view` | 平均开发者ecpm_曝光 |  |
| `dropped_req_fee` | drop请求对应收入 |  |
| `un_dropped_traffic_10pct_fee` | 10%未drop流量的总收入 |  |
| `drop_revenue_loss_rate` | drop收入损失率 |  |
| `revenue_per_mille` | 每千次请求收入 |  |

### 通用转化_转化点

| 字段 | 中文名 | 说明 |
|---|---|---|
| `target_conv_num_z` | 目标转化数(Z) |  |
| `deep_target_conv_num_z` | 深层目标转化数(Z) |  |
| `avg_target_cpa_conv_z` | 平均目标出价_转化(Z) | 总计目标出价_转化(Z) / 目标转化数(Z) |
| `avg_deep_target_cpa_deep_conv_z` | 平均深层目标出价_深层转化(Z) | 总计深层目标出价(Z) / 深层目标转化数(Z) |
| `target_conv_cost_z` | 实际转化成本(Z) | emi效果收入 / 目标转化数(Z) |
| `new_deep_billing_ratio_z` | 深层计费比(Z) | emi效果收入 / 深层广告主价值(Z) |
| `billing_ratio_z` | 计费比(Z) | emi效果收入 / 广告主价值(Z) |

### 小米自采集转化_转化点

| 字段 | 中文名 | 说明 |
|---|---|---|
| `own_new_day_active_z` | 小米新增当日激活(Z) |  |

### 系统预估

| 字段 | 中文名 | 说明 |
|---|---|---|
| `avg_pctr_view` | 平均pctr_曝光 | 总计pctr_曝光 / 计费曝光 |
| `avg_pcvr_bill` | 平均pcvr_计费点 | 总计pcvr_计费点 / 计费数 |
| `avg_pcvrfix_bill` | 平均pcvrFix_计费点 | 总计pcvrFix_计费点 / 计费数 |
| `ctr_view_click` | CTR_曝光点击率 | 计费点击 / 计费曝光 |
| `ctr_pcoc` | ctr pcoc | avg_pctr_view / CTR曝光计费率 |
| `cvr_pcoc_z` | cvr pcoc(Z) | 平均pcvrFix_计费点 / CVR扣费转化率(Z) |
| `avg_bidding_pecpm_view` | 平均Bidding出价pecpm_曝光 |  |
| `avg_adx_pecpm_view` | 平均adx出价pecpm_曝光 |  |
| `avg_derankscore_view` | 平均引擎精排rankScore_曝光 |  |
