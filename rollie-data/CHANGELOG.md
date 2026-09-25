# rollie-data CHANGELOG

## 2026-06-17 — extract-traffic-knowledge

- TODO: 补充本次改动摘要


## 2026-06-16 — add-media-taxonomy

- 在 `media_type_cn_mapping.md` 追加"媒体分类概念说明"章节，定义 5 个业务分类：商店搜索、商店推荐、信息流、联盟、软体
- 明确每个分类的查询条件：商店搜索用 6 个 tag_id，商店推荐用 media_type+tag_id 前缀排除法，信息流用 5 个 media_type，联盟用 UNION，软体用排除法
- 新增 XIAOMI_SC（小米商城）media_type 枚举
- 更新主字典 `media_type` 行：增加对"信息流/商店搜索/商店推荐/软体/联盟"等业务分类概念的引用提示，指向枚举文档的"媒体分类概念说明"章节
- 同步发布 dsp_level2 enum 文档（见上一条）

## 2026-06-16 — add-dsp-level2-enum

- 新增 `references/enums/xirang_ad_effect_enum_dsp_level2.md`：外部DSP二级标识枚举文档，收录22个 dsp_level2 值 → 中文含义映射
- 更新低频字典 `dsp_level2` 行：从 `如 xiaomi.ocpa` 改为指向新 enum 文档的引用
- 新增飞书确认文档：https://feishu.cn/wiki/BhoswY3NTitaNXkUvZGco0Y4nxb
- 状态：待业务确认中文含义后去掉"待确认"标注
