---
name: pivot-search-term-field-dictionary
description: query_pivot_search_term（SearchTermV2 搜索词看板）字段词典，供传参前确认字段名、中文含义与枚举值使用
---

# SearchTermV2 搜索词看板（query_pivot_search_term）

## 背景与定位

小米商店消耗 = **搜索位** + **非搜索位**。

`xirang_ad_effect`（息壤效果看板）最细只能拆到广告位层级，__无法查看搜索词粒度的数据__。当诊断对象是搜索位时，息壤只能告诉你"哪个广告位消耗掉了"，但无法回答"是哪个搜索词的请求/曝光/消耗变了"。

SearchTermV2 填补了这个缺口——它可以 **by 搜索词** 查看请求、曝光、点击、消耗、转化和预估指标，也可以 by 搜索词查看请求变化趋势。

**典型诊断路径**：

```
xirang_ad_effect 定位到搜索位有问题
  → SearchTermV2 by query 下钻，定位具体搜索词
    → 确认是请求量掉了还是效率（CTR/CVR）掉了
```

**支持查询的搜索位广告位**：

| tagId | 中文名 |
|---|---|
| `1.24.4.12` | 应用商店-搜索sug-应用下载 |
| `1.24.4.15` | 应用商店-搜索结果页-应用下载 |
| `1.24.4.129` | 应用商店-搜索结果页-精准量 |
| `1.24.4.11` | 应用商店-搜索结果页-下载推荐-应用下载 |
| `1.24.4.75` | 应用商店-搜索结果页-游戏分发 |
| `1.24.4.14` | 应用商店-搜索结果页from热词-应用下载 |
| `1.24.4.130` | 应用商店-搜索sug-自然量控量 |
| `1.24.4.76` | 应用商店-搜索结果页富媒体-游戏分发 |

> 更多广告位中文名 → `./enums/xirang_ad_effect_enum_tag_id.md`

数据源：Druid 集群 `SearchTermV2` datacube，通过 `http://pivot.olap.srv` 查询。

参数风格：canonical 字段使用 SearchTermV2 原始 **camelCase** 字段；常用 snake_case 可通过 server alias 自动映射。

默认指标：`count`、`request`、`view`、`pctr`

---


数据源共 36 个维度。下表覆盖全部维度，诊断常用维度标 ★。

| canonical_key | backend_field | UI 名称 | 中文常用说法 | 枚举值/说明 |
|---|---|---|---|---|
| `time` | `__time` | `Time` | 时间维度、时间 | Druid `__time` 字段，格式 `2026-03-11T12:04:00.000Z` |
| ★ `query` | `query` | `Query` | 搜索词、关键词、query | 真实搜索词字段，如 "快手"、"千问" |
| ★ `adId` | `adId` | `adId` | 广告ID、adid | 如 `400498383` |
| ★ `appId` | `appId` | `App Id` | 客户，应用， 应用ID, appid | appId=1562009， ⚠️ **中文名映射必须先读取** `./enums/top_appid_cn_mapping.md`|
| ★ `tagId` | `tagId` | `tagId` | 广告位ID、广告位、tagid | 搜索词看板仅覆盖搜索位，如 `1.24.4.12`（搜索sug）, `1.24.4.15`（搜索结果页）, `1.24.4.129`（精准量）。完整列表见上方「支持查询的搜索位广告位」。 |
| ★ `mediaType` | `mediaType` | `mediaType` | 媒体类型 | `APP_STORE` |
| ★ `dsp` | `dsp` | `dsp` | DSP、二级dsp | 如 `xiaomi.ocpa` |
| ★ `campaignId` | `campaignId` | `campaignId` | 计划ID、campaign | 如 `400010224` |
| ★ `customerId` | `customerId` | `Customer Id` | 账户，账户ID, 子账户 | customerId=1519472 |
| ★ `billingType` | `billingType` | `billingType` | 计费类型, 计费方式 | `0`=OTHER、`1`=CPM、`2`=CPC、`3`=CPD、`4`=SCHEDULER。 |
| ★ `industryLevel1` | `industryLevel1` | `industryLevel1` | 效果一级行业, 一级行业 | `0`=其他、`2`=KA电商+LA电商、`3`=金融服务、`4`=工具+招聘、`5`=旅游。 |
| ★ `industryLevel2` | `industryLevel2` | `industryLevel2` | 效果二级行业, 二级行业 | `0`=其他、`14`=单品电商、`15`=其他、`16`=保险、`17`=股票基金。 |
| ★ `convType` | `convType` | `convType` | 回传事件类型、转化类型 |  ⚠️ **中文映射必须先读取**`./enums/xirang_ad_effect_enum_target_conv_type.md`。  |
| ★ `targetConvType` | `targetConvType` | `targetConvType` | 目标转化类型 |  ⚠️ **中文映射必须先读取**`./enums/xirang_ad_effect_enum_target_conv_type.md`。⚠️ **提到"转化类型"时，若无特殊说明，默认使用本字段**  |
| ★ `deepTargetConvType` | `deepTargetConvType` | `deepTargetConvType` | 深层目标转化类型 | ⚠️ **中文映射必须先读取** `./enums/xirang_ad_effect_enum_target_conv_type.md`  |
| `seq` | `seq` | `Seq` | seq | seq=0, fee=19007673.336879753 |
| ★ `freshAd` | `freshAd` | `freshAd` | 新广告标记、是否新广告 | `true`=新广告, `false`=非新广告 |
| ★ `isPersonalizedClosed` | `isPersonalizedClosed` | `Is Personalized Closed` | 是否关闭个性化开关 | isPersonalizedClosed=false |
| `displayType` | `displayType` | `displayType` | 版位, 展示类型 | `0`=（空）、`2`=视频、`4`=焦点图、`6`=插屏、`8`=应用商店。 |
| `firstNaturalAppId` | `firstNaturalAppId` | `firstNaturalAppId` | 首个自然应用ID | 如 `1562009` |
| `device` | `device` | `device` | 设备类型 | `平板`=平板、`手机`=手机、`unknown`=unknown。 |
| ★ `guyuFilterReason` | `guyuFilterReason` | `guyuFilterReason` | Guyu过滤原因、精排过滤原因 | 与 `guyu_stat` 看板的 `filterReason` 取值一致 |
| `keyActionType` | `keyActionType` | `keyActionType` | 关键行为类型 | 如 `0`=无关键行为 |
| `layer20` | `layer20` | `expLayer20` | 实验层20 | A/B 实验分层标识 |
| `layer21` | `layer21` | `expLayer21` | 实验层21 | A/B 实验分层标识 |
| `layer25` | `layer25` | `expLayer25` | 实验层25 | A/B 实验分层标识 |
| `layer26` | `layer26` | `expLayer26` | 实验层26 | A/B 实验分层标识 |
| `layer34` | `layer34` | `expLayer34` | 实验层34 | A/B 实验分层标识 |
| `layer35` | `layer35` | `expLayer35` | 实验层35 | A/B 实验分层标识 |
| `adExpId1` | `adExpId1` | `adExpId1` | 广告实验ID1 | 广告级 A/B 实验标识 |
| `adExpId2` | `adExpId2` | `adExpId2` | 广告实验ID2 | 广告级 A/B 实验标识 |
| `adExpId3` | `adExpId3` | `adExpId3` | 广告实验ID3 | 广告级 A/B 实验标识 |
| `adExpId4` | `adExpId4` | `adExpId4` | 广告实验ID4 | 广告级 A/B 实验标识 |
| ★ `isPreciseQuery` | `isPreciseQuery` | `isPreciseQuery` | 是否精准搜索词 | `true`=精准匹配, `false`=非精准匹配 |
| `deliverDate` | `deliverDate` | `deliverDate` | 广告下发日期 | 如 `20260311` |
| `naturalReplace` | `naturalReplace` | `Natural Replace` | 自然量替换标记 | `true`/`false`，自然量替换相关 |

---

## 指标词典

数据源共 27 个指标。`raw`=直接 `sum`，`derived`=比值/组合表达式。

| canonical_key | UI 名称 | 中文常用说法 | 类型 | 公式摘要 |
|---|---|---|---|---|
| ★ `count` | `Count` | 总量、记录数、条数 | raw | `sum(total)` |
| ★ `request` | `request` | 请求数 | raw | `sum(request)` |
| ★ `view` | `view` | 曝光、曝光数 | raw | `sum(view)` |
| ★ `pctr` | `pctr` | 平均pCTR、预估CTR | derived | `sum(totalPctr) / sum(view)` |
| `pctrRaw` | `pctrRaw` | 平均pCTR(Raw)、原始pCTR | derived | `sum(pctrRaw) / sum(view)` |
| ★ `ctr` | `ctr` | CTR, 点击率, CTR_曝光点击率 | derived | `sum(billNum) / sum(view)` |
| `pcvr` | `pcvr` | 平均pCVR、预估CVR | derived | `sum(pcvr) / sum(billNum)` |
| `pcvrFixed` | `pcvrFixed` | 平均pCVR Fixed、预估CVR(修正) | derived | `sum(totalPcvrFixed) / sum(billNum)` |
| `pDeepCvr` | `pDeepCvr` | 平均pDeepCVR、预估深层CVR | derived | `sum(pDeepCvr) / sum(targetConvNum)` |
| `pDeepCvrFixed` | `pDeepCvrFixed` | 平均pDeepCVR Fixed、预估深层CVR(修正) | derived | `sum(pDeepCvrFixed) / sum(targetConvNum)` |
| `cvr` | `cvr` | CVR, 转化率, CVR_计费转化率 | derived | `sum(targetConvNum) / sum(billNum)` |
| ★ `totalfee` | `totalfee` | 总消耗、总收入、总花费 | derived | `sum(fee) + sum(feeRtb)` |
| ★ `fee` | `fee` | 消耗, 花费, 收入, emi效果收入 | raw | `sum(fee)` |
| `feeRtb` | `feeRtb` | RTB收入, 外部DSPRtb收入 | raw | `sum(feeRtb)` |
| ★ `ecpm` | `ecpm` | eCPM、千次曝光收入 | derived | `(sum(fee)+sum(feeRtb))*1000 / sum(view)` |
| `discountEcpm` | `discountEcpm` | 折扣eCPM | derived | `sum(discountEcpm) / sum(view)` |
| `rankScore` | `rankScore` | 排序分、平均排序分 | derived | `sum(rankScore) / sum(view)` |
| `pPrice` | `pPrice` | 调价PPrice, 平均pPrice_计费点 | derived | `sum(pPrice) / sum(billNum)` |
| ★ `cpc` | `cpc` | CPC、单次点击成本 | derived | `(sum(fee)+sum(feeRtb)) / sum(click)` |
| `cpd` | `cpd` | CPD、单次下载成本 | derived | `(sum(fee)+sum(feeRtb)) / sum(startDownload)` |
| `billNum` | `billNum` | 计费数、计费量 | raw | `sum(billNum)` |
| ★ `click` | `click` | 点击、点击数、计费点击 | raw | `sum(click)` |
| ★ `startDownload` | `startDownload` | 开始下载、下载数 | raw | `sum(startDownload)` |
| ★ `targetConvNum` | `targetConvNum` | 目标转化数 | raw | `sum(targetConvNum)` |
| `convNum` | `convNum` | 回传转化数、回传事件数 | raw | `sum(convNum)` |
| ★ `billingRatio` | `billingRatio` | 计费比(%) | derived | `(sum(fee)+sum(feeRtb))*100 / sum(totalTargetCpa)` |
| `totalTargetCpa` | `totalTargetCpa` | 平均目标出价(转化口径) | derived | `sum(totalTargetCpa) / sum(targetConvNum)` |
| `totalPctr` | `totalPctr` | 总pCTR(分子) | raw | `sum(totalPctr)`。`pctr` 的分子，一般不单独使用 |
| `totalPcvrFixed` | `totalPcvrFixed` | 总pCVR Fixed(分子) | raw | `sum(totalPcvrFixed)`。`pcvrFixed` 的分子，一般不单独使用 |
| `ocpxConvNum` | `ocpxConvNum` | OCPX回传转化数 | derived | 按 `convType` 过滤后 `sum(convNum)`（公式复杂，见模板 JSON） |
| `ocpxConvCost` | `ocpxConvCost` | OCPX转化成本 | derived | `totalfee / ocpxConvNum`（公式复杂，见模板 JSON） |


---

## 典型查询示例

### 示例 1：搜索位消耗下跌，by 搜索词下钻定位根因

场景：`xirang_ad_effect` 发现搜索位 `1.24.4.15`（搜索结果页）消耗同比掉了 20%，需要查是哪些搜索词的消耗在跌。

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": true,
    "comparison_start_time": "2026-05-24T00:00:00+08:00",
    "comparison_end_time": "2026-05-25T00:00:00+08:00"
  },
  "filters": { "tagId": "1.24.4.15" },
  "split": { "group_by": "query", "top": 50, "sort_by": "totalfee" },
  "measures": ["count", "request", "view", "click", "totalfee", "ecpm", "ctr"]
}
```
> 先看 `totalfee` 环比变化最大的搜索词，再看这些词是 `request` 掉了（流量问题）还是 `ctr`/`ecpm` 掉了（效率问题）。

### 示例 2：某客户搜索位消耗下降，by 搜索词下钻

场景：某客户反馈搜索位整体消耗有明显下降，需要定位是哪些搜索词的消耗在跌。

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": true,
    "comparison_start_time": "2026-05-30T00:00:00+08:00",
    "comparison_end_time": "2026-05-31T00:00:00+08:00"
  },
  "filters": { "customerId": "1519472", "tagId": "1.24.4.12" },
  "split": { "group_by": "query", "top": 30, "sort_by": "totalfee" },
  "measures": ["totalfee", "view", "click", "targetConvNum", "cvr", "ctr"]
}
```

> 按 `query` 下钻后看 `totalfee` 环比下降最明显的搜索词，再结合 `cvr`/`ctr` 判断是效率问题还是流量结构变化。

### 示例 3：某客户在特定搜索位的搜索词请求量下降

场景：客户 `1519472` 在 `1.24.4.12`（搜索sug）的「千问」一词上消耗下跌，需要确认是该搜索词的请求量本身跌了还是效率跌了。

⚠️ **重要规则**：通过 `query` 维度查请求量时，**严禁在 filters 中带上 `customerId`、`adId`、`campaignId`、`appId` 等广告属性维度**——请求量属于流量入口指标，只与 `tagId` 和 `query` 相关，混入广告属性会错误过滤原始请求数据。这与 `query_request_info` 阶段「只支持 tagId/mediaType 过滤」的规则一致。

```json
{
  "time": {
    "start_time": "2026-06-01T00:00:00+08:00",
    "end_time": "2026-06-02T00:00:00+08:00",
    "compare": true,
    "comparison_start_time": "2026-05-24T00:00:00+08:00",
    "comparison_end_time": "2026-05-25T00:00:00+08:00"
  },
  "filters": { "tagId": "1.24.4.12", "query": "千问" },
  "split": { "group_by": ["tagId", "query"], "top": 30, "sort_by": "request" },
  "measures": ["count", "request", "view", "pctr"]
}
```

> `tagId + query` 交叉下钻可以看到该搜索位下各搜索词的请求分布变化。如果 `request` 没跌但消耗跌了 → 效率问题，需换示例 1/2 带 `totalfee`/`ctr`/`cvr` 的查询继续排查。如果 `request` 跌了 → 流量问题，上游搜索流量发生变化。


---

## 备注

1. canonical_key 以 `SearchTermV2.json`（Druid 数据源 schema）为基准，不能凭空捏造字段。
2. ★ 标记的维度/指标为诊断最常用项，优先级最高。
3. `derived` 指标不是简单 `sum`，而是比值/组合表达式；公式以 `pivot_search_term.json` 模板中的 `custom_expressions` 为准。
4. 枚举值来源优先从 `xirang_ad_effect_field_dictionary_low_freq.md` 和 `guyu_stat_field_dictionary.md` 交叉引用；若两处均无完整枚举则以 `SearchTermV2.json` schema 中的样例值为准。
5. 后续维护时优先补"中文常用说法"列和枚举值映射表，**不要修改 canonical_key**（否则会和模板 JSON 不一致导致查询失败）。
6. 字典、help 文本、server 模板 JSON 三者必须保持一致；改任何一处都需同步校验另外两处。
