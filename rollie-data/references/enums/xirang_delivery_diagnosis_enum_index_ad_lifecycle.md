---
name: xirang-delivery-diagnosis-enum-index-ad-lifecycle
description: query_xirang_delivery_diagnosis 的 index_ad_lifecycle 英文过滤码 → 中文名称 + 解释映射。
---

# index_ad_lifecycle 枚举（投放诊断 - 召回+业务过滤看板）

> 字段 `index_ad_lifecycle` 在后端响应中返回英文过滤码（如 `booleanIndex`、`PreTopNFilter`），此文档提供中文名称和业务解释，用于提升诊断报告的可读性。

## ⚠️ 使用约定

- 查询结果中 `index_ad_lifecycle` 字段返回的是英文代码（如 `booleanIndex`）
- **字典内代码**：Agent 分析及输出报告时引用表格里的中文名称和解释，不做语义改写
- **字典外代码**：可能是新过滤项，词典还未收录，只报英文代码 + 量级 + 同比，**不要编造含义**
- 如某个代码的过滤量同比异常增大，建议写入报告并标注"需 L2/L3 同学跟进代码 XXXX"


## 召回

共 71 条过滤码：

| 过滤码 | 中文名称 | 解释 |
|---|---|---|
| `booleanIndex` | 召回过滤 | 含定向过滤（人群定向、策略平台配置的人群定向或排除逻辑）、RTA预过滤、ANN过滤等 |
| `PreTopNFilter` | PreTopNFilter | 为了应对召回层超时后topN_filter算不过来超时的问题，在已有的topN截断前又加了一道topN截断，截断逻辑和原有的topN逻辑一致 |
| `indexResultAd` | indexResultAd | index超时，这个分片的请求广告丢弃。 |
| `OcpxSwitchPreFilter` | OcpxSwitchPreFilter | ocpx广告的Dsp流量开关没打开 |
| `OpenStrategyFilter` | OpenStrategyFilter | 打开策略：如最近n天内打开过app的用户不下发 |
| `AppBehaviorFilter` | 用户行为策略过滤 | 已卸载/活跃n天/未活跃n天的用户停止下发 |
| `RtaCachePostFilter` | RtaCachePostFilter | 过滤有效期外的缓存结果中，明确拒绝的token对应广告，记外发Token |
| `TodayClickedAdFilter` | TodayClickedAdFilter | 当日已点击过滤 |
| `FlowOptPolicy` | 流量优选过滤 | 流量优选过滤 |
| `BudgetControlFilter` | BudgetControlFilter | 和BudgetControlController是同个逻辑过滤，只是标识不一样，在引擎侧因为在做向量化迁移所以需要起了两个标识 |
| `MMSKeyWordsRetriever` | MMSKeyWordsRetriever | 短信根据关键字召回，每个标签映射了app |
| `PushRetriever` | PushRetriever | 通知栏复用预算白名单 |
| `RecentlyExposedAppIdFilter` | 最近广告应用过滤 | 最近已曝光的app过滤（内容中心、桌面、画报、浏览器） |
| `RtaPreFilter` | RtaPreFilter | RTA预过滤，媒体开关（常开）、ssp开关过滤 |
| `RecentlyClickedAppIdCpcFilter` | RecentlyClickedAppIdCpcFilter | 最近已点击cpc广告过滤（天气） |
| `CpdAdAppInstalledFilter` | CPD已安装过滤 | cpd广告已安装过滤，目前的已安装app依赖两份数据，一份是DMP维护的用户已安装数据，另一份是用户（开始下载+24h内继续下载）的数据，这两个加一起，都判断为是已安装 |
| `BlackListFilter` | SSP黑名单过滤 | SSP各种黑名单过滤（主要针对详情页） |
| `UnionRetriever` | UnionRetriever | 联盟融合投放有个白名单，没配置的则过滤 |
| `ActivationStrategyFilter` | 广告激活策略过滤 | 已激活过滤 |
| `AppInstalledFilter` | AppInstalledFilter | app已安装过滤，判断这个请求已经安装了这个app后才会触发这个过滤项，一般不会有异常过滤 |
| `MaterialLevelFilter` | 素材等级过滤 | 素材等级过滤 |
| `UnionPackageNameFilter` | UnionPackageNameFilter | 联盟自己不能投自己 |
| `UnionPlacementTypeReduceFilter` | UnionPlacementTypeReduceFilter | 联盟根据广告位样式style过滤预算，如果广告位样式为图片类，过滤视频类预算；相反，广告位样式为视频类，过滤图片类预算。 |
| `SearchRecallPreFilter` | 搜索召回过滤 | 搜索结果页搜索召回过滤 4.31 |
| `AppUninstalledFilter` | 用户未安装广告过滤 | 仅保留用户已安装的appid对应的广告，依赖数据源为两份：一份是DMP维护的用户已安装数据，另一份是用户（开始下载+24h内继续下载）的数据，这两个加一起，都判断为是已安装 |
| `MediaConstraintReduceFilter` | MediaConstraintReduceFilter | uaid定制化过滤，媒体设置的包名、关键词过滤，不希望竞品出现在自己的媒体上 |
| `RecentlyExposedCampaignFilter` | 最近广告计划曝光过滤 | 最近广告计划曝光过滤（全搜、内容中心、浏览器） |
| `PushAppIdAuthorityFilter` | PushAppIdAuthorityFilter | 通知栏应用发权限通知的应用才能出广告 |
| `UnionTargetingReduceFilter` | UnionTargetingReduceFilter | uaid定向 |
| `PhoneVideoMiuiVersionPreFilter` | PhoneVideoMiuiVersionPreFilter | MIUI版本号以“v9.”开头的请求不下发明ocpa广告 |
| `AppWhiteListFilter` | AppWhiteListFilter | 桌面文件夹白名单过滤，考虑到用户体验，只有个别app才能出 |
| `OcpxConsumeFlowPacingController` | OcpxConsumeFlowPacingController | 流控过滤，是否过滤规则数据由调价侧维护，逻辑是根据广告计划 * 媒体 粒度对应的当日期望消耗分布曲线和当日总消耗及5分钟内实时消耗情况，对广告进行下发控制。  BudgetSmoothController与OcpxConsumeFlowPacingController是互斥关系，只会生效OcpxConsumeFlowPacingController 以上过滤在引擎侧召回广告 生效，进guyu前的过程阶段 |
| `BrowserSugRetriever` | BrowserSugRetriever | 浏览器sug召回 |
| `RecentlyDispensedAppIdFilter` | 最近下发应用过滤 | 最近下发应用过滤（浏览器、内容中心） |
| `UnionSmbReduceFilter` | UnionSmbReduceFilter | 联盟对小米设备下smb流量控制 如果是小米设备，且广告命中配置：union.smb.xiaomi.device.media.switch，且分桶配置为false，则过滤对应广告 如果非小米设备，且广告命中配置：union.smb.nonxiaomi.device.media.switch，且分桶配置为false，则过滤对应广告 |
| `OfflineRecommendPreFilter` | 协同预过滤 | 当前应用下进行行业、一级分类过滤 |
| `HourBlackListFilter` | HourBlackListFilter | 黑暗时间不推送，通知栏特殊逻辑 |
| `SensitiveWordFilter` | 广告敏感词过滤 | 广告敏感词过滤 |
| `RichMediaAdPreFilter` | RichMediaAdPreFilter | 富媒体过滤（供参考信息：4.31和4.79过滤不符合规格的广告） |
| `RecentlyExposePushAppFilter` | RecentlyExposePushAppFilter | 通知栏最近应用曝光过滤 |
| `DesktopFolderAppIdFilter` | DesktopFolderAppIdFilter | 预装应用过滤 |
| `SearchEducationCategoryFilter` | SearchEducationCategoryFilter | 某些词只出教育行业 |
| `CurrentAppFilter` | 当前APP广告过滤 | 详情页当前应用不出自己 |
| `MaterialTextBlackTagIdListFilter` | MaterialTextBlackTagIdListFilter | 主题画报 图里有黑名单词不让出  |
| `DesktopFolderDeletedFilter` | DesktopFolderDeletedFilter | 桌面文件夹 用户删除过app，则不出 |
| `TopDeviceAdFilter` | TopDeviceAdFilter | 高端机过滤（定期更新和释放） |
| `SearchKeywordExactFilter` | SearchKeywordExactFilter | 精准、短语匹配过滤 |
| `NegativeWordsFilter` | 否定词过滤 | 否词过率 |
| `RecentlyExposePushAdFilter` | RecentlyExposePushAdFilter | 通知栏最近曝光ad过滤 |
| `RecentlyExposedAdIdFilter` | 最近曝光广告过滤 | 最近曝光广告过滤（小米MIUI视频、画报、联盟、全搜、浏览器） |
| `MMSAppDownloadAdsFilter` | MMSAppDownloadAdsFilter | 短信场景针对配置的拉活pt过滤拉新下载类广告，针对拉新pt增加已安装过滤 |
| `SearchTopNFilter` | SearchTopNFilter | 搜索场景 TopN截断（目前仅针对游戏IAA生效） |
| `FeatureDisPageFilter` | 精品分页过滤 | 精品首页不同页面app需要有差异 |
| `ExtraNegativeFilter` | ExtraNegativeFilter | 字节系否词过滤 |
| `RecentlyDispensedAdIdFilter` | 最近下发广告过滤 | 最近下发广告过滤（小米MIUI视频、全局搜索、浏览器） |
| `ContextBasedMaterialLevelFilter` | 基于语境的素材等级过滤 | 小米视频基于上下文语境的素材等级过滤 |
| `FeatureCategoryLevelFilter` | FeatureCategoryLevelFilter | 广告主定向类目过滤，目前只作用在1.24.4.5-商店精品分类的位置上，如果emi下发的广告中没有[分类精品]这个标记则会过滤，标记的赋值逻辑问了下相关同学暂时没人了解背景了 |
| `DetailPageTargetDeliverFilter` | DetailPageTargetDeliverFilter | 详情页广告位、针对详情页包名的定向拉黑（一二级行业、包名维度），背景是游戏想优化在详情页的投放效果，需要拉黑不相关或者效果差的应用的详情页，因此销售侧提出了这个需求定投详情页ssp配置说明  |
| `DesktopFolderSourcePackageFilter` | DesktopFolderSourcePackageFilter | 桌面预装广告位、根据请求中的包名过滤 |
| `DesktopFolderTrafficReuseRetriever` | DesktopFolderTrafficReuseRetriever | 桌面旧版本广告位召回，复用26pt |
| `PersonalizedClosedAppFilter` | PersonalizedClosedAppFilter | 个性化开关关闭的用户不推荐敏感类app（主要是社交类，有一个配置list） |
| `SearchGuideGameFilter` | SearchGuideGameFilter | 搜索引导页游戏白名单过滤(4.64只能出游戏） |
| `MustHavePlacementTypeCategoryFilter` | MustHavePlacementTypeCategoryFilter | 装机必备 除了12pt以外，只能出白名单里的ad |
| `VoiceAiInstalledFilter` | VoiceAiInstalledFilter | 小爱已安装过滤 |
| `GameNaturalChannelFilter` | GameNaturalChannelFilter | 游戏自然量渠道过滤@安康 |
| `UnionParallelOnlineRankerV2` | UnionParallelOnlineRankerV2 | de缓存不了全量的广告，按需缓存，如果一个广告一直没有投放出去就从缓存中清除，等能出的时候异步加载，异步加载过程产生的gap就是这个过滤 |
| `CommonParallelOnlineRankerV2` | CommonParallelOnlineRankerV2 | de缓存不了全量的广告，按需缓存，如果一个广告一直没有投放出去就从缓存中清除，等能出的时候异步加载，异步加载过程产生的gap就是这个过滤 |
| `MMSAppIdDeduplicator` | 短信广告应用去重 | 短信广告应用去重 |
| `BrowserSugSelector` | 富媒体后_指定广告数量选择过滤 | 优先出品牌词白名单内的广告，其他随便出 |
| `PlacementTypeAppWhiteListFilter` | 渠道白名单过滤 | 欢迎回来，配置的app才出 |
| `CpdAdAppReplacementInstalledFilter` | CpdAdAppReplacementInstalledFilter | 一键换机已安装过滤 |

## 排序

共 12 条过滤码：

| 过滤码 | 中文名称 | 解释 |
|---|---|---|
| `OcpxOutputPostRanker` | OcpxOutputPostRanker | 排序过滤，涉及粗排、精排（含策略出价），要根据看板细拆一下。 |
| `AppIdDeDuplicator` | 广告应用去重 | 按pecpm去重 |
| `AppIdPerDspDeDuplicator` | AppIdPerDspDeDuplicator | dsp x appid维度按pecpm去重 |
| `jointProcessor` | joinProcessor | appid去重和相似icon去重，优先保留高ecpm的广告，其中相似icon去重指的是比如抖音和抖音极速版，快手和快手极速版，icon相似会去重 |
| `RtaPostRanker` | RtaPostRanker | 以下两类广告会被过滤 本次请求广告主拒绝的token对应广告 小于亿米底价的广告（小于1出价系数×亿米出价） |
| `NaiveSelector` | 简单选择过滤 | 根据媒体要的广告个数，按pecpm进行截断 |
| `NaivePerDspSelector` | NaivePerDspSelector | 每个物理dsp按pecpm保留剩下n个ad |
| `EcpmSelector` | ecpm阈值选择过滤 | 根据配置的pecpm进行过滤，ecpm特别低时会过滤 |
| `CustomerIdPerDspDeDuplicator` | CustomerIdPerDspDeDuplicator | 账户级别去重，按dsp x 账户去重 |
| `FeatureAppIdDeDuplicator` | FeatureAppIdDeDuplicator | 商店首页4.1和a.1的appid去重 |
| `InternalGlobalGspSelector` | InternalGlobalGspSelector | 去重过滤，根据配置：single.tagId.global.appId.dedup，命中配置流量，根据appId去重广告 |
| `CtrSelector` | ctr阈值选择过滤 | 根据配置的ctr进行过滤 |

## EMI

共 3 条过滤码：

| 过滤码 | 中文名称 | 解释 |
|---|---|---|
| `BudgetAllocationController` | 预算复用控制 | 配置预算复用比例 |
| `BudgetControlController` | 预算限制控制 | 为了保证不超投（针对所有计划），当预算低于一定额度之后，控制下发概率，配置下发概率随预算额度梯度递减。 当余额大于等于200时不进行控制，当余额小于200时根据余额以及可投放的时间进行流控。余额按min(账户预算-账户消耗，计划预算-计划消耗，账户余额)来计算 |
| `BudgetSmoothController` | 预算平滑控制 | 保证预算在全天更均匀的分配投放（针对设置“均匀投放”的计划），会根据创意的历史投放和当前投放情况，进行一定程度的下发控制，一般通过概率控制 |

## 下发

共 2 条过滤码：

| 过滤码 | 中文名称 | 解释 |
|---|---|---|
| `resultAd` | resultAd | 广告下发到adx的打点（很棒！说明ad的竞价能力很强） |
| `AdxAppstoreAdCntSelector` | AdxAppstoreAdCntSelector | 避免de返回adx广告数量太多造成超时上线的一个截断（阈值200），只有商店18个迁移了adx新架构的位置有该过滤，因为给新架构的rpc链路变长，超时风险较高 |

## 未分类

共 84 条过滤码：

| 过滤码 | 中文名称 | 解释 |
|---|---|---|
| `SearchNoResultStatusSelector` | SearchNoResultStatusSelector | ：商店搜索空结果页广告位，如果能从搜索侧获取到自然结果，则不返回广告 |
| `ExcludeCpxAdPreFilter` | ExcludeCpxAdPreFilter | 如果流量命中配置：(取消pt级别的cpx预算策略)，则删除配置中对应PT下的非OCPX广告 |
| `SearchSessionFilter` | SearchSessionFilter | sug下载进入结果页后的appId去重逻辑，如果是在sug页下载的广告，跳转到结果页后，根据配置：，当sug页下载广告的dsp在sugDsp配置列表时，按照rate比例过滤同appId的searchDsp下的广告 |
| `InexpensiveDeviceIAPFilter` | InexpensiveDeviceIAPFilter | 低端机不出iap付费游戏广告 |
| `AdxGameAdCntSelector` | AdxGameAdCntSelector | 商店详情页，限制广告返回数量：广告个数小于配置时不做限制，大于时仅添加游戏IAP类的广告，且个数不能超过 |
| `GameCategoryFilter` | 游戏种类过滤 | 过滤掉非游戏的广告，来自总榜的请求，返回所有游戏类别广告。若是来自虚拟分类的请求，则返回对应二类级别的广告 |
| `FinanceL1CategoryDeDuplicator` | 金融广告去重 | 一次请求限制下发金融广告的数量，只保留指定的金融广告数，满足用户体验 |
| `AppStoreParallelOnlineRankerV2` | AppStoreParallelOnlineRankerV2 | 请求RTA 和guyu，并进行过滤和排序： 针对guyu的结果：过滤guyu移除[discard]或者调用失败[computationError]的广告 针对RTA的结果：过滤RTA要删除的广告 |
| `CategoryCustomizedSelector` | CategoryCustomizedSelector | 1.24.4.115、1.24.4.116逻辑：自然量换量逻辑，根据请求中的自然量appId列表，选择广告填充 |
| `DownloadQueueFilter` | 正在下载_下载完成应用过滤 | 将请求中包含正在下载、下载完成的app过滤 |
| `SearchGameCategoryDeDuplicator` | SearchGameCategoryDeDuplicator | 1.24.4.14、1.24.4.15 - 根据apollo配置appstore.search.game.ratio的比例，如果自然结果前五个有一半是游戏，则仅保留游戏广告 和 精准词广告下发 |
| `SubscribeAppStatusFilter` | SubscribeAppStatusFilter | 预约广告状态过滤： 如果商店版本 < 40004320，不下发预约类广告 如果用户已预约某个app，不下发对应的预约广告 |
| `CategoryBoardDisPageFilter` | 榜单分页过滤 | 在请求榜单第一页之后的广告时，过滤掉之前页已经下发的广告 |
| `GamePopularCategoryFilter` | 非游戏广告过滤 | 类别过滤.过滤掉非游戏类app 4.32 |
| `SearchWithResultStatusSelector` | SearchWithResultStatusSelector | 搜索结果过滤：如果获取到的自然量结果为空，则过滤所有广告 |
| `TodayPageRankListSelector` | TodayPageRankListSelector | 1.24.4.108-自然结果换量逻辑：根据请求中的自然结果appId列表，选择列表中的广告进行填充 |
| `KeywordAndScoreOcpdRankerV2` | KeywordAndScoreOcpdRankerV2 |  |
| `ProductionTypeFilter` | ProductionTypeFilter | 应用类型过滤： 命中filtered.non.app.ad.switch配置，过滤非APP类[appId<=0]的广告 命中filtered.fast.app.ad.switch配置，过滤快应用广告 |
| `ExcludeAppFilter` | 请求包含appId过滤 | 媒体方发送的请求包含appIdList，将这些appId对应的adid过滤掉 |
| `DownloadRecommendGameAppFilter` | 游戏_非游戏区分请求过滤 | 游戏分类只出游戏类, 其他类只出其他类。4.45、4.23 |
| `GameL2CategorySearchDeDuplicator` | 游戏二级分类搜索去重 | 游戏二级分类广告个数控制：如果广告的个数 > 配置max_app_num 的个数，则过滤掉不在自然结果二级分类 且 命中配置game_prefer_l2_category_appids 的appId的广告 |
| `SearchAdKeywordRankerV2` | SearchAdKeywordRankerV2 |  |
| `FeatureParallelOnlineRankerV2` | FeatureParallelOnlineRankerV2 |  |
| `AppStoreGameCategoryFilter` | 应用商店游戏种类过滤 | 过滤掉非游戏的广告，来自总榜的请求，返回所有游戏类别广告。若是来自虚拟分类的请求，则返回对应二类级别的广告 |
| `ManualRecommendFilter` | 编辑推荐过滤 | 将出现在商店编辑推荐名单中的app过滤掉 |
| `SearchResultAdKeywordRankerV2` | SearchResultAdKeywordRankerV2 |  |
| `ReturningMustHaveSelector` | 装机必备二次广告选择过滤 | 装机必备二次广告选择过滤 |
| `ChannelPackageFilter` | ChannelPackageFilter | 1.24.5.9 - 渠道包过滤：如果广告的appChannel不为空，则过滤 |
| `GameOperationAppFilter` | 游戏操作APP过滤 | 根据不同的板块种类（热门游戏，动作游戏，休闲游戏），将在对应的游戏top榜单中过滤掉app id |
| `MustHaveSimNameAppIdDeduplicator` | 装机必备相似app名称去重 | 装机必备相似app名称去重.eg:今日头条、今日头条极速版 |
| `NewFeatureDisPageFilter` | NewFeatureDisPageFilter | 1.24.6.8 - 分页去重：如果本次广告请求非第0页，则过滤掉前几页已经下发过的emi二级行业的广告。 |
| `CarouselRanker` | CarouselRanker |  |
| `GameDeviceFilter` | 游戏机型过滤 | 游戏组根据自己指定的机型配置，不符合的广告将会被过滤 |
| `HighRiskReuseFilter` | HighRiskReuseFilter | 高风险人群禁止预算复用 |
| `NewFeatureSelector` | NewFeatureSelector | 1.24.6.8 - 根据emi二级行业的平均ecpm，对二级行业类别进行排序，每个二级行业下最多保留5个广告，如果该行业下广告个数 < 3 ，则不召回对应行业的广告 |
| `WhiteListFilter` | Apollo白名单过滤 | 如果没有Apollo白名单，则不过滤。如果存在白名单，只返回符合白名单配置的广告（互三广告素材审核过滤） |
| `TargetedAppCategoryFilter` | 分类定向过滤 | 不过滤的情况：没有定向或者一级分类定向满足，没有二级分类定向。 过滤的情况：一级分类定向不满足或者二级分类定向不满足 |
| `RichMediaAdRankerV2` | RichMediaAdRankerV2 |  |
| `CategoryBoardRanker` | CategoryBoardRanker |  |
| `TargetedAppFilter` | App定向过滤 | 过滤掉目标app是空的并且目标app中不包括请求的app id的广告 |
| `WhiteListAppInstalledFilter` | WhiteListAppInstalledFilter | 外投白名单adid跳过已安装过滤（主要1.24.5.17） 已安装过滤白名单，如果配置outer.ref.white.list.jump.installed.filter.switch开关未开启，走通用已安装过滤逻辑，否则，命中配置：jump.installed.filter.white.ad.id.list 的广告不会被已安装过滤 |
| `MaterialTypeFilter` | MaterialTypeFilter | 根据请求流量中限定的素材类型[即mt]，如果广告中不存在对应mt下的素材，则被过滤 |
| `DesktopFolderPreloadSelector` | DesktopFolderPreloadSelector | 桌面文件夹云预装广告位个数过滤，云预装广告位默认值为2个，计算云预装广告位的返回值 = 默认值 - 已安装个数 - 已删除个数。 根据返回值对广告候选集截断。 |
| `PackageInstallerDeviceFilter` | PackageInstallerDeviceFilter | 安装器，如果请求的设备命中配置[apollo- package.installer.wali.target.device.model]（m2007j1sc,mi 10 pro,mi mix 3 5g,mix 3,mix 3 the palace museum edition,M2006C3LC,M2007J22C,M2007J17C,M2012K11AC,M2104K10AC,21091116C），则过滤所有非wali的广告，否则过滤所有wali的广告 |
| `NaturalAppInstalledFilter` | 自然量已安装过滤 | 过滤掉用户已经安装的自然量 |
| `DesktopFolderRankerV2` | DesktopFolderRankerV2 | de缓存不了全量的广告，按需缓存，如果一个广告一直没有投放出去就从缓存中清除，等能出的时候异步加载，异步加载过程产生的gap就是这个过滤 |
| `AssetValidPostRanker` | AssetValidPostRanker | 融合投放PT，DE服务中素材MT过滤-由于de和index 两个服务的素材缓存数据可能不一致，因此在DE多做一次过滤避免无填充：如果广告对应PT命中配置：，且请求中支持的MT 与 广告本身挂载素材的MT无交集，则过滤 |
| `AbnormalNatureAppFilter` | 异常自然量APP过滤 | 桌面文件夹过滤掉异常的自然量APP，需要有自然量，需要标准 |
| `PackageInstallerCurInstallPackageFilter` | PackageInstallerCurInstallPackageFilter | 安装器，过滤用户当前正在安装的应用 - 根据请求参数packageName |
| `ParallelNovelMediaAdPriceRanker` | ParallelNovelMediaAdPriceRanker | de缓存不了全量的广告，按需缓存，如果一个广告一直没有投放出去就从缓存中清除，等能出的时候异步加载，异步加载过程产生的gap就是这个过滤 |
| `NovelCloseAdFilter` | NovelCloseAdFilter | 所有ranker的过滤均为未命中DE广告缓存导致的，算法或RTA过滤有单独的过滤项 |
| `ParallelSplashRanker` | ParallelSplashRanker | de缓存不了全量的广告，按需缓存，如果一个广告一直没有投放出去就从缓存中清除，等能出的时候异步加载，异步加载过程产生的gap就是这个过滤 |
| `PackageInstallerOnlineRankerV2` | PackageInstallerOnlineRankerV2 | de缓存不了全量的广告，按需缓存，如果一个广告一直没有投放出去就从缓存中清除，等能出的时候异步加载，异步加载过程产生的gap就是这个过滤 |
| `ThemeMiuiLiteFilter` | ThemeMiuiLiteFilter | 主题位置，如果是miuiLite 版本的请求，则不下发视频类广告 |
| `DefaultOcpdTrafficReuseRetriever` | DefaultOcpdTrafficReuseRetriever | 26PT复用广告位过滤，复用26pt广告tagId配置： ，如果26pt广告不在apollo配置白名单中：reuse_26pt_appids， 或 广告不是App类的ocpx广告，则过滤 |
| `DownloadManagerHotRankBlackListFilter` | 下载管理器热榜黑名单过滤 | 将下载管理器热榜的黑名单中的app过滤 |
| `CustomerIdDeDuplicator` | 广告账户去重 | 按照广告候选集的遍历顺序，对于投放同一个广告账户的创意，只保留第一个 |
| `DevicePostFilter` | DevicePostFilter | 根据用户请求的安卓版本和cpu参数，请求商店app信息，判断app是否适配设备，如果不适配则过滤 |
| `RecentlyClickedAdIdCpcFilter` | RecentlyClickedAdIdCpcFilter | 对于CPC广告，如果用户在设定时间内点击过该广告（8小时内），则过滤，时间间隔配置： |
| `ApkInterceptorRanker` | ApkInterceptorRanker | de缓存不了全量的广告，按需缓存，如果一个广告一直没有投放出去就从缓存中清除，等能出的时候异步加载，异步加载过程产生的gap就是这个过滤 |
| `NaturalAppBlacklistFilter` | 自然量黑名单过滤 | 桌面文件夹过滤掉在配置黑名单app（媒体确认）中的自然量 |
| `NegativeBlackListFilter` | NegativeBlackListFilter | 如果流量与搜索词命中配置：query.application.location，则过滤对应的appId（屏蔽搜索词拼多多） |
| `TzScoreFilter` | TzScoreFilter | 真机识别过滤 tzScore召回过滤，根据配置，如果用户的tzScore打分高于配置分数（3），则过滤对应app下的广告 |
| `DeviceFilter` | 适配机型过滤 | 根据 AndroidSdkVersion && CpuArchitecture 来对应用是否适配机型进行过滤 |
| `VoiceAiAppFilter` | VoiceAiAppFilter | 小爱下载App过滤，过滤掉请求中要求过滤的包名 |
| `WxMiniPreFilter` | WxMiniPreFilter | 微信小程序云控过滤。如果流量未命中配置：，过滤微信小程序类的广告 |
| `MiPaySelector` | MiPaySelector | 如果广告price字段 < 5000，则过滤 |
| `AssetOptimizePolisher` | AssetOptimizePolisher | 融合投放素材过滤，如果融合投放的广告没有成功选取到对应素材，则过滤该广告 |
| `CloudBackupFilter` | 云备份过滤 | 过滤掉备份不包含的package name |
| `BrowserInfoFeedParallelOnlineRankerV2` | BrowserInfoFeedParallelOnlineRankerV2 | de缓存不了全量的广告，按需缓存，如果一个广告一直没有投放出去就从缓存中清除，等能出的时候异步加载，异步加载过程产生的gap就是这个过滤 |
| `NewHomeParallelOnlineRankerV2` | NewHomeParallelOnlineRankerV2 | de缓存不了全量的广告，按需缓存，如果一个广告一直没有投放出去就从缓存中清除，等能出的时候异步加载，异步加载过程产生的gap就是这个过滤 |
| `PhoneVideoChildrenFilter` | PhoneVideoChildrenFilter | 小米视频儿童版本过滤，如果请求中的分类参数[category]，属于儿童内容[apollo配置-phonevideo.children.categories]（children2,s_cartoon,parentson,children,cartoon），且广告的appId不在【apollo配置-phonevideo.children.no.shield.appid】中（小红书,知乎,微博，脉脉），则过滤掉emi一级行业为11 或 59 的广告（社交） |
| `RecentlyDispensedAssetIdFilter` | RecentlyDispensedAssetIdFilter | 最近下发过滤，根据配置的时间：RecentlyDispensedAssetIdFilter.key（1min或2min），如果请求的imei在该时间内下发过某个广告的所有素材，则过滤该广告。 |
| `PushAppIdDeDuplicator` | PushAppIdDeDuplicator | appid去重，根据白名单配置，apollo-push.appId.deDuplicator.whiteList 【未配置】 和 abram- push_config 中replaceApps 字段，得到可以不去重的appId白名单，未命中白名单的广告需要去重处理  分DSP去重，如果apollo - push.appId.deDuplicator.dsp.on 开关开启，未在白名单的广告，每个dsp下每个appId仅保留一个广告 如果分DSP去重未开启，未在白名单的广告，每个appId下仅保留一个广告 |
| `RecentlyConfigDispensedAppIdFilter` | RecentlyConfigDispensedAppIdFilter | 根据配置：RecentlyConfigDispensedAppIdFilter.key，如果用户在时间窗口内，下发的appId的次数大于配置的阈值（1/5/10），则过滤对应的appId |
| `ParallelBrowserSugRanker` | ParallelBrowserSugRanker | de缓存不了全量的广告，按需缓存，如果一个广告一直没有投放出去就从缓存中清除，等能出的时候异步加载，异步加载过程产生的gap就是这个过滤 |
| `PhoneVideoPatchDurationSelector` | 视频广告时长选择过滤 | 选择符合请求时长的广告（不应该超过请求的广告时间） |
| `PushSimilarAdScoreDeDuplicator` | PushSimilarAdScoreDeDuplicator | 通知栏相似文案去重，相似比例限制，根据配置push.similar.ad.score.exp，获取广告相似分数阈值，如果当前候选集，与最近1天内下发的push广告的相似分 大于阈值（0.7），则过滤广告 |
| `RecentlyClickedPushAdFilter` | RecentlyClickedPushAdFilter | 通知栏最近点击过滤，通知栏过滤最近点击过的adid |
| `CampaignIdDeDuplicator` | 广告计划去重 | 按照广告候选集的遍历顺序，对于投放同一个广告计划的创意，只保留pecpm第一个 |
| `AppUninstalledExclH5Filter` | AppUninstalledExclH5Filter | 联盟低CVR广告位拉新广告过滤，针对cvr（下载/点击）较低的upid（0.01%），按照比例[union.cvr.fill.percent] -20%流量正常召回广告，剩余80%流量走该filter，仅召回拉活广告[已安装 + 最近有下载] + H5类广告，过滤拉新广告。 |
| `UnionAssetAuditFilter` | UnionAssetAuditFilter | 联盟快手流量专用：仅保留快手素材审核通过的广告 |
| `UnionAssetFilter` | UnionAssetFilter | 联盟融合投放素材标记过滤，融合投放pt下的广告对应appId，是否有素材可下发，没有则过滤 |
| `UnionMutualPushBoxFilter` | UnionMutualPushBoxFilter | 联盟互推盒子广告位1.11.k.1专用：仅保留快游戏类型的广告 |
