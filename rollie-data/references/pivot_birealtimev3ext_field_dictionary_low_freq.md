---
name: pivot-birealtimev3ext-field-dictionary-low-freq
description: query_pivot_birealtime_v3_ext（BIrealtimev3ext 实验分析看板）低频字段词典——算法侧实验分析不常用的 32 个维度（计划ID/账户ID/行业/开发者/机型标识等）和 50 个指标（原始计数、深层转化、pltv、激活留存、排序打分等）。仅当主词典查不到时使用。
---

# BIrealtimev3ext 实验分析看板 低频字段词典（query_pivot_birealtime_v3_ext）

> 本文档收录**算法侧实验分析不常用**的字段。算法实验分析的核心字段请查阅 `./pivot_birealtimev3ext_field_dictionary.md`。
>
> 这些字段在服务端查询模板中**均可正常查询**，只是不属于实验分析的默认关注范围。当用户明确问到这些字段（如深层转化、pltv、激活数、按计划/账户/行业下钻）时，从本文档取 canonical key。
>
> ⚠️ 与主词典一致的两条约定：① canonical key **大小写敏感**，必须原样传；② 本文档未收录的字段一律不存在于本看板，不要臆造。

## 维度词典（32 个）

| canonical_key | backend_field | UI 名称 | 中文常用说法 | 枚举值说明 |
| --- | --- | --- | --- | --- |
| `useCacheFlag` | `useCacheFlag` | `Use Cache Flag` | 是否缓存 | useCacheFlag=0 |
| `adProdType` | `adProdType` | `Ad Prod Type` | 广告产品类型 | |
| `appCategoryLvl1Id` | `appCategoryLvl1Id` | `App Category Lvl1 Id` | 应用一级分类ID | |
| `campaignId` | `campaignId` | `Campaign Id` | 计划ID, campaign | campaignId=400010224 |
| `categoryId` | `categoryId` | `Category Id` | 分类ID | |
| `convtype` | `convtype` | `Convtype` | 回传事件类型, 事件类型 | ⚠️ **中文映射必须先读取**`./enums/xirang_ad_effect_enum_target_conv_type.md`。|
| `customerId` | `customerId` | `Customer Id` | 账户，账户ID, 子账户 | customerId=1519472 |
| `deepTargetCovType` | `deepTargetCovType` | `Deep Target Cov Type` | 深层目标转化类型 | ⚠️ **中文映射必须先读取**`./enums/xirang_ad_effect_enum_target_conv_type.md`。 |
| `deliverDay` | `deliverDay` | `Deliver Day` | 广告下发日期 | deliverDay=20260311 |
| `developerId` | `developerId` | `Developer Id` | 开发者ID，联盟开发者ID | |
| `displayType` | `displayType` | `Display Type` | 展示类型 | |
| `emiRegion` | `emiRegion` | `Emi Region` | EMI区域 | |
| `freshAd` | `freshAd` | `Fresh Ad` | 新广告标记, 是否新广告 | ture代表新广告，false代表老广告 |
| `incrementalStatus` | `incrementalStatus` | `Incremental Status` | 增量智投状态 | `0`=关闭、`1`=增量模式、`2`=日常模式|
| `industryLevel1` | `industryLevel1` | `Industry Level1` | 效果一级行业 | `0`=其他、`2`=KA电商+LA电商、`3`=金融服务、`4`=工具+招聘、`5`=旅游 |
| `installed` | `installed` | `Installed` | 是否安装 | |
| `isApiBidding` | `isApiBidding` | `Is Api Bidding` | 是否API竞价 | |
| `isAutoOptimizationFlag` | `isAutoOptimizationFlag` | `Is Auto Optimization Flag` | 是否开启自动优化 | `0`=否、`1`=是 |
| `isZrlFlag` | `isZrlFlag` | `Is Zrl Flag` | 是否自然量 | `0`=否、`1`=是 |
| `keyActionThreshold` | `keyActionThreshold` | `Key Action Threshold` | 关键行为阈值 | |
| `keyActionType` | `keyActionType` | `Key Action Type` | 关键行为类型 | keyActionType=0 |
| `operLevel1Industry` | `operLevel1Industry` | `Oper Level1 Industry` | 运营一级行业、运营一级自定义行业 | `IAA买量类`、`商品交易类`、`线索类`、`增值服务类`、`内投`、`闭环变现类`、`其他` |
| `operLevel2Industry` | `operLevel2Industry` | `Oper Level2 Industry` | 运营二级行业、运营二级自定义行业 | ⚠️ **中文映射必须先读取** `./enums/xirang_ad_effect_enum_oper_industry_level2.md`。⚠️ **提到"行业"时，若无特殊说明，默认使用本字段**  |
| `scenarioTypeFlag` | `scenarioTypeFlag` | `Scenario Type Flag` | 投放场景 | `0`=日常投放、`1`=增量投放 |
| `seq` | `seq` | `Seq` | seq | seq=0 |
| `strategyTrafficTag` | `strategyTrafficTag` | `Strategy Traffic Tag` | 策略流量标签 | |
| `trackingType` | `trackingType` | `Tracking Type` | 追踪类型, 归因类型 | trackingType=1 |
| `typeName` | `typeName` | `Type Name` | 类型名称 | |
| `uTrafficType` | `uTrafficType` | `UTraffic Type` | 流量类型 | |
| `uaId` | `uaId` | `Ua Id` | UA ID, uaid, 联盟应用id | uaId=0 |
| `unionSoure` | `unionSoure` | `Union Soure` | 联盟渠道来源名称, 联盟来源 | |
| `upId` | `upId` | `Up Id` | UP ID, upid, 联盟位置id | upId=unknown |

## 指标词典（50 个）

> `raw` 表示直接求和——含 canonical_key 与 backend 字段名不同时的**别名求和**（如 `totalPltv = sum(pltv)`，行为上仍是原样求和）。
> `derived` 表示不是简单求和，而是比值、平均值、计数或组合表达式。
>
> ⚠️ **可加性与 raw/derived 无关，判据是公式里有没有除法。** `view`、`click`、`advv`、`totalFee`（= `fee + feeRtb`）、`count` 这类**跨行可以相加**；`ecpm`、`ctr1`、`cvr`、`ctr_pcoc`、`cvr_pcoc`、`billingRatio`、`totalPctr` 这类含除法的比值/平均值**跨行不可相加**——多维拆分后要合并，必须回到分子分母重算，**不能把各行的比值直接相加或求算术平均**。
>
> 其中 `fee`、`feeRtb`、`billCd`、`targetConvNum`、`convNum` 等**原始计数字段**是主词典派生指标的分子分母（如 `totalFee = fee + feeRtb`、`ctr1 = billCd*100/view`、`cvr = targetConvNum*100/billCd`）。它们可以直接查，但算法侧实验分析一般直接用主词典的派生指标，不必自己拼。

| canonical_key | UI 名称 | 中文常用说法 | 类型 | 样例值 |
| --- | --- | --- | --- | --- |
| `targetConvNum` | `targetConvNum(目标转化数)` | 目标转化数 | raw | 10966350 |
| `fee` | `fee(效果收入)` | 消耗, 花费, 收入, emi效果收入 | raw | 26124963.05549952 |
| `count` | `Count` | 条数, 记录数 | derived | 5338877778 |
| `feeRtb` | `feeRtb(外部DSPRtb收入)` | RTB收入, 外部DSPRtb收入 | raw | 12599824.392585797 |
| `convNum` | `convNum(回传转化数)` | 回传转化数, 回传事件数 | raw | 75761231 |
| `endDownload` | `endDownload(下载成功)` | 下载完成数, 下载成功 | raw | 16897746 |
| `endInstall` | `endInstall(安装成功)` | 安装完成数, 安装成功 | raw | 16631641 |
| `startInstall` | `startInstall` | 开始安装 | raw | — |
| `cpc` | `cpc(实际cpc)` | CPC, 单次点击成本 | derived | 0.5895462568004716 |
| `cpd` | `cpd(实际cpd)` | CPD, 单次下载成本 | derived | 2.0365351653617947 |
| `ctr` | `CTR(曝光点击率%)` | CTR, 点击率, CTR_曝光点击率 | derived | 1.7609817330679722 |
| `cvrFromDownload` | `cvrFromDownload(下载转化率%)` | 下载转化率 | derived | 398.4280386546751 |
| `cvrFromClick` | `cvrFromClick(点击转化率%)` | 点击转化率 | derived | 115.33891620844577 |
| `convCost` | `convCost(转化成本)` | 回传转化事件成本 | derived | 0.34483287442226906 |
| `targetConvCost` | `targetConvCost(实际转化成本)` | 目标转化成本, 实际转化成本 | derived | 2.3822842655486576 |
| `totalTargetCpa` | `targetCpa(平均目标出价_转化)` | 目标CPA, 平均目标出价, 平均目标出价_转化 | derived | 2.419445280390451 |
| `totalTargetCpaView` | `targetCpaView(平均目标出价_曝光)` | 平均目标出价_曝光 | derived | 40.823525591834674 |
| `totalDeepTargetCpaView` | `totalDeepTargetCpaView` | 深层目标出价_曝光 | raw | — |
| `billCd` | `billCd` | 计费量, Bill Cd, 计费数 | raw | 32919967 |
| `pDeepCvrBd` | `pDeepCvrBd` | 预估deepcvr(计费点) | raw | — |
| `pDeepCvrFixBd` | `pDeepCvrFixBd` | 预估deepcvrfix(计费点) | raw | — |
| `totalPDeepCvrFromBd` | `totalPDeepCvrFromBd(预估deepcvrFix_计费点)` | 计费点预估deepcvr总量, 总计pdeepcvr_计费点 | derived | 0.05742801141140777 |
| `totalPDeepCvrFixFromBd` | `totalPDeepCvrFixFromBd(预估deepcvr_计费点)` | 计费点预估deepcvrfix总量, 总计pdeepcvrFix_计费点 | derived | 0.05877246711515639 |
| `pDeepcvrFix` | `pDeepcvrFix(预估deepcvrfix在浅层目标转化事件上的平均)` | 预估deepcvrfix, 平均pdeepcvrFix_浅层转化点 | derived | 548.1277559618312 |
| `totalPdeepcvr` | `pdeepcvr(预估deepcvr)` | 预估DeepCVR | derived | 579.1557399160313 |
| `totalPcvrFromClick` | `pcvrFromClick(预估cvrfromclick)` | 预估点击转化率 | derived | 0.1001864625267299 |
| `totalPcvrFromDownload` | `pcvrFromDownload(预估cvrfromdownload)` | 预估下载转化率 | derived | 0.0981242499769017 |
| `totalPcvrFixedFromClick` | `pcvrFixedFromClick(预估cvrFixedFromClick)` | 预估CVR Fixed(点击口径) | derived | — |
| `totalPcvrFixedFromDownload` | `pcvrFixedFromDownload(预估cvrFixedFromdownload)` | 预估CVR Fixed(下载口径) | derived | — |
| `pltv` | `pltv(预估变现金额在计费事件上的平均)` | 预估LTV | derived | 0.011149922268222248 |
| `pltvFixed` | `pltvFixed(预估变现金额fixed在计费事件上的平均)` | 预估LTV Fixed | derived | 0.011237664451908476 |
| `pdeepltv` | `pdeepltv(预估深层变现金额/次数在浅层目标转化事件上的平均)` | 预估深层LTV | derived | 0.7540346760391322 |
| `pdeepltvFix` | `pdeepltvFix(预估深层变现金额/次数fix在浅层目标转化事件上的平均)` | 预估深层LTV Fix | derived | 0.6388068169070426 |
| `totalPltv` | `totalPltv(预估变现金额的总计)` | 总LTV | raw | 367055.07312244154 |
| `totalPltvFixed` | `totalPltvFixed(预估变现金额fixed的总计)` | 总LTV Fixed | raw | 369943.5429139001 |
| `totalPdeepltv` | `totalPdeepltv(预估深层变现金额的总计)` | 总深层LTV | raw | 8269008.169581737 |
| `totalPdeepltvFix` | `totalPdeepltvFix(预估深层变现金额fixed的总计)` | 总深层LTV Fix | raw | 7005379.1365885455 |
| `avgEnginePecpm` | `avgEnginePecpm(内部竞价pecpm，rankScore在曝光上的平均)` | 内部竞价pecpm | derived | — |
| `rankScore` | `Rank Score` | 排序分 | raw | — |
| `profitRate` | `profitRate(利润率)` | 利润率 | derived | — |
| `experimentFeeTotal` | `experimentFeeTotal(分成前收入)` | 分成前收入 | derived | — |
| `rawWin` | `rawWin(竞胜数)` | 竞胜数 | raw | — |
| `externalAppReturnPriceView` | `externalAppReturnPriceView(开发者bidding收入)` | 开发者bidding收入 | raw | — |
| `unionExternalPrice` | `unionExternalPrice(ADX出价eCPM)` | ADX出价eCPM | raw | — |
| `active` | `Active` | 激活数 | raw | 12869415 |
| `dayActive` | `Day Active` | 当日激活 | raw | 9922573 |
| `day3Active` | `Day3 Active` | 3日激活 | raw | — |
| `newActive` | `New Active` | 新增激活 | raw | 6305398 |
| `newDayActive` | `New Day Active` | 当日新增激活 | raw | 5124279 |
| `total` | `Total` | 总量 | raw | 135****1809 |

## 备注

1. "UI 名称"优先取 Pivot 页面里实际看到的标签；`canonical_key` 是当前 skill 对外暴露给模型和脚本的标准键。
2. 具体公式见服务端查询模板 `birealtimev3ext.json` 的 `custom_expressions` 字段。
3. 查询构造方式、默认筛选、按实验层分流的指标、以及四步分析流程（输入检查 → 拉数算 diff → 检测异常 → 下钻归因），全部见主词典 `./pivot_birealtimev3ext_field_dictionary.md`，本文档只提供字段名。
