---
name: request-info-field-dictionary
description: query_request_info（媒体请求）字段含义，供传参前确认使用
---

# 媒体请求看板（query_request_info）

漏斗位置：① 媒体请求

用途：确认上游流量入口是否正常，判断掉量是否源于媒体侧请求减少。

## 支持的过滤参数

| 参数名 | 说明 |
|---|---|
| `tagId` | 过滤到指定广告位 |
| `mediaType` | 过滤到指定媒体类型 |
| `uaid` | 过滤到指定联盟应用 |
| `upid` | 过滤到指定联盟广告位 |
| `unionAppType` | 过滤到指定联盟应用类型 |
| `unionDeveloperId` | 过滤到指定联盟开发者 |
| `unionSource` | 过滤到指定联盟渠道来源 |

## 维度（group_by 可选值）

| 规范名 | 后端字段名 | 前端 UI 展示名 | 中文含义与别名 | 诊断用途 |
|---|---|---|---|---|
| `tagId` | `tagId` | 广告位 | 广告位 ID, tag_id, tagid | 按广告位下钻，看哪个位置请求量变化 |
| `mediaType` | `mediaType` | 媒体 | 媒体类型, media_type, mediatype, 媒体 | 按媒体类型（xiaomi/union/APP_STORE 等）下钻 |
| `uaid` | `uaid` | uaid | 联盟应用 ID, UA ID, ua_id, uaId, ua id, 联盟应用, 联盟应用id | 按联盟应用下钻，判断是否特定应用请求量异常减少 |
| `upid` | `upid` | upid | 联盟广告位 ID, UP ID, up_id, upId, up id, 联盟广告位, 联盟广告位id | 按联盟广告位下钻，定位具体广告位请求变化 |
| `unionAppType` | `unionAppType` | Union App Type | 联盟应用类型, 应用类型, union_app_type, unionapptype, union app type, 联盟应用类型 | 按联盟应用类型下钻 |
| `unionDeveloperId` | `unionDeveloperId` | Union Developer Id | 联盟开发者 ID, 开发者 ID, union_developer_id, uniondeveloperid, union developer id, developerid, developerName, 开发者, 联盟开发者 | 按联盟开发者下钻，判断是否特定开发者流量异常 |
| `unionSource` | `unionSource` | Union Source | 联盟渠道来源名称, 联盟来源, 渠道来源, 流量来源, union_source, union_source_name, unionsource, union source, sourcename, sourceName, source_name, 来源 | 按联盟渠道（如游戏、第三方APP、快应用）下钻 |

**注意：此看板不支持搜索词（query/keyword/search query）维度查询。**

## 指标（measures 可选值）

| 规范名 | 后端字段名 | 前端 UI 展示名 | 中文含义与别名 | 诊断用途 |
|---|---|---|---|---|
| `count` | `count` | Count | 记录条数, 原始日志条数 | 原始日志条数，一般不直接用 |
| `eRawQuery` | `eRawQuery` | 总请求 | 总请求, 总请求数, 原始请求数, 原始请求 | 媒体侧发出的全部广告请求，含重复。全量流量入口指标 |
| `eQuery` | `eQuery` | 有效请求 | 有效请求, 有效请求数, 去重请求数 | 实际进入广告竞价的有效请求量，去重后的真实竞标流量 |
| `eFill` | `eFill` | 填充量 | 填充量, 填充数, 下发数, 返回数 | 广告竞价后有广告填充的次数，反映是否有广告可下发 |
| `fill_rate` | `fill_rate` | 填充率(填充/有效请求) | 填充率, 有效填充率 | 推导指标：`eFill / eQuery × 100%`。反映广告供给是否充足 |

三者关系：`eRawQuery ≥ eQuery ≥ eFill`

- `eQuery / eRawQuery` = 有效请求率，反映去重后的流量质量
- `eFill / eQuery` = 填充率（即 `fill_rate`），反映广告供给是否充足
- `fill_rate` 是 Plywood 预定义推导指标，等价于 `eFill / eQuery × 100`，可直接作为 measure 使用

## 典型查询示例

### 基础维度下钻：看某个广告位的请求量和填充率变化

```json
{
  "time": {
    "start_time": "2026-03-01T00:00:00+08:00",
    "end_time": "2026-03-02T00:00:00+08:00",
    "compare": true,
    "comparison_start_time": "2026-02-28T00:00:00+08:00",
    "comparison_end_time": "2026-03-01T00:00:00+08:00"
  },
  "filters": { "tagId": "1.11.t.1" },
  "split": { "group_by": "tagId" },
  "measures": ["eRawQuery", "eQuery", "eFill", "fill_rate"]
}
```

### 联盟维度下钻：按 tagId + uaid 排查某个联盟应用在某广告位的请求量

```json
{
  "time": {
    "start_time": "2026-03-01T00:00:00+08:00",
    "end_time": "2026-03-02T00:00:00+08:00",
    "compare": true,
    "comparison_start_time": "2026-02-28T00:00:00+08:00",
    "comparison_end_time": "2026-03-01T00:00:00+08:00"
  },
  "filters": { "tagId": "1.11.t.1", "uaid": "1002496" },
  "split": { "group_by": "mediaType", "sort_by": "eQuery", "top": 20 },
  "measures": ["eRawQuery", "eQuery", "eFill", "fill_rate"]
}
```

### 联盟渠道来源下钻

```json
{
  "time": {
    "start_time": "2026-03-01T00:00:00+08:00",
    "end_time": "2026-03-02T00:00:00+08:00",
    "compare": true,
    "comparison_start_time": "2026-02-28T00:00:00+08:00",
    "comparison_end_time": "2026-03-01T00:00:00+08:00"
  },
  "split": { "group_by": "unionSource", "sort_by": "eRawQuery", "top": 10 },
  "measures": ["eRawQuery", "eQuery", "eFill", "fill_rate"]
}
```

## 诊断要点

### 基础诊断

- 如果 `eQuery` 同比大幅下降 → 上游流量减少，问题在媒体侧，与广告本身无关
- 如果 `eQuery` 正常但 `eFill` 下降 → 填充率下降，广告供给侧问题，需往下游漏斗排查
- 如果 `eQuery` 和 `eFill` 都正常 → 媒体请求环节无异常，继续查下游

### 联盟流量专项诊断

- 按 `uaid` 下钻，如果某个应用的 `eQuery` 大幅下降 → 该应用流量减少，检查该应用是否被限流或下架
- 按 `upid` 下钻，如果某个广告位的 `fill_rate` 显著低于均值 → 该广告位广告供给不足，需排查该广告位的召回/过滤链路
- 按 `unionSource` 下钻，如果某个渠道（如快应用）的 `eRawQuery` 整体下降 → 渠道侧流量入口变化，排查渠道合作状态
- 按 `unionDeveloperId` 下钻，如果某个开发者的全部应用请求骤降 → 检查该开发者是否被策略调整或限流
