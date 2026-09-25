# References 目录组织约定

本目录承载 `rollie-data` Skill 在查数过程中需要查阅的全部参考资料。文件按属性分三层放置，新增文档前请先读完本文。

---

## 三层结构

| 层级 | 路径 | 文件角色 | 示例 |
|---|---|---|---|
| 根目录 | `references/` | **看板/字段主词典**：Skill 主流程在引入某个看板时必读的字段定义文档 | `xirang_ad_effect_field_dictionary.md`、`request_info_field_dictionary.md` |
| `enums/` | `references/enums/` | **枚举值映射**：被某个主词典引用，记录字段枚举值与中文翻译/分类的附录文档 | `media_type_cn_mapping.md`、`xirang_ad_effect_enum_tag_id.md` |
| `guides/` | `references/guides/` | **业务知识指南**：描述看板相关业务概念、链路架构等背景知识，辅助理解词典中的字段含义 | `xirang_recall_diagnosis_guide.md` |

---

## 新增文档归属判定流程

按下列顺序逐项问自己，第一个答 **是** 的就是该文档归属：

1. **这个文档定义某个看板/数据源的字段含义吗？**
   → 是 → 放 `references/` 根目录，文件名格式 `<board>_field_dictionary[_<variant>].md`。

2. **这个文档是某个字段枚举值与中文（或其他维度）的对照表吗？**
   → 是 → 放 `references/enums/`，文件名能体现来源看板与字段，例如 `<board>_enum_<field>.md` 或 `<scope>_<field>_cn_mapping.md`。

3. **这个文档提供业务背景知识（架构概念、链路原理等）吗？**
   → 是 → 放 `references/guides/`，文件名以 `_guide.md` 结尾。

如果三个问题都答否，先确认是否真的需要新增，而不是随手放根目录。

---

## 引用路径规范

| 引用方 | 被引用方 | 路径风格 | 示例 |
|---|---|---|---|
| References 内文件 | References 内任意文件 | 相对当前文件，`./` 起头 | `./enums/top_appid_cn_mapping.md` |
| `SKILL.md` 等 references 外文件 | References 内文件 | `references/` 起头（相对 skill 根） | `references/enums/top_appid_cn_mapping.md` |

**禁止**：同一目录层级混用 `references/...` 与 `./` 两种写法。

理由：
- references 内统一用相对路径，文件被独立预览或后续整体迁移时不会断链。
- SKILL.md 不在 references 下，继续用 `references/...` 与该文件已有惯例对齐。

---

## 变更治理

任何对**目录结构**（新增子目录、调整归属规则）或**引用路径策略**的修改 **MUST** 通过 OpenSpec change 流程实现，且该 change MUST 同时更新本 README 和 `openspec/specs/references-organization/spec.md`，防止两者漂移。

> 单纯增删一个 reference 文档（归属符合本约定）不需要走 OpenSpec change，正常 commit 即可。
