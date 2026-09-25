---
name: inside-curr-configs-field-dictionary
description: strategy_operation_query category=inside_curr_configs（内部配置信息）字段含义，供 agent 解读返回数据使用
---

# 内部配置信息（strategy_operation_query / inside_curr_configs）

category 值：`"inside_curr_configs"`

**返回类型：列表，含递归 children**

用途：查看平台侧对该广告/计划/账户/应用施加的策略配置——拉黑、定向、排除过滤、出价调整、预算复用、拦截比例等内部干预手段。排查平台策略是否抑制了广告投放。

## 调用参数
>查询必须输入`start_time`和`end_time`，如果用户没有明确表达，默认查当天数据

| 参数 | 必填 | 说明 |
|---|---|---|
| `start_time` | 是 | ISO 8601 +08:00 格式，如 `"2026-06-01T00:00:00+08:00"` |
| `end_time` | 是 | ISO 8601 +08:00 格式，如 `"2026-06-08T00:00:00+08:00"` |
| 六选一维度 key | 是 | `adId` / `adGroupId` / `campaignId` / `accountId` / `appId` / `adReportId` |
| `category` | 是 | 固定值 `"inside_curr_configs"` |

## 顶层字段（insideCurrentConfigs，14 个）

| canonical_key | 中文含义 | 说明 |
|---|---|---|
| `operateTime` | 配置生效时间 | `YYYY-MM-DD HH:MM:SS` |
| `platform` | 配置来源平台 | **与 `strategyKey` 一起决定 `newValue` 怎么解析** |
| `operateDimId` | 配置维度 ID | 见"operateDimId"表 |
| `operateDim` | 配置维度 | 中文，如 `"账户"`、`"应用"`、`"广告计划"` |
| `operateValue` | 配置对象值 | 对应的账户/应用/计划/广告 ID，也可能是包名或 RTA token 名 |
| `strategy` | 策略标识 | `strategyCn` + `-` + `strategyKey` 的拼接，无独立信息量 |
| `strategyCn` | 策略中文名 | 多数是运营手填的配置名，**不是枚举**。价值在于常直白写出运营意图（拉黑/屏蔽/定向/过滤/降价/控量） |
| `strategyKey` | 策略 Key | **稳定标识**，分族解析靠它 |
| `newValue` | 配置详情 | 结构由族决定，见"newValue：先分族，再解析" |
| `linkUrl` | 配置详情页链接 | 配置在源平台的详情页地址。路径可辅助识别配置类型（如 `/clpx/setOrientation` 与 `/clpx/excluFiltration`）；聚合父节点为空 |
| `status` | 生效状态 | `未知` / `生效` / `失效` / 空串。见下方警告 |
| `disableReason` | 失效原因 | 通常为空 |
| `children` | 子配置列表 | 递归结构，子项字段与顶层一致 |
| `key` | 唯一标识 | 第 4 段是被截断的策略名，**不要用它做解析** |

### ⚠️ status 不能用来过滤配置

`未知` 是最常见的取值，占多数，**它不代表配置没生效**。按"只看 `生效`"筛选会丢掉大部分真实生效的配置，且这种丢失不报错、无痕迹。

枚举只有 `未知` / `生效` / `失效` / 空串（空串仅出现在聚合父节点）。**不存在 `禁用`**。

### 聚合父节点：`newValue` / `linkUrl` / `status` 三空 + 有 `children`

这四个条件同时成立即为聚合父节点。它本身不是一条配置，真实内容全在 `children` 里，`strategyCn` 形如「拉黑配置, 共6条记录」。

遍历时必须递归展开 `children`，否则会漏掉大部分真实配置。反过来，看到 `newValue` 为空**不要报告"配置详情为空"**，先确认它是不是父节点。

### operateDimId ↔ operateDim

| operateDimId | operateDim | operateValue 含义 |
|---|---|---|
| 1 | 广告创意 | 广告 ID |
| 2 | 广告组 | 广告组 ID |
| 3 | 广告计划 | 计划 ID |
| 4 | 账户 | 客户账户 ID |
| 5 | 应用 | 应用 ID |
| 6 | RTA token | token 名 |
| 7 | RTA客户 | client 名 |
| 8 | 行业等级二 | 二级行业 ID |
| 9 | 行业等级一 | 一级行业 ID |
| 10 | 应用一级分类 | 分类 ID |
| 11 | 包名 | 包名字符串，如 `com.jingdong.app.mall` |

### platform

| platform | 涉及的配置 |
|---|---|
| `SSP平台` | 预算复用、各类黑名单/拦截比例、RTA 比例配置 |
| `新运营工具平台` | 拉黑配置、设置定向/排除过滤、调整出价配置、RTA 客户与 token 信息 |
| `PS策略平台` | 运营自定义定向/排除策略 |
| `Prism平台` | ocpx 调价规则、ocpx 广告配置 |
| `Apollo配置中心` | 研发侧 pcvr 系数 |

## newValue：先分族，再解析

`newValue` **不是一张统一的字段表**。字段集合由 `(platform, strategyKey)` 决定，不同族之间字段完全不重叠。**跨族套用字段含义会读出错误结论。**

### 第一步：判形态并解出 KV

| 形态 | 结构 | 出现在 |
|---|---|---|
| A · KV 列表 | `list[{"key":k,"value":v}]`，value 是标量 | 调整出价配置、预算复用、RTA |
| B · KV 列表嵌套二次序列化 | 同 A，但 value 本身是二次序列化的 JSON string | 拉黑配置、设置定向/排除过滤 |
| C · 规则树 | `{"name","defaultValue","master":[...],"grey":[]}` | SSP 黑名单/拦截比例 |
| D · 普通 dict | 直接就是对象 | PS策略平台、Prism平台 |
| 空 | `""` / `[]` / None | 聚合父节点 |
| 纯文本 / 裸数字 | 如 `"329:0.6"`、`5912` | Apollo配置中心 |

```python
nv = rec.get("newValue")
if not nv:                      # 聚合父节点 → 去 children
    ...
elif isinstance(nv, str):
    try:
        nv = json.loads(nv)     # 绝大多数是 JSON string，必须先解一层
    except ValueError:
        pass                    # Apollo 纯文本，原样呈现
if isinstance(nv, list):        # 形态 A / B
    kv = {}
    for item in nv:
        v = item["value"]
        if isinstance(v, str) and v.strip().startswith(("{", "[")):
            v = json.loads(v)   # 形态 B：value 必须再解一层
        kv[item["key"]] = v
```

⚠️ **形态 B 只解一层会静默丢掉全部限定条件**（拉黑范围、定向范围），这是最容易出错的地方。

### 第二步：按族读字段

---

#### 族①　oCPX 出价类配置（`新运营工具平台` + `ssp_ocpx_*`）

平台侧对出价的直接干预，掉量诊断优先级最高的族之一。三个 `strategyKey` 形态同为 A、字段大量重叠：

| strategyKey | strategyCn | 生效维度 | 说明 |
|---|---|---|---|
| `ssp_ocpx_adjust_price` | 调整出价配置 | 账户 / 广告计划 / 应用 / 广告 | 本族主体，字段与判读见下文 |
| `ssp_ocpx_dark_price` | 暗配oCPX目标出价 | 广告创意 | 暗投广告的目标出价配置。额外带 `placementType`（PT）；调价幅度看 `deepConfigRatio`，少数条目用 `configRatio` |
| `ssp_ocpx_pdcvr_ratio` | pdcvr系数配置 | 广告创意 / 应用 | 次留系数配置，调价幅度看 `configRatio`。另带一组**配置时的效果快照字段**（`billingRatio`/`feeCash`/`targetCpa`/`targetConvNum`/`targetConvCost`/`deepTargetCpa`/`deepTargetConvNum`/`deepCvr`/`view`/`click`/`startDownload`/`endDownload`/`ctr`），常见为 0，**是快照不是当前效果，不要当实时数据引用** |

⚠️ `targetCpa` 在本族是小数形态的效果快照，与族⑦ Prism 的整数 `targetCpa` 不是同一个东西。

**先读 `configType`**，它决定这条配置在调什么：

| configType | 含义 |
|---|---|
| `1` | 出价系数调整 |
| `2` | targetCPA ratio |
| `3` | bid上下界 |
| `4` | 搜索词出价系数 |

`configType=3` 没有 `configRatio`，方向看 `minBound`/`maxBound`；其余三类看 `configRatio`。⚠️ 上述取值含义**只适用于 `ssp_ocpx_adjust_price`**；`ssp_ocpx_dark_price` 与 `ssp_ocpx_pdcvr_ratio` 的 `configType` 取 `0`/`1`，含义不同，不要套用。别的族下的同名字段也与此无关。

| 字段 | 含义 | 判读要点 |
|---|---|---|
| `id` | 配置 ID | 与 `linkUrl` 中的 `searchForm={"id":"..."}` 对应 |
| `configRatio` | 配置系数 | `>1` 提价、`<1` 压价（`1.5`=加价 50%），范围 0.01–50 |
| `deepConfigRatio` | 深层配置系数 | 仅 `configType=2` |
| `minBound` / `maxBound` | bid下界比率 / bid上界比率 | 仅 `configType=3`；这两个才是该类型的方向依据 |
| `keyType` | 生效层级 | `1`=广告、`2`=广告计划、`3`=账户、`4`=应用。⚠️ 与族③的 `level` 不是同一套编码 |
| `queryKey` | 生效对象 ID | 恒等于 `keyType` 所指层级的 ID，也等于顶层 `operateValue`。与 `keyType` 配对读 |
| `customerId` / `campaignId` / `appId` / `adId` | 生效层级链路 | 非 0 的字段自上而下补全归属。`keyType=2` 时 `campaignId` 是生效对象，`customerId`/`appId` 说明它属于哪个账户和应用 |
| `convType` | 浅层转化目标 | 枚举见 `references/enums/xirang_ad_effect_enum_target_conv_type.md`，`0`=不限。语义是"**这条调价只对该转化目标的广告生效**"，判影响范围必看 |
| `deepConvType` | 深层转化目标 | 同上枚举，`0`=不限 |
| `dsp` / `mediaType` / `tagId` / `billingType` | 流量限定条件 | 值为 `"全部"` 或逗号分隔的具体值。**直接决定影响多大范围** |
| `adjustingRange` | 调价定向 | 仅 `configType=2` |
| `expId` | 实验 ID | 仅 `configType=3` |
| `searchKeyWords` | 搜索词 | 仅 `configType=4`，逗号分隔 |
| `effectiveStartTime` / `effectiveEndTime` | 生效周期 | **13 位毫秒时间戳** |
| `compensateMark` | 备注 | 运营手填的原因（"汽水核心位增量""头部计划不压计费比"），**判断配置意图最直接的字段** |
| `compensate` / `compensateRole` | 超成本赔付相关 | 口径未确认，原样呈现 |
| `onlyHolidaysEffective` | 是否仅节假日生效 | 仅法定节假日与正常周末，不含调休后的周末工作日 |
| `bpmStatus` | 审批状态 | 本接口只返回已通过审批的配置，审批中/已驳回的查不到 |
| `createBy` / `updateBy` / `notifier` | 配置人 / 修改人 / 通知人 | MI 账号，要找人时用 |

---

#### 族②　拉黑配置（`新运营工具平台` + `abram_v2`）

`strategyCn` 固定为 `拉黑配置`。**存在即为强干预信号。**

形态 B，解出的每个 key 对应一个限定条件对象 `{"field","operator","value":[...],"editMode"}`：`operator` 为 `IN`（命中即拉黑）/ `EX`（排除）/ 空；`editMode` 为 `NEW` / `EXIST`。

| 字段 | 含义 |
|---|---|
| `##id##` | 拉黑规则的记录 ID。顶层 `linkUrl` 用它拼跳转，是唯一能点进配置详情的锚点 |
| `##searchTag##` | **拉黑标签 + 原因 + 责任人**。本族最有价值的字段：前缀是标签（`【客户禁投】`/`【复用屏蔽】`/`【竞品屏蔽】`/`【分成限制屏蔽】`/`【特殊需求】`），后接自由文本原因，末尾常带 MI 账号。判断"这个拉黑该不该存在"就靠它 |
| `appId` / `customerId` | 被拉黑的应用 / 账户范围 |
| `tagId` / `uniLocation` / `placementType` / `displayType` | 广告位 / 版位 / 样式范围 |
| `mediaType` / `dsp` | 媒体 / DSP 范围 |
| `l1l2Category` / `l1Category` / `industryLevel1` | 行业与分类范围 |
| `mediaExpIds` / `adExpIds` | 实验范围 |
| `city` / `province` / `dmpCity` | 地域范围 |
| `keyword` | 关键词范围 |
| `uaid` / `userId` / `adPackageName` | 其他限定范围 |

除 `##id##` 和 `##searchTag##` 外，**其余 key 全是"拉黑生效的范围条件"**，是量化影响面的依据。

---

#### 族③　设置定向 / 排除过滤（`新运营工具平台` + 纯数字 `strategyKey`）

对应运营工具平台「策略配置 → 设置定向 / 排除过滤」。

| 字段 | 含义 | 判读要点 |
|---|---|---|
| `type` | **`0`=设置定向、`1`=排除过滤** | `linkUrl` 也分别指向 `/clpx/setOrientation` 与 `/clpx/excluFiltration`。**掉量诊断重点看 `type=1`**；把 `type=0` 报成抑量原因是方向性错误 |
| `strategies` | **这条策略到底干了什么** | `[{"category","value","name","ratio"}]`。`category` 见下表，`name` 是 `value` 的中文，`ratio` 是生效比例（`1.0`=100%、`0.7`=70%） |
| `level` | 生效级别，分号分隔多段 | 编码见"三套生效层级编码"。`"5;10"` = 第一段账户、第二段 DT |
| `objectIds` | 生效对象，分号分隔多段 | 与 `level` 同序对应，段内逗号分隔多个对象 |
| `effects` | `level`+`objectIds` 的结构化形式 | `[{"effectType","value"}]`，`effectType` 对应 `level`、`value` 对应 `objectIds`。有值时优先读它，为空数组时回落到 `level`+`objectIds` |
| `manual` | 是否限定生效时间 | `false` = 不限时间；`true` = 用具体时段限定 |
| `isAvaliable` | 启用开关 | |
| `flowAdEffect` | 是否对流量优选广告生效 | |
| `tagExpire` | 标签是否过期 | |
| `startTime` / `endTime` / `updateTime` | 生效周期 | **Java `Date.toString()` 格式**，如 `Tue Aug 25 17:01:46 CST 2026` |
| `description` | 策略名称 | 同 `strategyCn` |
| `owner` | 配置人 | MI 账号 |

`category` 中文名（族④的 `applyRatios`/`others` 复用同一套）：

| 定向类 | 中文 | 排除类 | 中文 |
|---|---|---|---|
| `mediaType` | 媒体定向 | `ex_mediaType` | 媒体排除 |
| `tagId` | tagid定向 | `ex_tagId` | tagid排除 |
| `includeTags` | 人群包 | `excludeTags` | 排除人群包 |
| `uaId` | uaId定向 | `ex_uaId` | uaid排除 |
| `city` | 城市定向 | `ex_city` | 城市排除 |
| `unionSource` | 联盟渠道来源定向 | `ex_unionSource` | 联盟渠道来源排除 |
| `installedApps` | 已安装App定向 | `negativeWords` | 否词 |
| `notInstalledApps` | 未安装App定向 | `isFilterClick` | 点击过滤（`1`=是、`0`=否） |
| `gender` | 性别（`1`=男、`2`=女） | | |
| `activeDays` | 激活天数（`-1`=未激活） | | |

`installedApps` / `notInstalledApps` 取 `-1` 时表示"取消 emi 定向"。

`ratio` 小于 1 时**必须带上比例说明影响面**：`ex_tagId` + `ratio=0.7` 读作"该广告位 70% 的流量被排除"，不能报成全量拉黑。

---

#### 族④　PS策略平台自定义策略（`PS策略平台` + 纯数字 `strategyKey`）

同样是运营配的定向/排除策略，字段结构与族③完全不同。

| 字段 | 含义 | 判读要点 |
|---|---|---|
| `配置信息` | **生效层级（中文，最直白）** | `[{"策略生效级别":"广告计划级别","广告计划ID":"100971717"}, ...]`，一条配置可铺多个对象 |
| `applyRatios` | **策略动作 + 生效比例** | `[{"category","ratio"}]`，`category` 用族③那张中文名表 |
| `others` | 动作的具体取值 | `[{"category","value","ratio"}]`。⚠️ 少数记录里它是二次序列化的字符串，需再 `json.loads()` |
| `includeTags` / `excludeTags` | 人群包 ID | 逗号分隔 |
| `tagIds` / `mediaTypes` | 广告位 / 媒体 | |
| `filterByClick` | 点击过滤开关 | |
| `startTime` / `endTime` / `createTime` / `updateTime` | 时间 | **ISO 8601 带时区 ID**，如 `2022-08-11T19:20:32+08:00[Asia/Shanghai]` |
| `description` / `owner` / `watchers` | 策略名 / 配置人 / 关注人 | `watchers` 是字符串不是数组 |
| `valid` / `isAvaliable` | 有效 / 启用标志 | |

`配置信息` 里 `策略生效级别` 与配对键：广告级别↔`广告ID`、广告组级别↔`广告组ID`、广告计划级别↔`广告计划ID`、客户级别↔`账户ID`、APP级别↔`APP ID`，另有 `未知`↔`未知`。

⚠️ 本族的 `type` 与族③的 `type` 无关，不要套用定向/排除的含义。

---

#### 族⑤　预算复用（`SSP平台` + `ssp_allocate_config` / `ssp_placement_type_config`）

`strategyCn` 为 `预算复用`。这一族返回条数往往很多，注意不要因为量大就跳过。

共有字段：

| 字段 | 含义 |
|---|---|
| `valueType` | `value` 是哪一层的 ID：`1`=appId、`2`=账户 ID。**不看它会把账户 ID 误读成 appId** |
| `value` | 生效对象 ID，等于顶层 `operateValue` |
| `appId` | 常为 `"0"`，表示不限定，真实对象看 `value` |
| `dsp` | `de` / `xiaomi.ocpa` / `xiaomi.finocpa` / `xiaomi.ecomocpa` / `xiaomi.sdpaocpa` / `xiaomi.evokeocpa-cvr` / `全部` |
| `ctime` / `mtime` | **10 位秒级时间戳**，`0` 表示未设置 |

`ssp_allocate_config`（广告位粒度）：`placementTypeId` 广告位类型、`tagid` 广告位（支持通配 `1.24.*.*`）、`mediaType` 媒体、`ratio` 复用比例、`ratioBuffer` 比例缓冲、`dropRatio` 丢弃比例。

`ssp_placement_type_config`（广告位类型粒度）：`id` 就是**广告位类型 ID（PT）**、与 `name`（PT 中文名）一一对应；另有 `enableAllocate`、`allocateThreshold`、`defaultAllocateRatio`、`allocateRatioBuffer`。注意这一族的 `id` 不是自增记录号。

---

#### 族⑥　规则树类（`SSP平台` + 业务 key）

各类黑名单、拦截比例、复用比例配置。这一族的 `strategyCn` 是固定词（如 `广告拦截比例配置`、`效果一级行业黑名单`、`已激活过滤应用名单`），直接读即可。

```json
{
  "name": "广告拦截比例配置",
  "defaultValue": "true",
  "master": [
    {"conditionId": 15637,
     "value": "false",
     "rules": [{"rule":"packageName","operator":"IN","ruleValue":"com.dragon.read,..."},
               {"rule":"tagId","operator":"IN","ruleValue":"1.148.k.1"},
               {"rule":"user","operator":"<=","ruleValue":"25"}]}],
  "grey": []
}
```

读法：`master` 里每个条件块表示"当 `rules` 全部命中时取 `value`"，都不命中则取 `defaultValue`；`grey` 是灰度条件块。

⚠️ `defaultValue` 和 `ruleValue` 常是几百个 appId 或几千个 uaid 的超长清单，**只提取与当前查询对象相关的片段**，不要整段贴给用户。

---

#### 族⑦　Prism 调价规则（`Prism平台`）

这一族的 `strategyKey` 本身是一个 JSON，与 `newValue` 内容高度重叠。

| strategyCn | strategyKey | newValue 字段 |
|---|---|---|
| `ocpx调价规则配置` | `{"appId","expId","confType":"adjustBound"}` | `minBound`、`maxBound`（bid 下界/上界比率） |
| `ocpx调价规则配置` | `{"adId"/"appId","confType":"adjustCoefficient"}` | `proportional`、`integral`、`differential`（PID 调价的 P/I/D 系数）、`iCoefficientAttenuationFactor`（i 值衰减系数） |
| `ocpx广告配置` | `{"adId","conversionType","targetCpa"}` | `adId`、`conversionType`、`targetCpa` |

`conversionType` 枚举见 `references/enums/xirang_ad_effect_enum_target_conv_type.md`。`expId` 形如 `188^47^147297`。

⚠️ `targetCpa` 是整数形态（如 `2200000`、`963510`），**单位未确认，不要换算成元、也不要与 `emi_ad_detail` 里的"XX元"出价直接比较**。原样呈现数值，需要口径时问用户。

---

#### 族⑧　其他族

| 族 | 说明 |
|---|---|
| RTA 相关（`SSP平台` + `clientName`/`tokenRatio`/`appRatio`/`tagIdRatio`，`新运营工具平台` + `token信息`/`rta_client_info`） | 字段名自解释（`clientName`、`token`、`installRatio`、`uninstallRatio`、`budget`、`cacheTime` 等）。⚠️ 这一族的 `ratio`/`installRatio`/`uninstallRatio` 是 **0–100 的百分数**，不是 0–1 小数。RTA 链路本身另有 `query_xirang_rta_diagnosis` 看板 |
| `Apollo配置中心` | 研发侧 pcvr 系数，`newValue` 是 `appId:系数` 的逗号列表或裸数字。不要试图结构化解析，**原样呈现** |

---

#### 遇到未收录的族

本词典按 `platform` + `strategyKey` 组织，线上会出现这里没列的组合。**这不代表配置不重要。**

处理方式：把 `strategyCn`（运营意图常直接写在里面）和 `newValue` 原始内容给用户，明确说明这是词典未收录的配置类型，请用户确认口径。**不要因为查不到族就当它不存在，也不要拿相邻族的字段含义硬套。**

## ⚠️ 三套"生效层级"编码互不通用

同一份返回里并存三套编号，数字相同但含义不同，混用会把生效层级读错：

| 编号 | 顶层 `operateDimId` | 族①的 `keyType` | 族③的 `level` / `effectType` |
|---|---|---|---|
| `1` | 广告创意 | 广告 | 广告id |
| `2` | 广告组 | 广告计划 | 计划id |
| `3` | 广告计划 | **账户** | **应用id** |
| `4` | 账户 | **应用** | **PT** |
| `5` | 应用 | — | 账户id |
| `6` | RTA token | — | 版位*素材规格（`objectIds` 形如 `"版位:素材规格"`，用冒号再分一层） |
| `10` | 应用一级分类 | — | **DT** |
| 其他 | 7=RTA客户、8=行业等级二、9=行业等级一、11=包名 | — | — |

**PT** = 广告位类型，**DT** = 版位。两者是不同的码表，页面上就叫 PT / DT，没有中文别名。

本词典未收录 PT 和 DT 的码表。`level`/`effectType` 为 `4` 或 `10` 时，只说明"生效在某个 PT / 某个 DT 上"并把原始数字给用户，**不要猜它是哪个广告位或版位**。唯一可借用的对照是族⑤ `ssp_placement_type_config` 的 `id`↔`name`，它给出了部分 PT 的中文名。

## 时间字段格式

| 出现位置 | 格式 | 示例 |
|---|---|---|
| 顶层 `operateTime` | `YYYY-MM-DD HH:MM:SS` | `2026-08-25 17:01:46` |
| 族① `effectiveStartTime`/`effectiveEndTime` | 13 位毫秒时间戳 | `1784217600000` |
| 族③ `startTime`/`endTime`/`updateTime` | Java `Date.toString()` | `Tue Aug 25 17:01:46 CST 2026` |
| 族④ `startTime`/`endTime`/`createTime`/`updateTime` | ISO 8601 + 时区 ID | `2022-08-11T19:20:32+08:00[Asia/Shanghai]` |
| 族⑤ `ctime`/`mtime` | 10 位秒级时间戳（`0`=未设置） | `1662436399` |

判断"配置是否覆盖掉量时间点"前必须先认准格式，混用会得出完全错误的时间。`endTime` 为 `2030-12-31` 是"长期有效"占位，不是真的到期计划。

## 典型查询示例

```json
{
  "start_time": "2026-06-01T00:00:00+08:00",
  "end_time": "2026-06-08T23:59:59+08:00",
  "adId": "411787296",
  "category": "inside_curr_configs"
}
```

## 使用要点

1. **先递归展开 `children`**。`newValue`/`linkUrl`/`status` 三空的节点是聚合父节点，真实配置全在 `children` 里。
2. **按 `platform` + `strategyKey` 分族，再按族读字段**。不要把 `newValue` 当统一字段表查。
3. **不要用 `status` 过滤**。`未知` 占多数且不代表未生效。
4. **优先级**：族②拉黑配置（直接阻断投放，看 `##searchTag##` 判原因）→ 族③ `type=1` 与族④ `ex_*` 动作（限制可触达流量，看 `ratio` 量化影响面）→ 族① oCPX 出价类配置（先看 `strategyKey` 与 `configType`，再看 `configRatio`/`deepConfigRatio` 或 `minBound`/`maxBound` 判方向）→ 族⑤预算复用与族⑥拦截比例（影响可分配流量）。
5. **判影响范围必须连带读限定条件**：族①的 `dsp`/`mediaType`/`tagId`/`billingType`/`convType`/`deepConvType`，族②的各范围字段，族③的 `level`+`objectIds`。只看"有没有配置"不看"配在哪、覆盖多少比例、对哪个转化目标生效"，会把只影响少量流量的配置误判成掉量主因。
6. **对时**：按 `operateTime` 排序找掉量前后新上或变更的配置，再用对应族的生效周期字段确认它当时确实在生效窗口内。
7. **拿不准就原样呈现**：Apollo 的纯文本、族⑥的超长清单、未收录的族、以及词典未给出含义的字段，都不要自行猜测，把原始内容给用户。
