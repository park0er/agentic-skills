---
name: xirang-ad-effect-field-dictionary
description: query_xirang_ad_effect 高频字段词典——维度（app_id/customer_id/tag_id/campaign_id/ad_id/core_id/agent_id 等 14 个）和指标（total_fee_effect/fee_effect/view/click/ctr/ecpm 等 23 个），含 split 参数、时间粒度编码、Z/J 归因说明。找不到的字段去低频词典。
---

# 广告效果看板-息壤版 字段词典（query_xirang_ad_effect）

漏斗位置：**⑦ 曝光后链路**（board_id=2）

用途：查看广告的实际效果数据，包括曝光、点击、收入、转化等核心指标，支持按广告/计划/广告位/媒体/应用/计费类型等多维度下钻，以及按时间粒度查看趋势。

---

## 全局参考

### 字段查找规则

> ⚠️ 高频文档只收录请求占比 ≥5% 的字段。**当用户描述能在本文档"差不多"找到字段时，你最容易踩坑**——因为低频字典里很可能有一个语义更精准的字段。遇到下面任一情况，必须先翻 `./xirang_ad_effect_field_dictionary_low_freq.md` 再决定：

1. **完全找不到**：用户说的概念在主字典里没有任何字段对得上 → 翻低频字典
2. **语义近似但不完全等同**：主字典里有个字段名字"沾边"，但用户的措辞带了主字典字段覆盖不到的修饰
   - 触发信号：用户用了"X 的 Y"、"X 类 Y"、"X 下的 Y"、"按 X 的 Y 分"、"X 来源 / X 类型 / X 渠道"等带限定词的表达
   - 例：用户说"联盟第三方APP"，主字典只有 `media_type`（取值 union/...），但"第三方APP"是 union 内部的细分 → 必须翻低频字典找到 `union_source_name`
   - 例：用户说"运营一级行业"，主字典有 `oper_industry_level2`，但用户带了"一级"修饰 → 翻低频字典确认 `oper_industry_level1`
3. **枚举值像但不完全像**：主字典字段名匹配，但用户说出的具体值不在该字段的常见枚举里
   - 例：`media_type` 常见值是 union / APP_STORE 等英文/系统码；用户说"第三方APP"这种中文细分名 → 八成是另一个字段的枚举，去低频字典里搜这个值

> **判断准则**：在主字典里找到一个候选字段后，先问自己一句——"用户那段措辞里有没有这个字段覆盖不到的限定信息？"如果有，翻低频字典；翻完没有更精准的，再回来用主字典字段。
> **不要凭印象猜字段；不要因为字段名"沾边"就直接落库。**

### 时间粒度编码（仅 `dt` 字段）

> `time_granularity` **必须与 `split.group_by = "dt"` 同时使用**，否则无效。

| 编码 | 含义 | dt 字段格式 |
|---:|---|---|
| `86402` | 合计（默认） | 无 |
| `86401` | 日均 | 无 |
| `300` | 5分钟 | `"YYYY-MM-DD HH:MM"` |
| `3600` | 按小时 | `"YYYY-MM-DD HH:MM"` |
| `86400` | 按天 | `"YYYY-MM-DD"` |
| `604800` | 按周 | `"YYYY-MM-DD"`（周起始日） |
| `2592000` | 按月 | `"YYYY-MM"` |

---

## 一、高频维度字段

> ⚠️ **高频维度的独立枚举文档收录前 100 个值；若在独立文档中找不到目标值，必须打开通用枚举文档 `./enums/xirang_ad_effect_enums_misc.md` 查找。**

| 字段名 | 中文名 | 枚举值 / 外接引用 |
|---|---|---|
| `app_id` | 应用ID, 应用, **客户** | ⚠️ **中文名映射必须先读取** `./enums/top_appid_cn_mapping.md`。⚠️ **"客户"在本系统中专指 app_id，不是 customer_id** |
| `customer_id` | 效果广告主账户, 账户ID, 广告主 | 如 `1121231`。注意：customer_id 是 app_id 的下一层级 |
| `dt` | 时间, 时间维度 | 需配合 `time_granularity` 使用；见上方时间粒度编码表 |
| `tag_id` | 广告位, 广告位ID | ⚠️ **中文映射必须先读取** `./enums/xirang_ad_effect_enum_tag_id.md` |
| `target_conv_type` | 目标转化类型, 转化目标 | ⚠️ **中文映射必须先读取**`./enums/xirang_ad_effect_enum_target_conv_type.md`。⚠️ **提到"转化类型"时，若无特殊说明，默认使用本字段** |
| `media_type` | 媒体, 媒体类型 | ⚠️ **中文映射必须先读取** `./enums/media_type_cn_mapping.md`。⚠️ 用户提到"信息流"、"商店搜索"、"商店推荐"、"软体"、"联盟"等业务分类时，**必须先读该枚举文档的"媒体分类概念说明"章节**确认查询条件（部分分类需要配合 `tag_id` 使用，不能仅靠 `media_type`） |
| `sale_industry` | 销售自定义行业 | ⚠️ **中文映射必须先读取** `./enums/xirang_ad_effect_enum_sale_industry.md`。⚠️ **关联不到外部 DSP 收入**，如有需要请参考低频词典的内外联动销售一、二级行业 |
| `agent_id` | 二代 | ⚠️ **中文映射必须先读取** `./enums/xirang_ad_effect_enum_agent_id.md`。⚠️ **"二代 ≠ 核代"** |
| `core_id` | 核代 | ⚠️ **中文映射必须先读取** `./enums/xirang_ad_effect_enum_core_id.md` |
| `campaign_id` | 广告计划, 计划ID | 如 `44769084` |
| `oper_industry_level2` | 运营二级自定义行业 | ⚠️ **中文映射必须先读取** `./enums/xirang_ad_effect_enum_oper_industry_level2.md`。⚠️ **提到"行业"时，若无特殊说明，默认使用本字段** |
| `ad_id` | adId, 广告ID | 如 `44769188` |
| `effect_region` | 效果区域 | ⚠️ **中文映射必须先读取** `./enums/xirang_ad_effect_enum_effect_region.md` |
| `deep_target_conv_type` | 深层目标转化类型 | ⚠️ **中文映射必须先读取** `./enums/xirang_ad_effect_enum_target_conv_type.md` |

---

## 二、高频指标字段

> **Z/J 后缀含义**：`_z` = 转化点归因，`_j` = 计费点归因。若无特殊说明，默认使用 `_z` 后缀版本。

| 字段名 | 中文名 | 类型 | 公式说明 |
|---|---|---|---|
| `fee_effect` | emi效果收入, 内部dsp消耗, 花费, 效果收入 | raw | emi现金+返券+现金Back+充值 |
| `total_fee_effect` | 效果总收入, 消耗 | derived | 效果收入+外部DSPRtb收入。⚠️ **若无特殊说明，"消耗"默认指本字段** |
| `billing_ratio_z` | 计费比(Z) | derived | emi效果收入 / 广告主价值(Z) |
| `cvr_bill_conv_z` | CVR_计费转化率(Z) | derived | 目标转化数(Z) / 计费数 |
| `target_conv_num_z` | 目标转化数(Z), 转化数, 目标转化 | raw | — |
| `target_conv_cost_z` | 实际转化成本(Z), 转化成本, CPA | derived | emi效果收入 / 目标转化数(Z) |
| `avg_target_cpa_conv_z` | 平均目标出价_转化(Z) | derived | 总计目标出价_转化(Z) / 目标转化数(Z) |
| `cvr_pcoc_z` | CVR pcoc(Z) | derived | 平均pcvrFix_计费点 / CVR扣费转化率(Z) |
| `view` | 计费曝光, 曝光, 曝光数 | raw | — |
| `active_z` | 自定义激活(Z), 激活数 | raw | — |
| `ecpm` | 实际eCPM, eCPM, 千次曝光收入 | derived | 1000 × (emi效果+品牌+外部Dsp) / 计费曝光。⚠️ **提到 eCPM 时优先使用本字段，`raw_ecpm` 仅在需要原始口径时使用** |
| `fee_dsp_rtb` | 外部DSPRtb收入, RTB收入 | raw | — |
| `active_cost_z` | 自定义激活成本(Z), 激活CPA | derived | emi效果收入 / 自定义激活(Z) |
| `avg_pcvrfix_bill` | 平均pcvrFix_计费点 | derived | 总计pcvrFix_计费点 / 计费数 |
| `register_cost_z` | 注册成本(Z) | derived | emi效果收入 / 自定义注册(Z) |
| `start_download` | 开始下载, 下载数 | raw | — |
| `register_num_z` | 自定义注册(Z), 注册数 | raw | — |
| `click` | 计费点击, 点击 | raw | — |
| `ctr_view_bill` | CTR_曝光计费率 | derived | 计费数 / 计费曝光 |
| `ctr_pcoc` | CTR pcoc | derived | avg_pctr_view / CTR曝光计费率 |
| `ctr` | CTR_曝光点击率, 曝光点击率, 点击率 | derived | 计费点击 / 计费曝光 |
| `fee_total` | 分成后总收入, 总收入 | derived | emi效果+品牌+外部Dsp+内部分成收入-内部分成支出 |

---

## 三、典型查询示例

### 基础查数

#### 1. 按计划分组（找掉量贡献最大的计划）

限定一个账户id后，按计划分组，4月1日对比3月31日，按emi效果收入指标计算两个日期的变化值（即`"sort_by": "fee_effect"，"sortFieldType": 1`），并按变化值升序（即`"direction": 0`），取top 50。同时查询这两个日期下的每个计划的效果收入、曝光、点击、点击率、目标转化数。

```json
{
  "time": {
    "start_time": "2026-04-01T00:00:00+08:00",
    "end_time": "2026-04-01T23:59:59+08:00",
    "compare": true,
    "comparison_start_time": "2026-03-31T00:00:00+08:00",
    "comparison_end_time": "2026-03-31T23:59:59+08:00"
  },
  "filters": { "customer_id": "1357652" },
  "split": { "group_by": "campaign_id", "top": 50, "sort_by": "fee_effect", "direction": 0, "sortFieldType": 1 },
  "measures": ["fee_effect", "view", "click", "ctr", "target_conv_num_z"]
}
```

#### 2. 时间趋势（按小时查看消耗走势）

限定一个广告id后，按小时分组，4月1日对比3月31日，按emi效果收入指标（即`"sort_by": "fee_effect"`）的4月1日当前值降序（即服务默认逻辑是`"direction": 1, "sortFieldType": 0`，），取top 24。同时查询这两个日期下的每个小时的效果收入、曝光、点击、点击率。

```json
{
  "time": {
    "start_time": "2026-04-01T00:00:00+08:00",
    "end_time": "2026-04-01T23:59:59+08:00",
    "compare": true,
    "comparison_start_time": "2026-03-31T00:00:00+08:00",
    "comparison_end_time": "2026-03-31T23:59:59+08:00"
  },
  "filters": { "ad_id": "400016661" },
  "split": { "group_by": "dt", "time_granularity": 3600, "top": 24 },
  "measures": ["view", "click", "fee_effect", "ctr"]
}
```

### 时间对比 vs 不对比的查询区别

#### 1. 用户可能询问大盘分析问题，不需做跨时间对比

- 场景举例：「看下大盘分媒体和广告位今天的消耗排名」
- 处理方式：不用做任何跨时间对比，即`"compare": false`。`split.group_by` 传字符串数组表达多维交叉，每行同时携带每个维度字段的值；`top` 是结果总行数上限（笛卡尔积截断），不是每个维度内的 Top N。


> 以下查询按效果收入指标（即`"sort_by": "fee_effect"`）的4月1日当前值降序（即服务默认逻辑是`"direction": 1, "sortFieldType": 0`）。同时查询这一天下的每个`媒体 × 广告位`组合的效果收入、曝光、点击、点击率。由于组合后行数多，因此取top 500

```json
{
  "time": {
    "start_time": "2026-04-01T00:00:00+08:00",
    "end_time": "2026-04-01T23:59:59+08:00",
    "compare": false
  },
  "split": { "group_by": ["media_type", "tag_id"], "top": 500, "sort_by": "fee_effect", "direction": 1, "sortFieldType": 0 },
  "measures": ["fee_effect", "view", "click", "ctr"]
}
```

<br />


#### 2. 需要时间对比时，要区分三种场景：


##### 2.1 掉量场景
- 场景举例：「看下大盘各媒体环比昨天掉量变化情况」
- 处理方式：`"sortFieldType": 3`，即按对比值（即昨天）排序。如果觉得候选对象太多（比如按广告id分组时），如果你希望精准列出变化最大的对象，则也可考虑并行另一组按变化值升序的查询（即`"direction": 0, "sortFieldType": 1` ）

```json
{
  "time": {
    "start_time": "2026-04-01T00:00:00+08:00",
    "end_time": "2026-04-01T23:59:59+08:00",
    "compare": true,
    "comparison_start_time": "2026-03-31T00:00:00+08:00",
    "comparison_end_time": "2026-03-31T23:59:59+08:00"
  },
  "split": { "group_by": "media_type", "top": 20, "sort_by": "fee_effect", "direction": 1, "sortFieldType": 3 },
  "measures": ["fee_effect", "view", "click", "ctr"]
}
```

##### 2.2 涨量场景
- 场景举例：「看下大盘各媒体环比昨天涨量变化情况」
- 处理方式：`"sortFieldType": 0`，即按当前值（即今天）排序。如果觉得候选对象太多（比如按广告id分组时），如果你希望精准列出变化最大的对象，则也可考虑并行另一组按变化值降序的查询（即`"direction": 1, "sortFieldType": 1` ）

```json
{
  "time": {
    "start_time": "2026-04-01T00:00:00+08:00",
    "end_time": "2026-04-01T23:59:59+08:00",
    "compare": true,
    "comparison_start_time": "2026-03-31T00:00:00+08:00",
    "comparison_end_time": "2026-03-31T23:59:59+08:00"
  },
  "split": { "group_by": "media_type", "top": 20, "sort_by": "fee_effect", "direction": 1, "sortFieldType": 0 },
  "measures": ["fee_effect", "view", "click", "ctr"]
}
```

##### 2.3 用户没有声明场景
- 场景举例：「看下大盘各媒体环比昨天消耗变化情况」
- 处理方式：`"sortFieldType": 0`，建议默认按当前值（即今天）排序。注意：但此时需明确告知用户你使用了当前值排序，用户有知情权，并拥有了下次要求按其他方式排序的选择权。

```json
{
  "time": {
    "start_time": "2026-04-01T00:00:00+08:00",
    "end_time": "2026-04-01T23:59:59+08:00",
    "compare": true,
    "comparison_start_time": "2026-03-31T00:00:00+08:00",
    "comparison_end_time": "2026-03-31T23:59:59+08:00"
  },
  "split": { "group_by": "media_type", "top": 20, "sort_by": "fee_effect", "direction": 1, "sortFieldType": 0 },
  "measures": ["fee_effect", "view", "click", "ctr"]
}
```



### split 参数说明

> ⚠️ **排序参数（`sort_by` / `direction` / `sortFieldType`）仅在 `split.group_by` 非空时影响结果**。无分组（聚合查询）时结果只有 1 行，排序参数无意义。

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `group_by` | string \| string[] | 无（不分组） | 下钻维度，传 `"dt"` 时须同时传 `time_granularity`。**支持数组多维交叉**：传 `["customer_id","target_conv_type"]` 等价于按多个维度笛卡尔组合分组，每行同时携带每个维度字段的值 |
| `top` | int | 50 | 返回行数上限，按 `sort_by` 的对应轴（由 `sortFieldType` 决定）按 `direction` 方向取前 N 行。**当 `group_by=dt` 时，必须根据时间范围和粒度动态计算 `top`，确保覆盖完整时间线**：小时级 = 时间范围小时数（如全天 = 24），5分钟级 = 时间范围分钟数 / 5（如全天 = 288），天级 = 天数。低值时段被 Top N 截断是常见误判来源 |
| `sort_by` | string | 优先 `total_fee_effect`（若在 measures 中），否则第一个 measure | 排序指标名，必须是本次查询 measures 中的字段 |
| `direction` | int | `1` | 排序方向：`1` = 降序；`0` = 升序 |
| `sortFieldType` | int \| string | `0` | 对比时的排序方式：`0` = 按当前值排（e.g.今天），`1` = 按变化值排（当前 − 对比， e.g. 今天-昨天），`2` = 变化率（e.g. (今天-昨天)/1），`3` = 对比值 (e.g.昨天）。 |
| `time_granularity` | int | 86402 | 仅 `group_by=dt` 时有效，见全局参考中的时间粒度编码表 |
