---
name: pivot-birealtimev3ext-field-dictionary
description: query_pivot_birealtime_v3_ext（BIrealtimev3ext 实验分析看板）字段词典。服务算法研发排查实验数据——对比实验组与对照组在核心指标上的 diff、定位 pcoc 预估偏离、看内外部 DSP 与计费结构差异。含 53 个核心维度（42 个实验层 + 流量/对象/计费维度）与 15 个核心指标。低频字段见 pivot_birealtimev3ext_field_dictionary_low_freq.md。
---

# BIrealtimev3ext 实验分析看板（query_pivot_birealtime_v3_ext）

当前状态：
- 与旧 `query_bi_realtime`（`MiuiAdBiMinuteCubeNoExp`）并存，不替换；本看板专用于算法侧分析算法实验数据。
- 本文档只收录**实验分析核心字段**。用户问到深层转化、pltv、激活留存、或要按计划/账户/行业下钻时，翻 `./pivot_birealtimev3ext_field_dictionary_low_freq.md`。
## 算法侧分析指南

本看板服务算法研发排查实验数据。**分析主体是实验组相对对照组的 diff，不是罗列各组指标值。** 按下面四步顺序走。

⚠️ **本看板每发一次查询，就回显一次参数**（`time` / `filters` / `split` / `measures`）——第 2 步的两查、第 4 步的每一次下钻都算，**一次查询一份参数**，不能几次合并成一份、也不能省略。本看板一轮分析要发多次查询、且各次的筛选范围不同，用户只能靠参数回显确认每组数到底是什么口径。

### 1. 用户输入检查

**1.1 · 带且仅带一个 `expLayerN`，且必须同时进 `split.group_by`（必做）**
用户只给了实验号（如"2336628 和 2336629 两个实验"）却没说层号 → **停下来追问是哪一层**。不要猜，也不要拿 42 个层逐个去试。带了多个层 → 与用户确认以哪层为准。

⚠️ **只把 `expLayerN` 放在 `filters` 里是不够的**：`split.group_by` 不带它时，各实验组会被**合并成一行**返回，而且**不会报错**——diff 就没有数据可算。即使用户说"不用拆维度、就看两个实验总体差异"，`expLayerN` 也必须进 `group_by`，否则拿到的是两组之和。

**1.2 · 补默认筛选（必做）**
`isPersonalizedClosed=false` —— 个性化开关关闭时不走算法实验，数据不置信。无特殊说明时补齐。

**1.3 · CVR 实验结合转化目标（先与用户确认，再查）**
层号属于 CVR 算法层，且 `targetConvType` 既不在 `filters` 也不在 `split.group_by` 时，先告诉用户「CVR 算法实验建议结合转化目标查询」，确认确实不需要之后才查。

### 2. 拉数与计算 diff

**两查并行**（没有先后依赖）：A 看大盘、B 看用户指定查询。指标见各自表格，按表传。

**diff 算法（两步共用）**

对照组（基线）识别：数据里**没有**实验组/对照组的字段标识，所以按经验默认——**假设这批实验号里数值最小的那个是基线（对照组）**。按实验号数值大小判定，**不是**按用户提及的先后顺序。

⚠️ **这是假设，不是事实**（小号大概率是对照组，但有例外），所以：

- **在输出里用一处轻量标注点明它是假设就够了**，例如组名后加括号 `2336638（假设为对照组）`，或表下一行小字「基线按实验号大小假设，如有误告知即可重算」。**不要每次都写一长段解释**——点一次就行，反复声明反而干扰阅读。
- 但**不得完全省略**：不标注，用户就无从发现基线选错了。
- **用户已明确指出哪个是对照组时以用户为准**，此时不必再标"假设"。

设假设为基线的最小实验号为 A，其余为 B、C、D…，对每个指标算两种 diff：

| diff 类型 | 公式 | 作用 |
| --- | --- | --- |
| 绝对 diff | `B - A` | 看差异量级 |
| 百分比 diff | `B / A - 1` | 看差异幅度 |

**两种都要给**，缺一不可。多组时逐组对 A 求 diff（`C/A-1`、`D/A-1`…）。

⚠️ **指标本身就是百分比时（`ctr1`、`cvr`、`billingRatio`），两种 diff 的单位不同，输出必须分开写**：绝对 diff 单位是**百分点（pp）**，写成 `+0.04pp`；百分比 diff 是相对变化，写成 `+2.3%`。举例 `ctr1` 从 1.76% 变到 1.80%，两者差 50 倍，**都简写成 "diff" 会被严重误读**。

**2.1 · 查询 A：大盘（默认必做，与 2.2 并行）**

| 项 | 值 |
| --- | --- |
| 筛选 | 只保留 实验层 + `isPersonalizedClosed=false`——**用户附加的维度筛选（`dsp` / `appId` / `tagId` 等）一律剥离，也不加 `dspLevel1`** |
| 指标 | `view`、`ecpm`、`totalFee` |

看这个实验对大盘的整体影响。**即使用户只问某个 DSP 或某个 App，这一查也要做**——实验不能靠局部涨、而大盘被拖下去，那样并不正向。先看各组 `view` 有无 diff（有则实验执行性存疑），再用 `ecpm`、`totalFee` 定性。

⚠️ 外部 DSP 没有 `advv` 和 `billingRatio`，**本查不看这两个指标**。

**2.2 · 查询 B：用户指定查询（与 2.1 并行）**

**这一查以用户指定的范围为准**，筛选条件照带；用户没指定 DSP 时才用 `dspLevel1=effect` 兜底。再按实验层选指标组：

| 用户是否指定了 DSP | 怎么办 |
| --- | --- |
| 指定了 `dsp` 或 `dspLevel1` | **以用户为准，不要再叠加 `dspLevel1=effect`** |
| 没指定 | **兜底**加 `dspLevel1=effect`（只看内部 DSP） |

⚠️ 用户指定的是**外部** DSP（如 `tengxunrtb`）时再叠加 `dspLevel1=effect` 会**直接查空**（实测：单独筛 2.39 亿曝光，叠加后 0 行），而且不报错。

| 实验层 | 实验类型 | 指标 |
| --- | --- | --- |
| `expLayer20`、`expLayer66` | **CTR 算法实验** | `view`、`ecpm`、`totalFee`、`advv`、`ctr1`、`ctr_pcoc` |
| 其余各层 | **CVR 算法实验** | `view`、`ecpm`、`totalFee`、`advv`、`cvr`、`cvr_pcoc`、`billingRatio` |

用户点名了别的指标就在此基础上追加，不要替换掉这组指标。

**输出两组数时必须标清口径**，否则指标名相同、范围不同，很容易被当成同一份数据：写成 `大盘（实验层全量，未带你指定的筛选）` 和 `用户指定查询（dsp=xiaomi.ocpa）` 这种。

⚠️ 回显参数时特别注意：**"大盘"这个词本身不说明筛选条件**。用户自己指定过 `dsp`/`appId` 时，要能从 A 查的 `filters` 里一眼看出它**确实没带**他的筛选——否则两组数其实是同一份，大盘对照就白做了。

### 3. 检测值得关注的现象

对查询 A（大盘）与查询 B（用户指定查询）的结果**分别检测、分别给结论**——大盘一个结论，用户指定查询一个结论，不要混成一句。打上标签供第 4 步下钻。

**3.1 · 实验组间 diff 差异大（两查都做）**
任一指标的百分比 diff 超 **±0.5%**（正向负向都算）→ 打「值得下钻」。

- 查询 A（大盘）看：`view`、`ecpm`、`totalFee`
- 查询 B（用户指定查询）看：该实验类型在上表所列全部指标

⚠️ `view` 各组 diff 超 ±0.5% 还多一层含义：**实验分流可能不均、准确性存疑**；此前提下 diff 不可信，不得把指标差异归因为实验效果。

**3.2 · 达标值检查（只在2.2查询B 时做）**
`ctr_pcoc` / `cvr_pcoc` 是**纯数字比值**，达标 **0.8 – 1.2**：`< 0.8` 预估偏低（模型低估）、`> 1.2` 预估偏高（模型高估）。⚠️ **是 0.8–1.2，不是 80–120**——按 80–120 判会把几乎所有正常值误判成严重低估。

`billingRatio` 是**百分比**，达标 **80 – 120**：`< 80` 成本偏低、`> 120` 成本偏高。⚠️ 与 pcoc 口径不同，**不要混用同一套阈值**。

⚠️ 这两类指标外部 DSP 都没有。所以**查询 A（大盘）不做本项检查**；查询 B 若用户指定的是外部 DSP，也不做。

**打标签时要落到维度值上。** 本次查询已按某维度拆过的，直接点名**是哪个维度值**异常（如「`mediaType=信息流` 的 `ctr_pcoc`=1.42 越界」）；只有总体一行、没拆维度的，标签就停在指标级（如「总体 `ctr_pcoc`=1.35 越界」），由第 4 步给下钻建议去定位到维度值。

**第 3 步的内容需要与第 2 步的内容放在一起输出。**

### 4. 下钻归因

**第 3 步打的两类标签都要下钻，一类都不能漏**：3.1 diff 差异大、3.2 达标值越界。

第 3 步只能告出**哪个指标有问题**，说不出**问题在哪**。需要进一步下钻，把「哪个指标有问题」变成「问题集中在哪个维度值」。

按以下步骤推进：

1. 先把第 3 步已经找到的异常范围作为筛选条件传到 `filters` 里。
2. 选择下表的核心业务概念进行下钻，可根据实际情况尽量 cover 全维度主题，但**最多都往下钻一层就结束**。输出结果按消耗降序，同时报告下钻各单元的贡献度（**可加指标**可以直接计算某枚举除以整体的比例；**不可加指标**如计费比等无法直接计算贡献度，直接 highlight 超标现象即可，可加性见指标词典的说明）。之后**询问用户是否继续更深入下钻**。

| 维度主题 | 下钻路径（只能从粗到细钻，不能反方向） |
| --- | --- |
| 流量 | `mediaType` → `tagId`（媒体大类语义见 `../bizknowledge/traffic_knowledge.md`） |
| 预算 | `appId` → `adId` |
| 计费类型 | `billingType` |
| 转化目标（仅 CVR 实验） | `targetConvType` |

> ⚠️ **下钻查询的 `group_by` 写成 `expLayerN` + 新维度，`expLayerN` 必须始终留在里面。** 换维度时最容易把它替换掉，一替换各实验组就被合并成一行、**不报错但 diff 全没了**（同第 1.1 步）——diff 类标签这时就彻底钻不动。

## 维度词典（53 个）

> ⚠️ canonical key **大小写敏感**，必须原样传。例如谷雨过滤原因是 `GuyuFilterReason`（首字母大写 G），写成 `guyuFilterReason` 会被拒。实验层是 `expLayer20`，写成 `exp20` 同样会被拒。

| canonical_key | backend_field | UI 名称 | 中文常用说法 | 枚举值说明 |
| --- | --- | --- | --- | --- |
| `__time` | `__time` | `Time` | 时间, 时间维度（`split.group_by` 可传 `time` 或 `__time`） | __time=2026-03-11T12:04:00.000Z |
| `appId` | `appId` | `App Id` | 客户，应用，应用ID, appid | appId=1562009，**查询本字段时必读此文档以获取appid的中文名！`./enums/top_appid_cn_mapping.md`** |
| `adId` | `adId` | `Ad Id` | 广告ID, adid | adId=400498383 |
| `tagId` | `tagId` | `Tag Id` | 广告位ID, 广告位, tagid | ⚠️ **中文映射必须先读取** `./enums/xirang_ad_effect_enum_tag_id.md` |
| `mediaType` | `mediaType` | `Media Type` | 媒体类型 | **查询本字段时必读此文档以获取mediaType的中文名！`./enums/media_type_cn_mapping.md`** |
| `dspLevel1` | `dspLevel1` | `Dsp Level1` | 一级DSP | `effect`=内部dsp、`dsp`=外部dsp |
| `dsp` | `dsp` | `Dsp` | DSP, 二级dsp | ⚠️ **中文映射必须先读取** `./enums/xirang_ad_effect_enum_dsp_level2.md` |
| `billingType` | `billingType` | `Billing Type` | 计费类型, 计费方式 | `0`=OTHER、`1`=CPM、`2`=CPC、`3`=CPD、`4`=SCHEDULER |
| `targetConvType` | `targetConvType` | `Target Conv Type` | 目标转化类型 | ⚠️ **中文映射必须先读取**`./enums/xirang_ad_effect_enum_target_conv_type.md`。⚠️ **提到"转化类型"时，若无特殊说明，默认使用本字段** |
| `isPersonalizedClosed` | `isPersonalizedClosed` | `Is Personalized Closed` | 是否关闭个性化开关 | false代表未关闭，true代表已关闭 ，⚠️ **该看板查询**默认选择`isPersonalizedClosed`=false |
| `GuyuFilterReason` | `GuyuFilterReason` | `Guyu Filter Reason` | 谷雨过滤原因, 过滤原因 | `-1`=通过（未被过滤）、`18`=`GATEWAY_PERSONAL_LIMIT`（关闭个性化开关标识）、`19`=`GATEWAY_OCPXSTRATEGY_TIMEOUT_v2`（策略服务超时，并走 bid 调节逻辑）、`32`=`GATEWAY_DOWNGRADE_TO_MA`（降级到 MA）。⚠️ **非全量枚举**：未收录的码值只报数字与量级，**不得编造含义** |
| `expLayer20` | `expLayer20` | `Exp Layer20` | 实验层20 | **CTR 算法实验层**；值为实验号（字符串，如 `"2336638"`），多值 IN 查询 |
| `expLayer21` | `expLayer21` | `Exp Layer21` | 实验层21 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer22` | `expLayer22` | `Exp Layer22` | 实验层22 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer23` | `expLayer23` | `Exp Layer23` | 实验层23 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer24` | `expLayer24` | `Exp Layer24` | 实验层24 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer25` | `expLayer25` | `Exp Layer25` | 实验层25 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer26` | `expLayer26` | `Exp Layer26` | 实验层26 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer27` | `expLayer27` | `Exp Layer27` | 实验层27 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer28` | `expLayer28` | `Exp Layer28` | 实验层28 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer29` | `expLayer29` | `Exp Layer29` | 实验层29 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer30` | `expLayer30` | `Exp Layer30` | 实验层30 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer31` | `expLayer31` | `Exp Layer31` | 实验层31 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer32` | `expLayer32` | `Exp Layer32` | 实验层32 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer33` | `expLayer33` | `Exp Layer33` | 实验层33 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer34` | `expLayer34` | `Exp Layer34` | 实验层34 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer35` | `expLayer35` | `Exp Layer35` | 实验层35 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer36` | `expLayer36` | `Exp Layer36` | 实验层36 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer37` | `expLayer37` | `Exp Layer37` | 实验层37 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer38` | `expLayer38` | `Exp Layer38` | 实验层38 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer39` | `expLayer39` | `Exp Layer39` | 实验层39 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer40` | `expLayer40` | `Exp Layer40` | 实验层40 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer41` | `expLayer41` | `Exp Layer41` | 实验层41 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer42` | `expLayer42` | `Exp Layer42` | 实验层42 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer43` | `expLayer43` | `Exp Layer43` | 实验层43 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer44` | `expLayer44` | `Exp Layer44` | 实验层44 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer45` | `expLayer45` | `Exp Layer45` | 实验层45 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer46` | `expLayer46` | `Exp Layer46` | 实验层46 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer47` | `expLayer47` | `Exp Layer47` | 实验层47 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer48` | `expLayer48` | `Exp Layer48` | 实验层48 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer49` | `expLayer49` | `Exp Layer49` | 实验层49 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer52` | `expLayer52` | `Exp Layer52` | 实验层52 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer53` | `expLayer53` | `Exp Layer53` | 实验层53 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer54` | `expLayer54` | `Exp Layer54` | 实验层54 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer55` | `expLayer55` | `Exp Layer55` | 实验层55 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer56` | `expLayer56` | `Exp Layer56` | 实验层56 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer57` | `expLayer57` | `Exp Layer57` | 实验层57 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer58` | `expLayer58` | `Exp Layer58` | 实验层58 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer59` | `expLayer59` | `Exp Layer59` | 实验层59 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer60` | `expLayer60` | `Exp Layer60` | 实验层60 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer63` | `expLayer63` | `Exp Layer63` | 实验层63 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer64` | `expLayer64` | `Exp Layer64` | 实验层64 | CVR 算法实验层；值为实验号（字符串），多值 IN 查询 |
| `expLayer66` | `expLayer66` | `Exp Layer66` | 实验层66 | **CTR 算法实验层**；值为实验号（字符串，如 `"2336638"`），多值 IN 查询 |

## 指标词典（15 个）

> `raw` 表示直接求和——含 canonical_key 与 backend 字段名不同时的**别名求和**（如 `totalPltv = sum(pltv)`，行为上仍是原样求和）。
> `derived` 表示不是简单求和，而是比值、平均值、计数或组合表达式；具体公式见服务端模板 `birealtimev3ext.json` 的 `custom_expressions`。
>
> ⚠️ **可加性与 raw/derived 无关，判据是公式里有没有除法。** `view`、`click`、`advv`、`totalFee`（= `fee + feeRtb`）、`count` 这类**跨行可以相加**；`ecpm`、`ctr1`、`cvr`、`ctr_pcoc`、`cvr_pcoc`、`billingRatio`、`totalPctr` 这类含除法的比值/平均值**跨行不可相加**——多维拆分后要合并，必须回到分子分母重算，**不能把各行的比值直接相加或求算术平均**。
>
> ⚠️ **样例值仅用于示意数值量级与口径（是百分比还是纯比值），不代表达标。** 是否达标一律按第 3.2 步（达标值检查）的阈值判定。
>
> 下表公式里出现的 `fee`、`feeRtb`、`billCd`、`targetConvNum` 等是 **backend 原始字段**（如 `totalFee = fee + feeRtb`、`ctr1 = billCd*100/view`、`cvr = targetConvNum*100/billCd`）。它们本身也可查，字段名见 `./pivot_birealtimev3ext_field_dictionary_low_freq.md`，但算法侧实验分析直接用下表的派生指标即可，不必自己拼。

| canonical_key | UI 名称 | 中文常用说法 | 类型 | 样例值 |
| --- | --- | --- | --- | --- |
| `ecpm` | `ECPM(实际ecpm)` | ECPM, 千次曝光收入 | derived | 10.381801890242302 |
| `totalFee` | `totalFee(总收入)` | 总收入, 总消耗 | derived | 38724787.448085316 |
| `advv` | `advv(广告主价值)` | 广告主价值 | raw | 24390731.819325544 |
| `view` | `view(计费曝光)` | 曝光，计费曝光 | raw | 3730064189 |
| `click` | `click(计费点击)` | 点击, 计费点击 | raw | 65685749 |
| `startDownload` | `startDownload(开始下载)` | 开始下载 | raw | 19015035 |
| `ctr1` | `CTR(曝光扣费率%)` | 曝光扣费率, CTR_曝光扣费率 | derived | — |
| `totalPctr` | `pctr(预估ctr)` | 预估CTR | derived | 0.02428264958303468 |
| `totalPctrRaw` | `pctrRaw(预估ctrRaw)` | 预估CTR Raw | derived | — |
| `ctr_pcoc` | `ctr_pcoc(预估ctr/CTR曝光扣费率)` | CTR PCOC，CTR预估偏差 | derived | 1.0971 |
| `cvr` | `cvr(扣费转化率%)` | CVR, 转化率, CVR_计费转化率 | derived | 33.31215368472271 |
| `totalPcvr` | `pcvr(预估cvr)` | 预估CVR | derived | 0.15762199977948615 |
| `totalPcvrFixed` | `pcvrFixed(预估cvrfixed)` | 预估CVR Fixed | derived | 0.15852903942098204 |
| `cvr_pcoc` | `cvr_pcoc(pcvrfixed/cvr扣费转化率)` | CVR PCOC,CVR预估偏差 | derived | 1.0111 |
| `billingRatio` | `billingRatio(计费比%)` | 计费比 | derived | 107.11020583154415 |

## 备注

1. "UI 名称"优先取 Pivot 页面里实际看到的标签；`canonical_key` 是当前 skill 对外暴露给模型和脚本的标准键。
2. 本文档未收录的字段先翻 `./pivot_birealtimev3ext_field_dictionary_low_freq.md`；两份都没有的字段不存在于本看板，不要臆造。
3. `time` 参数**必须写成嵌套对象** `{"time": {"start_time": ..., "end_time": ...}}`。写成与 `filters` 平级的顶层 `start_time` 不会生效，也不会报错，会静默按最近 24 小时返回。

## 示例查询

> 两个示例覆盖算法侧最常见的两类问法（CTR 实验对比、CVR 实验对比）。`top` 默认 30 减少噪音；`sort_by` 按场景目标选。
> 两例都**显式传 `measures`**、都用**嵌套 `time`**、都带默认筛选——照抄即符合第 1 步的输入检查。
> 需要看同一实验组跨时间的变化（今天 vs 昨天、实验上线前后）时，用 `compare=true` 并显式写 `comparison_start_time` / `comparison_end_time`，用法见 SKILL.md 的「何时 `compare=true`」小节。

### 示例 1 — CTR 实验组对比（多维交叉拆分）

**用户问法**：「exp66 层实验 2336638 和 2336639 的 CTR 核心指标差异，按媒体拆分看看」

```json
{
  "time": {
    "start_time": "2026-08-11T00:00:00+08:00",
    "end_time": "2026-08-11T23:59:59+08:00",
    "compare": false
  },
  "filters": {
    "expLayer66": ["2336638", "2336639"],
    "isPersonalizedClosed": "false",
    "dspLevel1": "effect"
  },
  "split": { "group_by": ["expLayer66", "mediaType"], "top": 30, "sort_by": "view" },
  "measures": ["view", "ecpm", "totalFee", "advv", "ctr1", "ctr_pcoc"]
}
```

- 层号 66 属 CTR 算法实验，`measures` 取 CTR 组。
- `group_by` 带上 `mediaType`，回应"按媒体拆分"，同时演示多维交叉拆分。
- 输出时：2336638 < 2336639，**假设 2336638 为基线**——表头写成 `2336638（假设为对照组）` 即可，不必额外解释；对每个指标给出绝对 diff 与百分比 diff；再逐行检查 `ctr_pcoc` 是否落在 0.8–1.2、各组 `view` diff 是否超 ±0.5%。**表下回显本次的 `time`/`filters`/`split`/`measures`。**

### 示例 2 — CVR 实验组对比（定点流量 + 转化目标拆分）

**用户问法**：「exp25 层实验 2435205 和 2435204 在 tagid 1.13.c.1 上的核心指标差异，按转化目标拆开」

```json
{
  "time": {
    "start_time": "2026-08-11T00:00:00+08:00",
    "end_time": "2026-08-11T23:59:59+08:00",
    "compare": false
  },
  "filters": {
    "expLayer25": ["2435205", "2435204"],
    "tagId": "1.13.c.1",
    "isPersonalizedClosed": "false",
    "dspLevel1": "effect"
  },
  "split": { "group_by": ["expLayer25", "targetConvType"], "top": 30, "sort_by": "view" },
  "measures": ["view", "ecpm", "totalFee", "advv", "cvr", "cvr_pcoc", "billingRatio"]
}
```

- 层号 25 不是 20/66，属 CVR 算法实验，`measures` 取 CVR 组（含 `billingRatio`）。
- `group_by` 带 `targetConvType` 满足第 1.3 步（CVR 实验结合转化目标）。
- 输出时：**假设基线是数值更小的 2435204**（不是用户先提到的 2435205），表头标 `2435204（假设为对照组）` 即可。除 diff 外还要查 `cvr_pcoc` 是否在 0.8–1.2、`billingRatio` 是否在 80–120。**表下回显本次的 `time`/`filters`/`split`/`measures`。**
