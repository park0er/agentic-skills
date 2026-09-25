---
name: xirang-ad-effect-field-dictionary-low-freq
description: query_xirang_ad_effect 低频字段词典（请求占比 <5%）——低频维度（oper_industry_level1/billing_type/conv_type 等 50+ 个）和低频指标（raw_ecpm/深层转化/留存/IAP/IAA/游戏联运等 200+ 个）。仅当主词典查不到时使用。
---

# 广告效果看板-息壤版 低频字段词典（query_xirang_ad_effect）

> 本文档收录请求占比 <5% 的维度和指标字段。高频/中频字段请查阅 `./xirang_ad_effect_field_dictionary.md`。


---

## 一、低频维度字段
> 维度字段"枚举值"列为空的字段，其完整枚举请查阅 `./enums/xirang_ad_effect_enums_misc.md` 对应章节。

| 字段名 | 中文名 | 枚举值 / 外接引用 |
|---|---|---|
| `oper_industry_level1` | 运营一级自定义行业, 运营行业 | 如 `IAA买量类` |
| `promote_goal` | 营销目的, 推广目标 | `0`=未知、`1`=拉新、`2`=拉活、`3`=召回、`4`=预约 |
| `ad_version` | 广告版本 | `3.0`=3.0、`4.0`=4.0、`unknown`=unknown |
| `ua_id` | 联盟应用Id, uaid | 如 `1002496` |
| `union_source_name` | 联盟渠道来源名称, 联盟来源 | 如`游戏`、`第三方APP`、`快应用`、`快游戏` |
| `install_status` | 下发安装状态 | `0`=未安装、`1`=已安装、`-1`=未知 |
| `industry_level2` | 效果二级行业, 二级行业 | `0`=其他、`14`=单品电商、`15`=其他、`16`=保险、`17`=股票基金 |
| `sale_email` | 销售cube, 销售人员 | 如`caiyuwei@xiaomi.com` |
| `union_developer_id` | 联盟开发者Id | 如 `4228` |
| `dsp_level2` | 二级DSP | 如 `xiaomi.ocpa` |
| `dsp_level1` | 一级DSP | `dsp`=dsp、`brand`=品牌、`effect`=效果 |
| `platform_type` | emi投放范围 | `商店`=商店、`米盟`=米盟、`非商店`=非商店、`unknown`=unknown |
| `rta_token` | rtaToken, RTA Token | 如 `vip_a` |
| `emi_install_directed` | emi安装定向, 安装状态定向 | `0`=null(品牌广告)、`1`=未安装、`2`=已安装、`3`=已卸载、`-1`=不限 |
| `ad_report_id` | adReportId, 报告ID | 如 `44769185` |
| `display_type` | 版位, 展示类型 | `0`=（空）、`2`=视频、`4`=焦点图、`6`=插屏、`8`=应用商店 |
| `billing_type` | 计费类型, 计费方式 | `0`=OTHER、`1`=CPM、`2`=CPC、`3`=CPD、`4`=SCHEDULER |
| `is_cache` | 是否缓存, 缓存广告 | `0`=非缓存、`1`=缓存、`-999`=未知 |
| `is_personalized_closed` | 是否关闭个性化开关 | `true`=是、`false`=否 |
| `industry_level1` | 效果一级行业, 一级行业 | `0`=其他、`2`=KA电商+LA电商、`3`=金融服务、`4`=工具+招聘、`5`=旅游 |
| `conv_type` | 回传事件类型, 事件类型 | `0`=unknown、`1`=自定义激活、`2`=自定义注册、`3`=自定义留存、`4`=安装完成 |
| `is_video_asset` | 是否视频素材 | `0`=否、`1`=是、`-1`=未知 |
| `material_type` | 下发素材规格 | `1`=大图、`2`=小图、`3`=组图、`4`=竖图、`5`=横版视频 |
| `ad_derive_type` | adid生成方式, 衍生类型 | `1`=本体、`200`=素材拓展、`300`=ICON拓展、`-1`=未知 |
| `asset_id` | assetid, 素材包ID | 如 `100000000` |
| `model_tagid_group` | 模型广告位分组, 广告位模型分组 | `1`=商店搜索、`2`=商店精品、`3`=非商店应用分发、`4`=非商店信息流、`5`=联盟 |
| `sub_account_type` | 效果子账户类型 | `1`=直客、`2`=代理 |
| `emi_material_type` | 本体素材规格, 素材规格 | `1`=大图、`3`=组图、`5`=横版视频、`7`=开屏图片、`9`=图标 |
| `fresh_ad` | 是否新广告, 新广告标记 | `true`=true、`false`=false |
| `ad_age_bucket` | 素材创建生命周期 | `0`=0-7天（含）、`8`=8-21天（含）、`-1`=未知、`22`=22-35天（含）、`36`=36-65（含） |
| `asset_img_material_ids` | 图片ID | 如`1` |
| `asset_source` | 素材来源 | `1`=广告主EMI上传素材、`2`=商店富媒体素材库、`3`=商店详情页素材、`4`=ssp配置素材、`5`=融合投放衍生素材（非商店） |
| `asset_video_material_ids` | 视频ID |  如`1`  |
| `is_vango` | 是否梵高衍生 | `0`=否、`1`=是、`-1`=未知 |
| `asset_derive_type` | 素材衍生类型 | `1`=抖动+光亮、`2`=弹幕样式、`4`=热气效果、`5`=固定金额放大抖动、`6`=横转竖 |
| `union_style_id` | 联盟广告样式 | 如 `1`|
| `traffic_ad_source` | 流量优选广告来源 | `0`=非流量优选广告、`1`=emi勾选流量优选、`2`=emi勾选智能创意优选、`3`=ssp配置流量优选白名单、`4`=emi勾选增量智投 |
| `ad_attribution_mark` | 重定向类型 | `1`=未知、`2`=重定向广告、`3`=次留补效广告、`4`=拉新定向拓展 |
| `is_rta` | 是否Rta广告, RTA | `0`=否、`1`=是、`-1`=未知 |
| `landing_page_type` | 落地页模板类型 | `1`=E米个性化详情页、`2`=商店详情页、`3`=商店miniCard、`4`=商店个性化详情页、`5`=商店悬浮窗 |
| `product_type` | 推广产品类型, 推广类型 | `0`=未知、`1`=网址、`2`=应用下载、`4`=Deeplink、`8`=自定义下载 |
| `effect_settle_type` | 效果区域结算方式 | `不结算`=不结算、`内部结算`=内部结算、`正常结算`=正常结算 |
| `up_id` | 联盟广告位, upid | 如 `15000001`|
| `union_access_model` | 联盟接入方式 | `0`=0-SDK、`1`=1-API、`3`=系统开屏、`5`=系统开屏、`6`=JS-SDK |
| `brand_region` | 品牌区域 |如`全国` |
| `tag_status` | 广告位状态 | `0`=活跃、`1`=关闭、`2`=废弃 |
| `ad_form_id` | 广告位形式 | `1`=信息流、`3`=开屏、`5`=文字链、`7`=情景、`9`=非标 |
| `env` | 集群, 服务集群 | `C3`=C3、`AKSRV`=AKSRV、`unknown`=unknown |
| `ad_position_id` | 排期位置, 版位ID | `99`=banner、`101`=小米视频－播放页-前贴片、`102`=电视盒子－播放页-前贴片、`103`=电视画报、`104`=盒子视频广告,前贴 |
| `traffic_support_status` | 流量扶持状态, 扶持标记 | `true`=扶持、`false`=不扶持 |
| `scenario_type` | 投放场景 | `0`=日常投放、`1`=增量投放 |
| `incremental_status` | 增量智投状态 | `0`=否、`1`=是 |
| `is_auto_optimize` | 是否自动优化 | `0`=否、`1`=是 |
| `key_action_analysis_type` | 关键行为分析类型 | `0`=其他、`1`=非游单出价、`2`=非游双出价、`3`=非游每日留存、`4`=快应用关键行为 |
| `key_action_type` | 关键行为类型 | `0`=其他、`100`=app打开频次、`101`=app使用时长、`102`=ipu次数、`103`=ecpm |
| `deep_key_action_type` | 深层关键行为类型 | `0`=其他、`100`=app打开频次、`101`=app使用时长(秒)、`102`=ipu次数、`103`=ecpm(丝) |
| `key_action_threshold` | 关键行为阈值 | 数值，如 `0`~`90000` |
| `deep_key_action_threshold` | 深层关键行为阈值 | 数值，如 `0`~`90000` |
| `ad_material_product_type` | AI素材产品类型 | `1`=数字人、`2`=文生图、`3`=模版制图、`-1`=未知 |
| `ad_material_model_type` | AI素材模型来源 | `1`=阿里、`2`=技术委、`3`=梵高自研、`4`=豆包、`-1`=未知 |
| `is_deeplink` | 是否deeplink广告 | `0`=否、`1`=是、`2`=未知 |
| `is_derive_enable` | 是否开启衍生 | `0`=关闭、`1`=开启、`-1`=null |
| `asset_title` | 素材标题 | 如 `招聘季` |
| `asset_level` | 素材等级 | `0`=未知、`1`=素材等级L1、`2`=素材等级L2、`3`=素材等级L3、`4`=素材等级L4 |
| `material_source` | 物料来源 | `[]`=[]、`[1]`=本地上传、`[2]`=API上传、`[4]`=视频转换工具上传、`[5]`=衍生上传 |
| `ad_support_status` | 广告扶持状态 | `UNKNOWN`=不扶持、`REGULAR_BOOST`=扶持、`DOWNGRADED_BOOST`=扶持降级 |
| `is_placement_ad` | 是否PT广告, 排期广告 | `0`=否、`1`=是 |
| `is_zrl_billing` | 是否zrl扣费, 自然量扣费 | `0`=否、`1`=是 |
| `is_ai_landing_page` | 是否AI落地页 | `0`=否、`1`=是、`-1`=未知 |
| `landing_page_id` | 落地页ID | 如 `4` |
| `is_emi_landing_page` | 是否EMI落地页 | `0`=否、`1`=是、`-1`=未知 |
| `conv_tracking_type` | 回传追踪类型 | `0`=无转化跟踪or非ocpx、`1`=API统计方案、`2`=API上报方案、`3`=小米数据、`4`=JS埋点 |
| `tracking_type` | 追踪类型, 归因类型 | `0`=无转化跟踪or非ocpx、`1`=API统计方案、`2`=API上报方案、`3`=小米数据、`4`=JS埋点 |
| `union_category_name` | 联盟行业名称 | 如`新闻` |
| `union_is_api_bidding` | 是否bidding | `0`=否、`1`=是、`-999`=unknown |
| `u_traffic_type` | 是否联盟冷启流量 | `0`=未判断流量、`1`=常规流量、`2`=冷启动流量 |
| `device_type` | 设备类型 | `平板`=平板、`手机`=手机、`unknown`=unknown |
| `rerank_appid` | 重排应用ID | 如 `332`|
| `rerank_mark` | 重排标识 | `true`=重排、`false`=未重排 |
| `rerank_times` | 重排次数 | 如`1` |
| `rerank_seq` | 重排seqNum | 如`1` |
| `seq` | 下发seq | 如`1`  |
| `brand_industry_level` | 品牌行业 | 如`交通` |
| `brand_company_name` | 品牌公司名称 | 如`米家` |
| `dsp_region` | dsp区域 | 如`网服电商部` |
| `app_category_level1` | 应用一级分类 | `0`=unknown、`1`=金融理财、`2`=聊天社交、`3`=旅行交通、`4`=居家生活 |
| `download_channel` | 下载渠道 | `30`=30、`95`=95、`ms`=ms、`tt`=tt、`610`=610 |

**注意：此看板不支持搜索词（query/keyword/search query）维度查询。**

---

## 二、低频指标字段

> **Z/J 后缀含义**：`_z` = 转化点归因，`_j` = 计费点归因。若无特殊说明，默认使用 `_z` 后缀版本。

| 字段名 | 中文名 | 类型 | 公式说明 |
|---|---|---|---|
| `avg_pcvr_bill` | 平均pcvr_计费点 | derived | 总计pcvr_计费点 / 计费数 |
| `new_active_z` | 自定义新增激活(Z), 新增激活 | raw | — |
| `cvr_conv_deepconv_z` | deepCVR_浅层到深层转化率(Z) | derived | 深层目标转化数(Z) / 目标转化数(Z) |
| `active_retention_2day_z` | 自定义激活留存率(Z) | derived | 自定义留存(Z) / 自定义激活(Z) |
| `avg_pdeepcvrfix_conv_z` | 平均pdeepcvrFix_浅层转化点(Z) | derived | 总计pdeepcvrFix_浅层转化点 / 目标转化数(Z) |
| `iap_cost_z` | 付费成本(Z) | derived | emi效果收入 / 付费次数(Z) |
| `avg_target_cpa_view` | 平均目标出价_曝光 | derived | 总计目标出价_曝光 / 计费曝光 |
| `new_active_retention_2day_z` | 自定义新增激活留存率(Z) | derived | 自定义留存(Z) / 自定义新增激活(Z) |
| `avg_pdeepcvr_conv_z` | 平均pdeepcvr_浅层转化点(Z) | derived | 总计pdeepcvr_浅层转化点 / 目标转化数(Z) |
| `retention_z` | 自定义留存(Z), 次留 | raw | — |
| `new_active_cost_z` | 自定义新增激活成本(Z) | derived | emi效果收入 / 自定义新增激活(Z) |
| `iap_num_z` | 付费次数(Z) | raw | — |
| `avg_pctr_view` | 平均pctr_曝光 | derived | 总计pctr_曝光 / 计费曝光 |
| `iap_revenue_z` | 付费金额(Z) | raw | — |
| `reactive_z` | 首次拉活(Z) | raw | — |
| `avg_rta_ratio_view` | 实际RTA平均出价系数_曝光 | derived | 总计RTA出价系数_曝光 / 曝光数_分母 |
| `open_account_cost_z` | 开户成本(Z) | derived | emi效果收入 / 开户(Z) |
| `recall_z` | 召回(Z) | raw | — |
| `deeplink_success_click` | 计费点击_DP调起成功率 | derived | Deeplink调起成功 / 计费点击 |
| `cvr_bill_conv_j` | CVR_计费转化率(J) | derived | 目标转化数(J) / 计费数 |
| `raw_view` | 原始曝光, 去重前曝光 | raw | — |
| `avg_deep_target_cpa_deep_conv_z` | 平均深层目标出价_深层转化(Z) | derived | 总计深层目标出价(Z) / 深层目标转化数(Z) |
| `open_account_z` | 开户(Z) | raw | — |
| `reactive_cost_z` | 首次拉活成本(Z) | derived | emi效果收入 / 首次拉活(Z) |
| `register_retention_2day_rate_z` | 自定义注册留存率(Z) | derived | 自定义留存(Z) / 自定义注册(Z) |
| `cvr_pcoc_j` | CVR pcoc(J) | derived | 平均pcvrFix_计费点 / CVR_计费转化率(J) |
| `target_conv_num_j` | 目标转化数(J) | raw | — |
| `advv_z` | 广告主价值(Z), ADVV | raw | — |
| `purchase_z` | 购买(Z), 购买数 | raw | — |
| `bb_retention_7day_z` | 明激活明7日留存数(Z) | raw | — |
| `addiction_cost_z` | 关键行为成本(Z) | derived | emi效果收入 / 关键行为(Z) |
| `deep_advv_advv_rate` | 深层目标率完成度(Z) | derived | 深层广告主价值(Z) / 广告主价值(Z) |
| `cpc` | CPC, 单次点击成本 | derived | (emi效果+品牌+外部Dsp) / 计费点击 |
| `raw_fee_total` | 分成前收入, 分成前总收入 | derived | emi效果+品牌+外部Dsp |
| `addiction_z` | 关键行为(Z) | raw | — |
| `total_pltv_bill_user` | 总计pltv_业务口径_计费点 | raw | — |
| `iaa_revenue_24h_z` | 24小时变现金额(Z), 变现收入 | raw | — |
| `deepconv_cost_z` | 深层转化成本(Z), 深层CPA | derived | emi效果收入 / 深层目标转化数(Z) |
| `own_new_day_active_z` | 小米新增当日激活(Z) | raw | — |
| `download_success` | 下载成功 | raw | — |
| `avg_pltvfix_bill_user` | 平均pltvFix_业务口径_计费点 | derived | — |
| `fee_cash` | emi现金收入, 现金收入 | raw | — |
| `avg_pdeepcvrfix_bill` | 平均pdeepcvrFix_计费点 | derived | 总计pdeepcvrFix_计费点 / 计费数 |
| `avg_pdeepcvr_bill` | 平均pdeepcvr_计费点 | derived | 总计pdeepcvr_计费点 / 计费数 |
| `avg_pltv_bill_user` | 平均pltv_业务口径_计费点 | derived | — |
| `total_pltvfix_bill_user` | 总计pltvFix_计费点_业务口径 | raw | — |
| `conv_num_z` | 回传事件数(Z) | raw | — |
| `credit_z` | 授信(Z) | raw | — |
| `credit_cost_z` | 授信成本(Z) | derived | emi效果收入 / 授信(Z) |
| `deep_target_conv_num_j` | 深层目标转化数(J) | raw | — |
| `new_deep_billing_ratio_j` | 深层计费比(J) | derived | emi效果收入 / 深层广告主价值(J) |
| `bb_retention_2day_z` | 明激活明2日留存数(Z) | raw | — |
| `start_download_view` | CTR_曝光下载率 | derived | — |
| `new_deep_billing_ratio_z` | 深层计费比(Z) | derived | emi效果收入 / 深层广告主价值(Z) |
| `avg_deep_target_cpa_deep_conv_j` | 平均深层目标出价_深层转化(J) | derived | — |
| `deeplink_success` | Deeplink调起成功 | raw | — |
| `total_pdeepltv_conv_z` | 总计pdeepltv_浅层转化点(Z) | raw | — |
| `total_pdeepltvfix_conv_z` | 总计pdeepltvFix_浅层转化点(Z) | raw | — |
| `iap_num_24h_z` | 24小时付费次数(Z) | raw | — |
| `raw_click` | 原始点击, 去重前点击 | raw | — |
| `new_user_purchase_z` | 首单购买(Z) | raw | — |
| `iaa_arpu_24h_z` | 24小时变现ARPU(Z) | derived | 24小时变现金额(Z) / 24小时变现用户数(Z) |
| `bd_retention_2day_z` | 明激活暗2日留存数(Z) | raw | — |
| `cvr_bill_deepconv_z` | deepCVR_计费到深层转化率(Z) | derived | 深层目标转化数(Z) / 计费数 |
| `iaa_uv_24h_z` | 24小时变现用户数(Z) | raw | — |
| `iap_day_uv_day_z` | 当日付费人天(Z) | raw | — |
| `submit_z` | 完件(Z) | raw | — |
| `install_success` | 安装成功 | raw | — |
| `iap_num_7day_z` | 7日付费次数(Z) | raw | — |
| `iap_roi_24h_z` | 24小时付费ROI(Z) | derived | 24小时付费金额(Z) / emi效果收入 |
| `advv_j` | 广告主价值(J), ADVV(J) | raw | — |
| `iap_roi_7day_z` | 7日付费ROI(Z) | derived | 7日内付费金额(Z) / emi效果收入 |
| `own_acitve_z` | 小米打点激活(Z) | raw | — |
| `fee_dsp` | 外部Dsp收入, DSP收入 | raw | — |
| `bb_retention_lt7_cost_j` | 明激活明留存LT7成本(J) | derived | emi效果收入 / 明激活明7日内留存总数(J) |
| `cvr_click_download` | 点击下载率 | derived | 开始下载 / 计费点击 |
| `iaa_roi_24h_z` | 24小时变现ROI(Z) | derived | 24小时变现金额(Z) / emi效果收入 |
| `deep_target_conv_num_z` | 深层目标转化数(Z), 深层转化数 | raw | — |
| `target_conv_cost_j` | 实际转化成本(J) | derived | emi效果收入 / 目标转化数(J) |
| `cpd` | CPD, 单次下载成本 | derived | (emi效果+品牌+外部Dsp) / 开始下载 |
| `deep_advv_z` | 深层广告主价值(Z), 深层ADVV | raw | — |
| `retention_cost_z` | 自定义留存成本(Z) | derived | emi效果收入 / 自定义留存(Z) |
| `view_filter_rate` | 曝光作弊过滤比例 | derived | (原始曝光 - 计费曝光) / 原始曝光 |
| `click_filter_rate` | 点击作弊过滤比例 | derived | (原始点击 - 计费点击) / 原始点击 |
| `cancel_download` | 取消下载 | raw | — |
| `cvr_view_download` | 曝光下载率 | derived | 开始下载 / 计费曝光 |
| `landing_page_view` | 落地页曝光 | raw | — |
| `landing_page_click` | 落地页点击 | raw | — |
| `video_start` | 视频播放 | raw | — |
| `video_fail` | 视频启播失败 | raw | — |
| `dev_win_num` | 开发者竞胜数 | raw | — |
| `raw_start_download` | 原始开始下载 | raw | — |
| `gross_view` | 大盘计费曝光, 含SDK曝光 | raw | 计费曝光+sdk曝光 |
| `gross_raw_view` | 大盘原始曝光 | raw | 原始曝光+sdk曝光 |
| `gross_click` | 大盘计费点击, 含SDK点击 | raw | 计费点击+sdk点击 |
| `gross_raw_click` | 大盘原始点击 | raw | 原始点击+sdk点击 |
| `raw_ecpm` | 原始eCPM | derived | 1000 × (emi效果+品牌+外部DspRtb) / 大盘原始曝光 |
| `fee_brand` | 品牌收入, 品牌消耗 | raw | — |
| `iap_game_joint_profit_j` | IAP游戏联运毛利(J) | raw | — |
| `iap_game_total_fee` | IAP游戏综合收入 | raw | — |
| `cvr_bill_deepconv_j` | CVR_计费到深层转化率(J) | derived | 深层目标转化数(J) / 计费数 |
| `deep_cvr_conv_j` | CVR_浅层到深层转化率(J) | derived | 深层目标转化数(J) / 目标转化数(J) |
| `conv_num_j` | 回传事件数(J) | raw | — |
| `deep_advv_j` | 深层广告主价值(J) | raw | — |
| `billing_ratio_j` | 计费比(J) | derived | emi效果收入 / 广告主价值(J) |
| `avg_target_cpa_conv_j` | 平均目标出价_转化(J) | derived | — |
| `avg_deep_target_cpa_deep_conv_j` | 平均深层目标出价_深层转化(J) | derived | — |
| `recall_retention_2day_z` | 召回留存率(Z) | derived | 自定义留存(Z) / 召回(Z) |
| `order_z` | 下单数(Z) | raw | — |
| `chargeback_z` | 退单数(Z) | raw | — |
| `add_desktop_z` | 加桌(Z) | raw | — |
| `web_form_submit_z` | 表单提交(Z) | raw | — |
| `inquire_z` | 线索(Z) | raw | — |
| `active_j` | 自定义激活(J) | raw | — |
| `new_active_j` | 自定义新增激活(J) | raw | — |
| `register_num_j` | 自定义注册(J) | raw | — |
| `retention_j` | 自定义留存(J) | raw | — |
| `reactive_j` | 首次拉活(J) | raw | — |
| `recall_j` | 召回(J) | raw | — |
| `open_account_j` | 开户(J) | raw | — |
| `purchase_j` | 购买(J) | raw | — |
| `new_user_purchase_j` | 首单购买(J) | raw | — |
| `order_j` | 下单数(J) | raw | — |
| `chargeback_j` | 退单数(J) | raw | — |
| `add_desktop_j` | 加桌(J) | raw | — |
| `credit_j` | 授信(J) | raw | — |
| `submit_j` | 完件(J) | raw | — |
| `inquire_j` | 线索(J) | raw | — |
| `web_form_submit_j` | 表单提交(J) | raw | — |
| `addiction_j` | 关键行为(J) | raw | — |
| `addiction_cost_j` | 关键行为成本(J) | derived | emi效果收入 / 关键行为(J) |
| `iap_revenue_24h_z` | 24小时付费金额(Z) | raw | — |
| `iap_uv_24h_z` | 24小时付费人数(Z) | raw | — |
| `iap_day_uv_24h_z` | 24小时付费人天(Z) | raw | — |
| `iap_uv_24h_cost_z` | 24小时付费成本(Z) | derived | emi效果收入 / 24小时付费人数(Z) |
| `iaa_day_uv_24h_z` | 24小时变现人天(Z) | raw | — |
| `iaa_day_arpu_24h_z` | 24小时变现arpu_人天(Z) | derived | 24小时变现金额(Z) / 24小时变现人天(Z) |
| `iap_revenue_7day_z` | 7日付费金额(Z) | raw | — |
| `iap_day_uv_7day_z` | 7日付费人天(Z) | raw | — |
| `iap_num_7day_cost_z` | 7日每次付费成本(Z) | derived | emi效果收入 / 7日内付费次数(Z) |
| `iap_uv_7day_cost_z` | 7日首次付费成本(Z) | derived | emi效果收入 / 7日内首次付费数(Z) |
| `iap_uv_7day_z` | 7日首次付费(Z) | raw | — |
| `first_order_7day_cost_z` | 7日首次下单成本(Z) | derived | emi效果收入 / 7日内首次下单数(Z) |
| `first_order_7day_z` | 7日首次下单数(Z) | raw | — |
| `iap_revenue_day_z` | 当自然日付费金额(Z) | raw | — |
| `iap_roi_day_z` | 当自然日付费ROI(Z) | derived | 当自然日付费金额(Z) / emi效果收入 |
| `iaa_revenue_day_z` | 当自然日变现金额(Z) | raw | — |
| `iaa_num_day_z` | 当自然日变现次数(Z) | raw | — |
| `iaa_uv_day_z` | 当自然日变现人数(Z) | raw | — |
| `iaa_roi_day_z` | 当自然日变现ROI(Z) | derived | 当自然日变现金额(Z) / emi效果收入 |
| `iaa_day_uv_day_z` | 当日变现人天(Z) | raw | — |
| `iaa_arpu_day_z` | 当自然日变现ARPU(Z) | derived | 当自然日变现金额(Z) / 当自然日变现人数(Z) |
| `iaa_day_arpu_day_z` | 当自然日变现arpu_人天(Z) | derived | 当自然日变现金额(Z) / 当日变现人天(Z) |
| `iap_revenue_z` | 付费金额(Z) | raw | — |
| `iap_day_uv_z` | 付费人天(Z) | raw | — |
| `iap_roi_z` | 付费ROI(Z) | derived | 付费金额(Z) / emi效果收入 |
| `iap_uv_z` | 首次付费(Z) | raw | — |
| `purchase_amount_z` | 购买金额(Z) | raw | — |
| `purchase_roi_z` | 购买ROI(Z) | derived | 购买金额(Z) / emi效果收入 |
| `chargeback_amount_z` | 退单金额(Z) | raw | — |
| `bb_retention_3day_z` | 明激活明3日留存数(Z) | raw | — |
| `bb_retention_4day_z` | 明激活明4日留存数(Z) | raw | — |
| `bb_retention_5day_z` | 明激活明5日留存数(Z) | raw | — |
| `bb_retention_6day_z` | 明激活明6日留存数(Z) | raw | — |
| `bb_retention_lt7_z` | 明激活明留存LT7总数(Z) | raw | — |
| `bb_retention_lt7_cost_z` | 明激活明留存LT7成本(Z) | derived | emi效果收入 / 明激活明7日内留存总数(Z) |
| `bd_retention_3day_z` | 明激活暗3日留存数(Z) | raw | — |
| `bd_retention_4day_z` | 明激活暗4日留存数(Z) | raw | — |
| `bd_retention_5day_z` | 明激活暗5日留存数(Z) | raw | — |
| `bd_retention_6day_z` | 明激活暗6日留存数(Z) | raw | — |
| `bd_retention_7day_z` | 明激活暗7日留存数(Z) | raw | — |
| `bd_retention_lt7_z` | 明激活暗留存LT7总数(Z) | raw | — |
| `bd_retention_lt7_cost_z` | 明激活暗留存LT7成本(Z) | derived | emi效果收入 / 明激活暗7日内留存总数(Z) |
| `own_day_active_z` | 小米当日激活(Z) | raw | — |
| `own_new_active_z` | 小米新增激活(Z) | raw | — |
| `own_new_active_rate_z` | 小米自有新增激活占比(Z) | derived | 小米新增当日激活(Z) / 小米当日激活(Z) |
| `own_tiny_app_open_z` | 小米快应用打开(Z) | raw | — |
| `own_tiny_app_adddesttop_z` | 小米快应用加桌(Z) | raw | — |
| `own_tiny_game_open_z` | 小米快游戏打开(Z) | raw | — |
| `own_day_active_start_download_z` | 小米自有下载当日激活率(Z) | derived | — |
| `own_tiny_app_open_j` | 小米快应用打开(J) | raw | — |
| `own_tiny_app_adddesttop_j` | 小米快应用加桌(J) | raw | — |
| `own_tiny_game_open_j` | 小米快游戏打开(J) | raw | — |
| `bill_conv_num_z` | 计费点转化(Z) | raw | 非多触点 |
| `contact_conv_num_z` | 多触点转化(Z) | derived | 曝光+点击+下载+安装转化之和 |
| `contact_click_conv_num_z` | 多触点点击转化(Z) | raw | — |
| `contact_view_conv_num_z` | 多触点曝光转化(Z) | raw | — |
| `contact_start_download_conv_num_z` | 多触点开始下载转化(Z) | raw | — |
| `contact_install_success_conv_num_z` | 多触点安装完成转化(Z) | raw | — |
| `zrl_push_conv_num_z` | zrl汇川转化(Z) | raw | — |
| `bill_conv_num_j` | 计费点转化(J) | raw | 非多触点 |
| `contact_conv_num_j` | 多触点转化(J) | raw | — |
| `contact_click_conv_num_j` | 多触点点击转化(J) | raw | — |
| `contact_view_conv_num_j` | 多触点曝光转化(J) | raw | — |
| `contact_start_download_conv_num_j` | 多触点开始下载转化(J) | raw | — |
| `contact_install_success_conv_num_j` | 多触点安装完成转化(J) | raw | — |
| `zrl_push_conv_num_j` | zrl汇川转化(J) | raw | — |
| `avg_deep_target_cpa_view` | 平均深层目标出价_曝光 | derived | 合计深层目标出价_曝光 / 计费曝光 |
| `avg_org_rta_ratio_view` | 原始RTA平均出价系数_曝光 | derived | — |
| `avg_pltv_bill` | 平均pltv_计费点 | derived | 总计pltv_计费点 / 计费数 |
| `avg_pltvfix_bill` | 平均pltvFix_计费点 | derived | 总计pltvFix_计费点 / 计费数 |
| `avg_pdeepltv_bill_user_j` | 平均pdeepltv_业务口径_计费点 | derived | — |
| `avg_pdeepltvfix_bill_user_j` | 平均pdeepltvFix_业务口径_计费点 | derived | — |
| `avg_pdeepltv_conv_user_z` | 平均pdeepltv_业务口径_浅层转化点(Z) | derived | — |
| `avg_pdeepltvfix_conv_user_z` | 平均pdeepltvFix_业务口径_转化点(Z) | derived | — |
| `avg_pdeepltv_conv_z` | 平均pdeepltv_浅层转化点(Z) | derived | — |
| `avg_pdeepltvfix_conv_z` | 平均pdeepltvFix_浅层转化点(Z) | derived | — |
| `avg_p_price_bill` | 平均pPrice_计费点 | derived | 平均pPrice_计费点 / 计费数 |
| `avg_pcvr_download` | 平均pcvr_下载 | derived | 总计pcvr_下载 / 开始下载 |
| `avg_rerank_pctr_view` | 平均端侧重排pctr_曝光 | derived | — |
| `avg_derankscore_view` | 平均引擎精排rankScore_曝光 | derived | — |
| `avg_rerank_pecpm_view` | 平均端侧重排pecpm_曝光 | derived | — |
| `avg_iap_game_divide_ecpm_view` | 平均预估联运分成pecpm_曝光 | derived | — |
| `total_pltv_bill` | 总计pltv_计费点 | raw | — |
| `total_pltvfix_bill` | 总计pltvFix_计费点 | raw | — |
| `total_pdeepltv_bill_user` | 总计pdeepltv_业务口径_计费点 | raw | — |
| `total_pdeepltvfix_bill_user` | 总计pdeepltvFix_业务口径_计费点 | raw | — |
| `total_pdeepltv_conv_user_z` | 总计pdeepltv_业务口径_浅层转化点(Z) | raw | — |
| `total_pdeepltvfix_conv_user_z` | 总计pdeepltvFix_业务口径_浅层转化点(Z) | raw | — |
| `total_iap_game_joint_pltv7_bill` | 总计联运pltv7_计费点 | raw | — |
| `total_iap_game_joint_pltv180_bill` | 总计联运pltv180_计费点 | raw | — |
| `total_iap_game_joint_pltv7_fix_bill` | 总计联运pltv7Fix_计费点 | raw | — |
| `total_iap_game_joint_profit180_bill` | 总计预估IAP游戏联运毛利180天_计费点 | raw | — |
| `pcoc_joint_pltv7` | 联运pltv7 pcoc(J) | derived | — |
| `pcoc_joint_pltv7_fix` | 联运pltv7Fix pcoc(J) | derived | — |
| `pcoc_joint_pltv180` | 联运pltv180 pcoc(J) | derived | — |
| `iap_game_subsidize_revenue_view` | 总计IAP游戏扶持补贴金额_曝光 | raw | — |
| `fee_effect_ac` | 对账后emi效果收入 | raw | — |
| `raw_fee_total_ac` | 对账后分成前收入 | derived | 对账后emi效果+外部Dsp+品牌 |
| `fee_total_ac` | 对账后分成后总收入 | derived | 对账后emi效果+外部Dsp+品牌+内部分成收入-内部分成支出 |
| `iap_revenue_180day_j` | 180天付费金额(J) | raw | — |
| `iap_revenue_24h_j` | 24小时付费金额(J) | raw | — |
| `iap_uv_24h_j` | 24小时付费人数(J) | raw | — |
| `iap_num_24h_j` | 24小时付费次数(J) | raw | — |
| `iap_roi_24h_j` | 24小时付费ROI(J) | derived | 24小时内付费金额(J) / emi效果收入 |
| `iap_arpu_24h_j` | 24小时付费ARPU(J) | derived | — |
| `iap_uv_24h_cost_j` | 24小时付费成本(J) | derived | emi效果收入 / 24小时付费人数(J) |
| `iaa_revenue_24h_j` | 24小时变现金额(J) | raw | — |
| `iaa_uv_24h_j` | 24小时变现用户数(J) | raw | — |
| `iaa_arpu_24h_j` | 24小时变现ARPU(J) | derived | 24小时变现金额(J) / 24小时变现用户数(J) |
| `iaa_roi_24h_j` | 24小时变现ROI(J) | derived | 24小时变现金额(J) / emi效果收入 |
| `iap_revenue_7day_j` | 7日付费金额(J) | raw | — |
| `iap_num_7day_j` | 7日付费次数(J) | raw | — |
| `iap_roi_7day_j` | 7日付费ROI(J) | derived | 7日内付费金额(J) / emi效果收入 |
| `iap_uv_7day_j` | 7日首次付费(J) | raw | — |
| `iap_uv_7day_cost_j` | 7日首次付费成本(J) | derived | emi效果收入 / 7日内首次付费数(J) |
| `iap_num_7day_cost_j` | 7日每次付费成本(J) | derived | emi效果收入 / 7日内付费次数(J) |
| `first_order_7day_j` | 7日首次下单数(J) | raw | — |
| `first_order_7day_cost_j` | 7日首次下单成本(J) | derived | fee_effect / first_order_7day_j |
| `iap_revenue_day_j` | 当自然日付费金额(J) | raw | — |
| `iap_roi_day_j` | 当自然日付费ROI(J) | derived | — |
| `iap_register_arpu_day_j` | 当自然日注册付费arpu(J) | derived | — |
| `iaa_revenue_day_j` | 当自然日变现金额(J) | raw | — |
| `iaa_uv_day_j` | 当自然日变现人数(J) | raw | — |
| `iaa_num_day_j` | 当自然日变现次数(J) | raw | — |
| `iaa_roi_day_j` | 当自然日变现ROI(J) | derived | 当自然日变现金额(J) / emi效果收入 |
| `iap_revenue_j` | 付费金额(J) | raw | — |
| `iap_num_j` | 付费次数(J) | raw | — |
| `iap_roi_j` | 付费ROI(J) | derived | 付费金额(J) / emi效果收入 |
| `purchase_amount_j` | 购买金额(J) | raw | — |
| `iap_uv_j` | 首次付费(J) | raw | — |
| `chargeback_amount_j` | 退单金额(J) | raw | — |
| `effect_app_purchase` | 有效购买数(J) | derived | 购买(J) - 退单数(J) |
| `bb_retention_2day_j` ~ `bb_retention_7day_j` | 明激活明2-7日留存数(J) | raw | — |
| `bb_retention_lt7_j` | 明激活明留存LT7总数(J) | raw | — |
| `bd_retention_2day_j` ~ `bd_retention_7day_j` | 明激活暗2-7日留存数(J) | raw | — |
| `bd_retention_lt7_j` | 明激活暗留存LT7总数(J) | raw | — |
| `bd_retention_lt7_cost_j` | 明激活暗留存LT7成本(J) | derived | emi效果收入 / 明激活暗7日内留存总数(J) |
| `iap_game_conv_num_z` | 游戏付费次数(Z) | raw | — |
| `iap_game_uv_24h_z` | 游戏24小时新增付费(Z) | raw | — |
| `iap_game_revenue_24h_z` | 游戏24小时付费金额(Z) | raw | — |
| `iap_game_uv_24h_cost_z` | 游戏24小时新增付费成本(Z) | derived | — |
| `iap_game_roi_24h_z` | 游戏24小时付费roi(Z) | derived | — |
| `iap_game_num_7day_z` | 游戏7日付费次数(Z) | raw | — |
| `iap_game_num_7day_cost_z` | 游戏7日付费次数成本(Z) | derived | — |
| `game_register_num_z` | 游戏自定义注册数(Z) | raw | — |
| `game_register_cost_z` | 游戏自定义注册成本(Z) | derived | — |
| `iap_game_conv_num_j` | 游戏付费次数(J) | raw | — |
| `iap_game_uv_24h_j` | 游戏24小时新增付费(J) | raw | — |
| `iap_game_revenue_24h_j` | 游戏24小时付费金额(J) | raw | — |
| `iap_game_uv_24h_cost_j` | 游戏24小时新增付费成本(J) | derived | — |
| `iap_game_roi_24h_j` | 游戏24小时付费roi(J) | derived | — |
| `iap_game_num_7day_j` | 游戏7日付费次数(J) | raw | — |
| `iap_game_num_7day_cost_j` | 游戏7日付费次数成本(J) | derived | — |
| `game_register_num_j` | 游戏自定义注册数(J) | raw | — |
| `game_register_cost_j` | 游戏自定义注册成本(J) | derived | — |
| `iap_game_revenue_day_j` | 游戏1日付费金额(J) | raw | — |
| `iap_game_revenue_3day_j` | 游戏3日付费金额(J) | raw | — |
| `iap_game_revenue_7day_j` | 游戏7日付费金额(J) | raw | — |
| `iap_game_revenue_30day_j` | 游戏30日付费金额(J) | raw | — |
| `iap_game_uv_day_j` | 游戏1日付费人数(J) | raw | — |
| `iap_game_register_num_day_j` | 游戏1日注册数(J) | raw | — |
| `iap_game_roi_day_j` | 游戏1日roi(J) | derived | — |
| `iap_game_roi_3day_j` | 游戏3日roi(J) | derived | — |
| `iap_game_roi_7day_j` | 游戏7日roi(J) | derived | — |
| `iap_game_roi_30day_j` | 游戏30日roi(J) | derived | — |
| `iap_game_uv_day_cost_j` | 游戏1日付费成本(J) | derived | — |
| `iap_game_arpu_day_j` | 游戏1日ARPU(J) | derived | — |
| `iap_game_register_cost_day_j` | 游戏1日注册成本(J) | derived | — |
| `iap_game_uv_revenue_register_day_rate_j` | 游戏付费率(J) | derived | — |
