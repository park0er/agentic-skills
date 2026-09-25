---
name: xirang-adx-diagnosis-enum-adx-reason
description: query_xirang_adx_diagnosis 的 adx_reason 英文代码 → 中文含义 + 所属环节映射。数据来源：DSP请求漏斗各环节过滤原因内部文档。
---

# adx_reason 过滤原因枚举（ADX链路多维分析看板）

> 字段 `adx_reason` 在后端响应中返回英文代码（如 `NOAD`、`TimeoutException`、`LOW_PRICE`），此文档提供中文含义和所属环节，用于提升分析和报告的可读性。

## 一、请求（请求DSP前的请求过滤）

此环节发生在媒体请求到达ADX后、向DSP发起竞价请求之前。

| adx_reason | 中文含义 | 备注 |
|---|---|---|
| `IP_NULL` | 客户端请求无IP地址不请求外部DSP | |
| `MODEL_NULL` | 客户端请求无机型不请求外部DSP | |
| `PACKAGE_IS_EMPTY` | 客户端请求没有包名不请求外部DSP | |
| `PACKAGE_NOT_MATCH` | 客户端请求包名与SSP配置不匹配不请求外部DSP | |
| `MEDIA_VERSION_ERROR` | 客户端请求媒体版本错误不请求外部DSP | |
| `SHORT_CIRCUITED` | 请求熔断 | DSP超时高后触发，降低对应DSP的请求量 |
| `no_need_rtb` | 该流量不走RTB请求 | |
| `ApiRequestFilter` | 联盟API媒体流量不请求外部DSP | |
| `ExternalDspEmptyDeviceIdFilter` | 设备ID过滤 | Android Q以上需要OAID，以下需要IMEI |
| `FastGameRequestFilter` | 联盟快游戏媒体流量不请求外部DSP | |
| `NotSdkGameRequestFilter` | 联盟SDK非游戏媒体流量不请求外部DSP | |
| `ExternalDspForbidFilter` | DSP黑名单过滤 | 请求中制定的DSP在SSP配置的黑名单中 |
| `PersonalizedAdFilter` | 关闭个性化广告的用户不请求DSP | 对应SSP配置 `personalized_ad_filter_dsp` |
| `APP_NOT_INSTALLED` | 未安装指定APP的流量不请求对应DSP | |
| `TimeDspFilter` | 时间定向/地域定向过滤 | 不在时间定向和地域定向范围内的DSP被过滤 |
| `WinRateDspFilter` | DSP竞胜率不符合要求 | 该DSP竞胜率不符合要求，请求被限制 |
| `ExternalDspTimeFilter` | 通知栏黑暗时间不请求外部DSP | |
| `CountFilter` | 到达曝光限制后不继续请求DSP | |
| `request in blacklist` | 黑名单过滤 | 对应SSP配置 `blacklist_filter` |
| `AppStoreVersionFilter` | 商店低版本及指定版本不请求外部DSP | |
| `TopDeviceDspFilter` | 固定高端机型可配置广告位不请求外部DSP | 对应配置 `top.device.filter` |
| `TaidixiongFilter` | 特定版本不请求taidixiong | "1.22.a.4", "1.22.a.5" 不请求 |
| `NewFeatureFilter` | 首页卡片化版本的请求不请求自然量 | |
| `MediaExpExcludeDspFilter` | 请求前根据配置规则过滤外部DSP | |
| `SUG_PACKAGES_NOT_MATCH` | 请求应用建议与配置不一致不请求对应DSP | |

## 二、响应前（DSP响应前的过滤）

此环节发生在请求已发给DSP、等待DSP返回广告的过程中。

| adx_reason | 中文含义 | 备注 |
|---|---|---|
| `retrieve_delay` | 排期延迟 | |
| `AF_RETRIEVE#TimeoutException` | 排期超时 | 请求排期后再请求DSP响应超时 |
| `AF_RETRIEVE#OutOfMemoryError` | 排期内存溢出 | |
| `TimeoutException` | 超时 | 直接请求DSP后响应超时 |
| `APPSTORE_ADS_CUT` | 商店新架构外部DSP超时截断 | |

## 三、出价前

此环节发生在DSP返回广告后、进入竞价排序之前。

| adx_reason | 中文含义 | 备注 |
|---|---|---|
| `NOAD` | DSP没有返回广告 | |

## 四、竞价前（DSP返回广告之后的广告过滤）

此环节发生在DSP已返回广告、进入竞价排序之前，对广告素材和内容做合规校验。

| adx_reason | 中文含义 | 备注 |
|---|---|---|
| `SENSITIVE_KW` | 广告文案被敏感词黑名单过滤 | |
| `SENSITIVE_URL` | 广告URL被黑名单过滤 | |
| `SENSITIVE_BUNDLE` | 广告包名被黑名单过滤 | |
| `BUNDLE_NOT_ON_APP_STORE` | 下载类广告包名未在商店上架 | |
| `TITLE_BLANK` | 广告title字段为空 | 涉及SSP key: `title.blank.filter.key` |
| `MATERIAL_MACHINE_AUDIT_WAIT` | 广告素材机审审核中 | 品牌DSP需要加白 |
| `MATERIAL_MACHINE_AUDIT` | 广告素材机审未通过 | |
| `MATERIAL_CHECK_FAIL` | ADX样式/素材模板校验失败 | 对各字段是否必填、文字限制做校验 |
| `URL_FORMAT_ERROR` | 广告内URL不符合要求 | 返回的所有地址必须是HTTPS |
| `APP_ALREADY_INSTALLED` | 下载类广告APP已安装 | |
| `VIDEO_DURATION_EXCEED_LIMIT` | 广告素材视频时长超过限制 | |
| `EXPOSE_LIMIT` | 曝光上限 | |
| `AppRequestFilter` | APP请求过滤 | |
| `QUICK_DP_FILTER` | 限制快应用广告投放 | |
| `AD_SDK_VERSION_ERROR` | 广告SDK版本错误 | |
| `SugSensitiveDspFilter` | SUG敏感DSP过滤 | |
| `INVALID_CR_ID` | 无效创意ID（CRID） | |
| `NO_MATERIAL_MATCHED_FILTER` | 样式不匹配过滤 | |
| `SAME_L1_FILTER` | 相同L1素材过滤 | |
| `appIdDeduplicate` | 广告位请求多条广告按appId去重 | |
| `multiTagIdDeduplicate` | 一次请求多广告位按广告元素去重 | |
| `DuplicatedAd` | 用户多次请求时间窗内去重 | |
| `multiTagIdAppIdDeduplicate` | 一次请求多广告位按appId去重 | |
| `cptCarouselDeduplicate` | CPT重复过滤 | |
| `landingUrlNeed` | landingUrl字段不能为空 | |
| `imgUrlNeed` | imgUrl字段不能为空 | |
| `titleNeed` | title字段不能为空 | |
| `videoUrlNeed` | videoUrl字段不能为空 | |
| `actionUrlNeed` | actionUrl字段不能为空 | |
| `imgUrlNeed_actionUrlNeed` | imgUrl和videoUrl字段不能同时为空 | |
| `titleNeed_actionUrlNeed` | title和actionUrl字段不能同时为空 | |
| `titleNeed_videoUrlNeed` | title和videoUrl字段不能同时为空 | |
| `titleNeed_imgUrlNeed` | title和imgUrl字段不能同时为空 | |
| `landingUrlNeed_videoUrlNeed` | videoUrl和landingUrl字段不能同时为空 | |
| `imgUrlNeed_landingUrlNeed` | imgUrl和landingUrl字段不能同时为空 | |
| `DOWNLOAD_AD_NO_BUNDLE` | 下载类广告bundle字段不能为空 | |
| `NO_BUNDLE` | 下载类广告bundle字段不能为空 | |
| `INVALID_ACTIONURL` | actionUrl字段内容失效 | |
| `emptyTemplateId` | TemplateId字段不能为空 | |
| `reqNoMatchRepTemplate` | TemplateId字段需与请求一致 | |
| `IMAGE_SIZE_NOT_CORRECT` | 广告素材尺寸与请求尺寸不一致 | |
| `target_dsp_has_been_blocked_after_close` | 用户点关闭后不再下发重复广告 | |
| `TemplateNotMatchException` | 京东API模板不匹配过滤 | |
| `NO_INSTALLED_DPL_PACKAGE` | 拉活广告未安装APP过滤 | 按状态判断字段 |
| `ALREADY_INSTALLED_ACTION_PACKAGE` | 拉新广告已安装APP过滤 | 按状态判断字段 |
| `PRICE_TOO_HIGH` | 异常过高出价 | |
| `MATERIAL_NOT_AUDITED` | 品牌DSP素材审核过滤 | DSP返回素材为空或没有该dealId/materialId的素材 |
| `previewDeDuplicator` | 排期preview广告去重 | 排期返回preview广告时其他广告被过滤 |
| `OuterDspAdsCutDeDuplicator` | 商店新架构外部DSP数目截断 | 模拟老架构lowprice外部折损 |
| `appStoreAppNameGroupJoinDeDuplicator` | 商店相似icon去重 | 相似icon只出一个（如抖音和抖音极速版） |
| `APP_IN_DELIVERED_APP_SET` | 商店首页分页去重 | 首页多页请求，第一页下发后在第二页去重 |
| `baseLevel1CategoryJointDeDuplicator` | 商店一级行业过滤 | 限制金融/游戏一级行业个数 |
| `CURRENT_APP` | 商店详情页下不能投放对应APP | |
| `NATURAL_IN_BLACK_LIST` | 商店黑名单过滤 | |
| `appIdJointDeduplicator` | 下发后appId去重 | |
| `L1L2CategoryIdJointDeDuplicator` | 商店相同类别去重 | |
| `external.dsp.consumer.controller.filter` | 商店自然量屏蔽 | |
| `GAME_APP_IN_NON_GAME_REQUEST` | 商店非游戏请求过滤游戏行业广告 | 请求中不含4.64时过滤外部DSP游戏行业广告 |
| `UNDERAGE_FILTER` | 商店请求排除appIdList对应APP过滤 | |
| `APP_IN_RECOMMEND_SET` | 广告已在商店推荐列表中过滤 | |
| `OFF_LINE_PRE_FILTER` | 商店行业过滤 | |
| `APP_IN_EXCLUDE_APPS` | 商店请求excludeAppIds包含的appId过滤 | |
| `SEARCH_RECALL_PREFILTER` | 商店搜索广告位外部DSP相关性过滤 | |
| `appStoreJointAppIdDeDuplicator` | 商店下发后appId去重 | |
| `NOT_CANDIDATE_APPID` | 非候选appId过滤 | |
| `APPSTORE_BLACK_APP_FILTER` | 商店APP黑名单过滤 | |
| `EXTERNAL_DSP_CONSUMER_CONTROLLER_FILTER` | 屏蔽外部DSP返回 | 支持地域、广告主等维度 |
| `PlacementTypeAppWhiteListFilter` | PT应用白名单过滤 | |
| `DOWLOAD_AD_NO_BUNDLE` | 有下载链接但无packageName | |
| `APP_NO_INSTALLED` | 未安装过滤 | |
| `LANDING_APK` | 落地页为.apk结尾禁止投放 | |
| `package_in_desktop_deleted_apps` | 桌面文件夹-过滤已删除应用 | |
| `appid_not_in_desktop.folder.app.whitelist` | 桌面文件夹-应用不在白名单中 | |
| `desktop_preload_no_landingurl` | 桌面文件夹-广告无落地页 | |
| `package_in_desktop_downloaded_apps` | 桌面文件夹-应用已安装 | |
| `SEARCH_INSTALLED_IN_SESSION` | 前序广告位开始下载屏蔽后序竞胜 | 4.12下载4.15过滤 |
| `UNION_INDUSTRY_FILTER` | 联盟行业预算屏蔽 | 应用业务屏蔽风险行业预算 |

## 五、竞价中

此环节发生在广告进入多DSP竞争排序阶段。

| adx_reason | 中文含义 | 备注 |
|---|---|---|
| `LESS_THAN_BID_FLOOR` | 价格低于广告位底价 | |
| `LOW_PRICE` | 竞价失败 | |
| `RANK` | 竞价失败 | |

## 六、异常错误（非占比异常高可忽略）

这些是网络/协议/系统级异常，正常情况下占比极低。只有当某项同比明显暴增时才需要关注。

| adx_reason | 中文含义 |
|---|---|
| `SocketException` | 网络异常 |
| `ResponseParserException` | 响应参数异常 |
| `RequestParamException` | 请求参数异常 |
| `NullPointerException` | 空指针异常 |
| `MalformedJsonException` | 下发JSON解析异常 |
| `IllegalStateException` | 非法调用 |
| `ResponseStatusException` | 广告返回非法异常 |
| `TException` | 内部错误 |
| `IllegalArgumentException` | 参数不合法 |
| `AF_RETRIEVE#RejectedExecutionException` | 排期线程拒绝 |
| `EOFException` | End of file，一般为广告返回204 |
| `SSLProtocolException` | SSL协议异常 |
| `RejectedExecutionException` | 拒绝执行异常 |
| `StreamResetException` | 流重置 |
| `SlotIdNotFoundException` | SlotId映射异常 |
| `ValidatorException` | 验证异常 |
| `InvocationTargetException` | 调用目标异常 |
| `IndexOutOfBoundsException` | 超出边界 |
| `ConnectException` | 链接异常 |
| `SSLException` | SSL异常 |
| `ConnectionShutdownException` | 链接关闭异常 |
| `IOException` | I/O异常 |
| `SSLHandshakeException` | 连接不可以 |
| `SocketTimeoutException` | Socket连接超时 |
| `ThriftInvokeException` | Thrift调用异常 |
| `ProtocolException` | 协议异常 |
| `UnknownHostException` | 未知异常 |
| `SSLPeerUnverifiedException` | HTTP请求异常 |
| `InvalidProtocolBufferException` | HTTP请求异常 |
| `NoRouteToHostException` | 非路由宿主异常 |
| `RuntimeException` | 运行异常 |
| `InvalidWireTypeException` | 无效线程异常 |
| `TTransportException` | Thrift传输异常 |
| `DataFormatException` | 数据格式异常 |

## 七、竞价成功

| adx_reason | 中文含义 | 备注 |
|---|---|---|
| `null` | 成功下发 | 竞价成功正常下发，不计为过滤 |

## ⚠️ 使用约定

- 查询结果中 `adx_reason` 字段返回的是英文代码（如 `NOAD`、`LOW_PRICE`、`TimeoutException`）
- **字典内代码**：Agent 分析及输出报告时引用表格里的中文含义和所属环节，不做语义改写
- **字典外代码**：可能是新增过滤项，词典还未收录，只报英文代码 + 量级 + 同比，**不要编造含义**
- 如某个过滤原因的过滤量同比异常增大，建议写入报告并标注"需 ADX 侧同学跟进过滤原因 XXXX"
- 异常错误类（第六节）在正常情况下占比极低，只有同比暴增才在报告中提及
