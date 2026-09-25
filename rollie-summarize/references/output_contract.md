# 输出规范

默认在对话里直接输出完整总结。只有用户明确要求沉淀、导出、同步或写文件时，才写入外部位置。

## 对话回复

- 使用中文，除非用户要求英文。
- 保持“滚滚”风格：直接、理性、锐利、有判断。
- 结构固定为：核心内容总结、逻辑硬伤分析、对盛总的价值提炼、具体行动项。
- 原文价值低时直接说，不为了凑内容拉长。

## Obsidian

当用户要求写入 Obsidian 时，目标目录固定为：

```text
/Users/park0er/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/Rollie/Rollie的报告厅/
```

写入前必须先物理核验目录存在：

```bash
ls "/Users/park0er/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/Rollie/Rollie的报告厅/"
```

不要新建相似目录，不要写入 `Rollie/报告厅/`、workspace 或临时目录。

命名格式：

```text
YYYY-MM-DD_标题.md
```

标题部分简洁、可检索，默认保留作者或主题关键词。没把握时先查看目标目录最近 5-10 个历史文件。

## 飞书

当用户要求导出到飞书或更新飞书文档时：

- 使用现有 `feishu` skill。
- 创建/更新文档前，按 `feishu` skill 要求读取飞书扩展 Markdown 规范。
- 用 `feishu docx create/update`，不要使用旧 `mcp_feishu_*` 或 `mcporter`。
- 如果涉及本地文件和飞书文档双向同步，必须在本地文件头部保留或回写溯源注释：

```html
<!-- feishu: https://www.feishu.cn/docx/xxx 或 https://mi.feishu.cn/wiki/xxx -->
```

## 本地 Markdown

当用户要求保存为本地 Markdown：

- 文件头部保留来源链接、抓取时间和原作者/标题。
- 如果来源是飞书，同样保留 `<!-- feishu: ... -->` 溯源注释。
- 不要覆盖已有同名文件，除非用户明确要求。
