---
name: bi-realtime-field-dictionary
description: BI Realtime 字段中英文词典草稿，供自然语言问数与字段映射校对使用。
---


# BI Realtime 字段词典


当前状态：
- 默认指标：`view`、`click`、`startDownload`、`fee`、`targetConvNum`

## 维度词典
| canonical_key | backend_field | UI 名称 | 中文常用说法 | 枚举值说明 |
| --- | --- | --- | --- | --- |
| `time` | `__time` | `Time` | 时间, 时间维度 |  __time=2026-03-11T12:04:00.000Z |
| `sourceName` | `sourceName` | `sourceName` | 联盟渠道来源，流量来源 | sourceName=None |
| `productType` | `productType` | `productType` | 推广产品类型 | productType=2 |
| `adId` | `adId` | `Ad Id` | 广告ID, adid | adId=400498383 |
| `appId` | `appId` | `App Id` | 客户，应用， 应用ID, appid | appId=1562009，**查询本字段时必读此文档以获取appid的中文名！`./enums/top_appid_cn_mapping.md`** |
| `billingType` | `billingType` | `Billing Type` | 计费类型, 计费方式 | billingType=3 |
| `campaignId` | `campaignId` | `Campaign Id` | 计划ID, campaign | campaignId=400010224 |
| `convType` | `convType` | `Conv Type` | 回传事件类型, 事件类型 | convType=0 |
| `customerId` | `customerId` | `Customer Id` | 账户，账户ID, 子账户 | customerId=1519472 |
| `deepTargetConvType` | `deepTargetConvType` | `Deep Target Conv Type` | 深层目标转化类型 | deepTargetConvType=0 |
| `deliverDay` | `deliverDay` | `Deliver Day` | 广告下发日期 | deliverDay=20260311 |
| `developerName` | `developerName` | `Developer Name` | 联盟开发者名称 | developerName=None |
| `dpaType` | `dpaType` | `Dpa Type` | DPA类型 |  dpaType=0 |
| `dsp` | `dsp` | `Dsp` | DSP, 二级dsp | dsp=xiaomi.ocpa |
| `filterExpId` | `filterExpId` | `Filter Exp Id` | 过滤实验ID | filterExpId=None |
| `freshAd` | `freshAd` | `Fresh Ad` | 新广告标记, 是否新广告 | freshAd=false |
| `industryLevel1` | `industryLevel1` | `Industry Level1` | 效果一级行业 | industryLevel1=9 |
| `isAutoOptimizationFlag` | `isAutoOptimizationFlag` | `Is Auto Optimization Flag` | 是否开启自动优化 | isAutoOptimizationFlag=1 |
| `isPersonalizedClosed` | `isPersonalizedClosed` | `Is Personalized Closed` | 是否关闭个性化开关 | isPersonalizedClosed=false |
| `isZrlFlag` | `isZrlFlag` | `Is Zrl Flag` | 是否自然量 | isZrlFlag=0 |
| `keyActionType` | `keyActionType` | `Key Action Type` | 关键行为类型 | keyActionType=0 |
| `logEnv` | `logEnv` | `Log Env` | 日志环境 | logEnv=C3, fee=13701144.997430028 |
| `mediaType` | `mediaType` | `Media Type` | 媒体类型 | mediaType=APP_STORE，**查询本字段时必读此文档以获取mediaType的中文名！`./enums/media_type_cn_mapping.md`**|
| `operLevel1Industry` | `operLevel1Industry` | `Oper Level1 Industry` | 运营一级行业 | operLevel1Industry=IAA买量类 |
| `operLevel2Industry` | `operLevel2Industry` | `Oper Level2 Industry` | 运营二级行业 | operLevel2Industry=SKA |
| `placementType` | `placementType` | `Placement Type` | PT |  placementType=0 |
| `rtaToken` | `rtaToken` | `Rta Token` | RTA Token | rtaToken=unknown |
| `scenarioTypeFlag` | `scenarioTypeFlag` | `Scenario Type Flag` | 投放场景 | scenarioTypeFlag=0 |
| `seq` | `seq` | `Seq` | seq | seq=0, fee=19007673.336879753 |
| `tagId` | `tagId` | `Tag Id` | 广告位ID, 广告位, tagid | tagId=1.24.4.12 |
| `targetConvType` | `targetConvType` | `Target Conv Type` | 目标转化类型 | targetConvType=1 |
| `trackingType` | `trackingType` | `Tracking Type` | 追踪类型, 归因类型 | trackingType=1 |
| `uaId` | `uaId` | `Ua Id` | UA ID, uaid, 联盟应用id | uaId=0 |
| `upId` | `upId` | `Up Id` | UP ID, upid, 联盟位置id | upId=unknown |
| `useCacheFlag` | `useCacheFlag` | `Use Cache Flag` | 是否缓存 | useCacheFlag=0 |

# 转化分析规范（盛总 2026-03-16 确认）

1. **分转化目标时，必须用 `targetConvType` 维度**，不是 `convType`
2. **排除以下 targetConvType**，这些均为 ROI 转化目标，目标转化数无业务意义，不得纳入统计：
   - `10049`
   - `10022`
   - `10056`
   - （规则：所有 ROI 转化目标的 targetConvNum 均不可看）
3. **指标分析顺序**：
   - 先分析 **ADVV（广告主价值）**
   - 再分析 **targetConvNum（目标转化数，已排除上述 ROI 类型）**


## 指标词典

| canonical_key | UI 名称 | 中文常用说法 | 类型 | 样例值 |
| --- | --- | --- | --- | --- |
| `targetConvNum` | `targetConvNum` | 目标转化数 | raw | 10966350 |
| `fee` | `fee` | 消耗, 花费, 收入, emi效果收入 | raw | 26124963.05549952 |
| `startDownload` | `startDownload` | 开始下载 | raw | 19015035 |
| `click` | `click` | 点击, 计费点击 | raw | 65685749 |
| `view` | `view` | 曝光 | raw | 3730064189 |
| `count` | `Count` | 条数, 记录数 | raw | 5338877778 |
| `query` | `query(请求)` | 请求数 | raw | 7646322296 |
| `delivery` | `delivery(填充)` | 下发数, 填充数 | raw | 4391317148 |
| `rawView` | `rawView(原始曝光)` | 原始曝光 | raw | 4741377539 |
| `rawClick` | `rawClick(原始点击)` | 原始点击 | raw | 78552881 |
| `rawStartDownload` | `rawStartDownload(原始开始下载)` | 原始开始下载 | raw | 21249703 |
| `endDownload` | `endDownload(下载成功)` | 下载完成数, 下载成功 | raw | 16897746 |
| `endInstall` | `endInstall(安装成功)` | 安装完成数, 安装成功 | raw | 16631641 |
| `totalFee` | `totalFee(总收入)` | 总收入, 总消耗 | derived | 38724787.448085316 |
| `feeRtb` | `feeRtb(外部DSPRtb收入)` | RTB收入, 外部DSPRtb收入 | raw | 12599824.392585797 |
| `biddingFee` | `BiddingFee(竞价收入)` | 竞价收入 | raw | 210957.5178700028 |
| `convNum` | `convNum(回传转化数)` | 回传转化数, 回传事件数 | raw | 75761231 |
| `ocpxConvNum` | `ocpxConvNum(明ocpx回传转化数)` | OCPX回传转化数 | raw | 7931666 |
| `pDeepcvrFix` | `pDeepcvrFix(预估deepcvrfix在浅层目标转化事件上的平均)` | 预估deepcvrfix, 平均pdeepcvrFix_浅层转化点 | derived | 548.1277559618312 |
| `ecpm` | `ECPM(实际ecpm)` | ECPM, 千次曝光收入 | derived | 10.381801890242302 |
| `rpm` | `rpm` | RPM | derived | 5.064498454157929 |
| `cpc` | `cpc(实际cpc)` | CPC, 单次点击成本 | derived | 0.5895462568004716 |
| `cpd` | `cpd(实际cpd)` | CPD, 单次下载成本 | derived | 2.0365351653617947 |
| `clickFilterRatio` | `clickFilterRatio(点击过滤比例)` | 点击过滤比例 | derived | 0.16380216532096384 |
| `ctr` | `CTR(曝光点击率%)` | CTR, 点击率, CTR_曝光点击率 | derived | 1.7609817330679722 |
| `cvr` | `cvr(扣费转化率%)` | CVR, 转化率, CVR_计费转化率 | derived | 33.31215368472271 |
| `cvrFromDownload` | `cvrFromDownload(下载转化率%)` | 下载转化率 | derived | 398.4280386546751 |
| `cvrFromClick` | `cvrFromClick(点击转化率%)` | 点击转化率 | derived | 115.33891620844577 |
| `convCost` | `convCost(转化成本)` | 回传转化事件成本 | derived | 0.34483287442226906 |
| `ocpxConvCost` | `ocpxConvCost(明ocpx回传转化成本)` | OCPX转化成本 | derived | 3.2937548121037272 |
| `targetConvCost` | `targetConvCost(实际转化成本)` | 目标转化成本, 实际转化成本 | derived | 2.3822842655486576 |
| `targetCpa` | `targetCpa(平均目标出价_转化)` | 目标CPA, 平均目标出价, 平均目标出价_转化 | derived | 2.419445280390451 |
| `targetCpaView` | `targetCpaView(平均目标出价_曝光)` | 曝光口径目标CPA | derived | 40.823525591834674 |
| `iAARevenue24h` | `iAARevenue24h(24小时变现金额)` | 24小时变现金额 | raw | 502959.18462999986 |
| `iAARoi24h` | `iAARoi24h(24小时变现ROI)` | 24小时变现ROI | derived | 0.019252053431100365 |
| `advv` | `advv(广告主价值)` | 广告主价值 | raw | 24390731.819325544 |
| `pPrice` | `pPrice(调价pPrice)` | 调价PPrice, 平均pPrice_计费点 | derived | 0.796704839225375 |
| `iAAuv24h` | `iAAuv24h(24小时变现用户数)` | 24小时变现用户数 | raw | 1713057 |
| `iAAarpu24h` | `iAAarpu24h(24小时变现ARPU)` | 24小时变现ARPU | derived | 0.2936032978645777 |
| `billingRatio` | `billingRatio(计费比%)` | 计费比 | derived | 107.11020583154415 |
| `totalPDeepCvrFromBd` | `totalPDeepCvrFromBd(预估deepcvrFix_计费点)` | 计费点预估deepcvr总量, 总计pdeepcvr_计费点 | derived | 0.05742801141140777 |
| `totalPDeepCvrFixFromBd` | `totalPDeepCvrFixFromBd(预估deepcvr_计费点)` | 计费点预估deepcvrfix总量, 总计pdeepcvrFix_计费点 | derived | 0.05877246711515639 |
| `ctrViewCostRate` | `ctrViewCostRate(CTR曝光扣费率%)` | 曝光扣费率, CTR_曝光扣费率 | derived | 0.8825576540232563 |
| `pctr` | `pctr(预估ctr)` | 预估CTR | derived | 0.02428264958303468 |
| `pcvr` | `pcvr(预估cvr)` | 预估CVR | derived | 0.15762199977948615 |
| `pcvrFixed` | `pcvrFixed(预估cvrfixed)` | 预估CVR Fixed | derived | 0.15852903942098204 |
| `pltv` | `pltv(预估变现金额在计费事件上的平均)` | 预估LTV | derived | 0.011149922268222248 |
| `pltvFixed` | `pltvFixed(预估变现金额fixed在计费事件上的平均)` | 预估LTV Fixed | derived | 0.011237664451908476 |
| `pdeepcvr` | `pdeepcvr(预估deepcvr)` | 预估DeepCVR | derived | 579.1557399160313 |
| `pcvrFromClick` | `pcvrFromClick(预估cvrfromclick)` | 预估点击转化率 | derived | 0.1001864625267299 |
| `pcvrFromDownload` | `pcvrFromDownload(预估cvrfromdownload)` | 预估下载转化率 | derived | 0.0981242499769017 |
| `pdeepltv` | `pdeepltv(预估深层变现金额/次数在浅层目标转化事件上的平均)` | 预估深层LTV | derived | 0.7540346760391322 |
| `pdeepltvFix` | `pdeepltvFix(预估深层变现金额/次数fix在浅层目标转化事件上的平均)` | 预估深层LTV Fix | derived | 0.6388068169070426 |
| `cvr_pcoc` | `cvr_pcoc(pcvrfixed/cvr扣费转化率)` | CVR PCOC | derived | 0.47588949343039644 |
| `ctr_pcoc` | `ctr_pcoc(预估ctr/CTR曝光扣费率)` | CTR PCOC | derived | 2.7513952739902034 |
| `active` | `Active` | 激活数 | raw | 12869415 |
| `adReturn` | `adReturn` | 广告返回 | raw | 0 |
| `billCd` | `billCd` | 计费量, Bill Cd, 计费数 | raw | 32919967 |
| `dayActive` | `dayActive` | 当日激活 | raw | 9922573 |
| `newActive` | `newActive` | 新增激活 | raw | 6305398 |
| `newDayActive` | `newDayActive` | 当日新增激活 | raw | 5124279 |
| `pDeepCvrFixRaw` | `pDeepCvrFix` | 原始pDeepCvrFix | raw | 66903981483.92394 |
| `total` | `Total` | 总量 | raw | 13561221809 |
| `totalPcvrFromClick` | `totalPcvrFromClick` | 总预估点击转化率 | raw | 6580822.830728686 |
| `totalPcvrFromDownload` | `totalPcvrFromDownload` | 总预估下载转化率 | raw | 1865836.047659535 |
| `totalPdeepltv` | `totalPdeepltv` | 总深层LTV | raw | 8269008.169581737 |
| `totalPdeepltvFix` | `totalPdeepltvFix` | 总深层LTV Fix | raw | 7005379.1365885455 |
| `totalPltv` | `totalPltv` | 总LTV | raw | 367055.07312244154 |
| `totalPltvFixed` | `totalPltvFixed` | 总LTV Fixed | raw | 369943.5429139001 |

## 备注

1. 这里的”UI 名称”优先取页面里实际看到的标签；”canonical_key” 是当前 skill 对外暴露给模型和脚本的标准键。
2. `derived` 表示该指标不是简单 `sum(main.$field)`，而是比值、平均值或组合表达式。
3. 如果你后续改这份词典，优先改”中文常用说法”这一列；真正影响运行的是模板 JSON 里的 `canonical_key`、`measure_aliases`、`dimension_aliases`。


## 示例查询

### Phase 1 — 维度下钻（定位掉量对象）

按 `campaignId` / `adId` / `tagId` 逐层 group_by，核心指标为 `fee`，辅助 `totalFee`、`view`、`click`。

```json
{
  “time”: {
    “start_time”: “2026-03-01T00:00:00+08:00”,
    “end_time”: “2026-03-01T08:00:00+08:00”,
    “compare”: true
  },
  “filters”: { “customerId”: “123456” },
  “split”: { “group_by”: “campaignId” },
  “measures”: [“fee”, “totalFee”, “view”, “click”]
}
```

> 锁定计划后，将 `split.group_by` 换为 `adId`（并在 `filters` 加 `campaignId` 过滤），再换为 `tagId`（并加 `adId` 过滤），逐层下钻。

### Phase 2 — 漏斗收口验证（2.7 曝光后链路）

回到 bi_realtime 验证漏斗异常与最终曝光/点击/消耗/转化的一致性，measures 覆盖全链路。

```json
{
  “time”: {
    “start_time”: “2026-03-01T00:00:00+08:00”,
    “end_time”: “2026-03-01T08:00:00+08:00”,
    “compare”: true
  },
  “filters”: { “adId”: “400016661”, “tagId”: “1.11.t.1” },
  “measures”: [“fee”, “totalFee”, “view”, “click”, “targetConvNum”, “ecpm”, “ctr”, “cvr”, “cvr_pcoc”, “ctr_pcoc”]
}
```