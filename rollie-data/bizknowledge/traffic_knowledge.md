# 流量侧知识

---

## 一、媒体大类

### 概念说明

用户说"媒体大类"时，指的是商店搜索/商店推荐/信息流/联盟/软体等业务分类。
这些分类**不能仅靠 `media_type` 一个字段**，部分分类需要同时使用 `media_type` 和 `tag_id` 两个条件。
不要用 `model_tagid_group`（那是广告位模型分组，不是媒体大类）。

### 分类定义与查询条件

| 媒体大类 | 查询条件 | 说明 |
|---|---|---|
| 商店搜索 | `tag_id` IN 6个搜索位 | 属于 APP_STORE，但必须用 tag_id 区分 |
| 商店推荐 | `media_type=APP_STORE` 且 `tag_id` 以 `1.24.` 开头，排除搜索6位 | 属于 APP_STORE，必须用 tag_id 排除搜索 |
| 信息流 | `media_type` IN [NEW_HOME, BROWSER_FEED, PHONE_VIDEO, DUOKAN, QUANMIN_READER] | 仅靠 media_type 即可 |
| 联盟 | `media_type=UNION` | 仅靠 media_type 即可 |
| 软体 | 排除以上 4 类 + MI_PAY + QUICK_SEARCH_BOX 后的所有 media_type | 仅靠 media_type 即可 |
| 小米钱包 | `media_type=MI_PAY` | 不归入以上任何大类 |
| 全局搜索 | `media_type=QUICK_SEARCH_BOX` | 不归入以上任何大类 |

### 各分类完整查询条件

#### 商店搜索

`tag_id` IN: `1.24.4.12`, `1.24.4.15`, `1.24.4.129`, `1.24.4.75`, `1.24.4.14`, `1.24.4.130`

| tag_id | 中文名 |
|---|---|
| `1.24.4.12` | 搜索sug-应用下载 |
| `1.24.4.15` | 搜索结果页-应用下载 |
| `1.24.4.129` | 搜索结果页-精准量 |
| `1.24.4.75` | 搜索结果页-游戏分发 |
| `1.24.4.14` | 搜索结果页from热词-应用下载 |
| `1.24.4.130` | 搜索sug-自然量控量 |

#### 商店推荐

`media_type` = APP_STORE，且 `tag_id` 以 `1.24.` 开头，排除上述 6 个搜索位。

⚠️ 不能只用 `media_type=APP_STORE`，因为商店搜索也属于 APP_STORE，需要配合 tag_id 排除。

#### 信息流

`media_type` IN: NEW_HOME, BROWSER_FEED, PHONE_VIDEO, DUOKAN, QUANMIN_READER

#### 联盟

`media_type` = UNION

#### 软体

排除商店搜索、商店推荐、信息流、联盟、MI_PAY、QUICK_SEARCH_BOX 后的所有 media_type。

具体包含：WEATHER, DESKTOP, PUSH_NOTIFICATION, SAFE_CENTER, GALLERY_APP, CALENDAR, MIUI_VOICEASSIST, MI_MOVER, THEME, DOWNLOAD_MANAGER, GAME, ASSISTANT, MMS, XIAOMI_SC, MUSIC, FM

#### 不归类

MI_PAY（小米钱包）、QUICK_SEARCH_BOX（全局搜索）不归入以上任何分类。

### 查询示例

#### 查某外部DSP各媒体大类消耗

需要组合查询——部分大类靠 media_type 过滤，部分靠 tag_id 过滤：

1. 查按 media_type 分组的消耗（覆盖信息流/联盟/软体/MI_PAY/QUICK_SEARCH_BOX 等）
2. 查按 tag_id 分组的消耗（覆盖商店搜索/商店推荐，需要按 tag_id 前缀和具体值归类）
3. 汇总后按上方分类规则归入对应大类

#### 查信息流消耗

```json
{ "filters": { "media_type": ["NEW_HOME", "BROWSER_FEED", "PHONE_VIDEO", "DUOKAN", "QUANMIN_READER"] } }
```

#### 查联盟消耗

```json
{ "filters": { "media_type": "UNION" } }
```

#### 查软体消耗

构造 `media_type` IN 软体 16 个值的 filters。
