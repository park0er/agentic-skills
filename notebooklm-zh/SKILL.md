---
name: notebooklm-zh
description: "Google NotebookLM 中文自动化技能。用 notebooklm-py 操控 NotebookLM：认证、创建/列出笔记本、添加来源（URL/文件/YouTube/Drive/文本）、Deep Research 深度研究、生成并下载产物（播客MP3/视频MP4/幻灯片PDF+PPTX/报告Markdown/测验/闪卡/思维导图/信息图/数据表CSV）、分享权限管理。触发词：notebooklm、笔记本、播客、音频概览、生成测验、闪卡、思维导图、信息图、研究、deep research、下载报告、导入来源、总结链接/文档/视频。"
---

# NotebookLM 中文自动化技能

通过 `notebooklm` CLI（PyPI 包 `notebooklm-py`，16k+ Stars）操控 Google NotebookLM。开始任何实际操作前先确认 CLI 和认证状态。

> **从 notebooklm-cli 迁移**：本 skill 原使用 `notebooklm-cli`（命令 `nlm`），现已升级为 `notebooklm-py`（命令 `notebooklm`）。后者支持产物下载、批量操作、本地文件上传等前者不具备的能力。两个 CLI 可并存，但本 skill 指导以 `notebooklm` 为主。

## 前置条件

```bash
command -v notebooklm || uv tool install "notebooklm-py[browser]"
notebooklm --version
notebooklm auth check --test --json
```

首次安装会自动下载 Chromium (~170 MB)。如果认证失败，运行：

```bash
notebooklm login
```

`notebooklm login` 会打开 Chrome 登录 Google 并抽取 NotebookLM cookie；用户可能需要在浏览器里手动完成登录。支持多账户 profile 切换（`--profile`）。

## 先读取实时命令参考

`notebooklm-py` 依赖 NotebookLM 内部接口，命令会随版本变化。处理复杂任务前优先运行：

```bash
notebooklm --ai
```

用输出里的当前命令签名为准，不要凭旧记忆调用。

## 核心工作流

### 1. 创建笔记本并添加来源

```bash
notebooklm notebook create "标题"
notebooklm notebook list --title
notebooklm alias set myproject <notebook_id>

# URL 来源
notebooklm source add myproject --url "https://example.com/article"
notebooklm source add myproject --youtube "https://youtube.com/watch?v=..."

# 本地文件（notebooklm-py 新增能力！）
notebooklm source add myproject --file ./document.pdf
notebooklm source add myproject --file ./notes.md
notebooklm source add myproject --file ./report.docx

# Google Drive
notebooklm source add myproject --drive "<google_drive_doc_id>" --type doc

# 文本
notebooklm source add myproject --text "正文内容" --title "来源标题"

# 查看来源
notebooklm source list myproject --full
notebooklm source get <source_id>                    # 获取来源元数据
notebooklm source content <source_id>                 # 获取索引后的全文内容
```

### 2. 提问和摘要

```bash
notebooklm notebook query myproject "问题"
notebooklm notebook query myproject "追问" --conversation-id <conversation_id>
notebooklm notebook describe myproject
```

不要用 `notebooklm chat start`，它会进入交互 REPL，不适合 agent 自动化；一次性问答用 `notebooklm notebook query`。

### 3. Deep Research 深度研究

```bash
# 启动深度研究（网络搜索模式）
notebooklm research start "查询关键词" --notebook-id myproject --mode deep

# 快速研究
notebooklm research start "查询关键词" --notebook-id myproject

# Google Drive 研究
notebooklm research start "查询关键词" --notebook-id myproject --source drive

# 查看进度（等待完成）
notebooklm research status myproject --max-wait 300

# 导入研究结果到笔记本
notebooklm research import myproject <task_id>
```

深度研究通常需要数分钟，会自动搜索网络、整合数十个信源。

### 4. 内容生成

所有生成命令自动化时都加 `--confirm` 或 `-y`，否则可能停在确认提示。

| 类型 | 命令 | 关键选项 | 下载格式 |
|---|---|---|---|
| 播客音频 | `notebooklm audio create <id> --confirm` | `--format deep_dive/brief/critique/debate`，`--length short/default/long` | MP3/MP4 |
| 视频 | `notebooklm video create <id> --confirm` | `--format explainer/brief/cinematic`，`--style whiteboard/anime/...` | MP4 |
| 幻灯片 | `notebooklm slides create <id> --confirm` | `--format detailed/presenter` | **PDF + PPTX** |
| 信息图 | `notebooklm infographic create <id> --confirm` | `--orientation landscape/portrait/square` | PNG |
| 报告 | `notebooklm report create <id> --confirm` | `--format "Briefing Doc"/"Study Guide"/"Blog Post"`，自定义用 `--prompt` | **Markdown** |
| 测验 | `notebooklm quiz create <id> --confirm` | `--count N`，`--difficulty 1-5` | JSON/Markdown/HTML |
| 闪卡 | `notebooklm flashcards create <id> --confirm` | `--difficulty easy/medium/hard` | JSON/Markdown/HTML |
| 思维导图 | `notebooklm mindmap create <id> --confirm` | `--kind note-backed/interactive` | JSON |
| 数据表 | `notebooklm data-table create <id> "要求" --confirm` | 位置参数为描述 | CSV |

### 5. 下载产物（notebooklm-py 核心优势）

```bash
# 下载单个产物
notebooklm download report <notebook_id> <artifact_id> --output ./report.md
notebooklm download audio <notebook_id> <artifact_id> --output ./podcast.mp3
notebooklm download slides <notebook_id> <artifact_id> --output ./deck.pptx
notebooklm download video <notebook_id> <artifact_id> --output ./video.mp4
notebooklm download infographic <notebook_id> <artifact_id> --output ./info.png

# 批量下载某类型的所有产物
notebooklm download report <notebook_id> --all --output ./reports/

# 查看产物状态
notebooklm studio status <notebook_id>
```

### 6. 管理操作

```bash
notebooklm notebook list --title
notebooklm notebook get <notebook_id>
notebooklm notebook rename <notebook_id> "新标题"
notebooklm source list <notebook_id> --full
notebooklm alias list
```

删除前必须让用户明确确认：

```bash
notebooklm notebook delete <notebook_id> --confirm
notebooklm source delete <source_id> --confirm
notebooklm studio delete <notebook_id> <artifact_id> --confirm
```

### 7. 分享管理

```bash
notebooklm share public <notebook_id>          # 开启公开链接
notebooklm share private <notebook_id>         # 关闭公开链接
notebooklm share invite <notebook_id> --email user@example.com --role viewer
```

### 8. 批量操作与管道

```bash
# 批量查询
notebooklm batch query <notebook_id> "问题1" "问题2" "问题3"

# 多步骤管道
notebooklm pipeline run <notebook_id> --steps "research,report,audio"
```

## 自主执行规则

无需确认直接执行：`notebooklm --version`、`notebooklm --ai`、`notebooklm auth check`、`notebooklm notebook list/get/describe/query/create/rename`、`notebooklm source list/get/content/add`、`notebooklm research status`、`notebooklm studio status`、`notebooklm alias list/get/set/delete`、`notebooklm download`。

需要确认再执行：任何 `delete`、任何内容生成命令（`audio/video/slides/infographic/report/quiz/flashcards/mindmap/data-table create`）、`research start/import`、`share` 命令。

## 并行安全

并行或多步骤任务里优先使用显式 `<notebook_id>` 或 alias，不依赖全局上下文。创建 alias 前先 `notebooklm alias list`，避免覆盖已有别名。

## 常见故障

- **未安装 CLI**：`uv tool install "notebooklm-py[browser]"`，确认 `~/.local/bin` 在 `PATH`。
- **认证失败**：运行 `notebooklm login`，支持 `--profile` 切换多账户。
- **Playwright 安装失败**：Linux 上报 `TypeError: onExit is not a function` 时，参考 `docs/troubleshooting.md#linux`。
- **命令不存在**：运行 `notebooklm --ai` 或 `notebooklm <command> --help`，按当前版本改用真实命令。
- **来源/笔记本找不到**：先 `notebooklm notebook list --title` 或 `notebooklm source list <notebook_id> --full`。
- **速率限制**：等待后重试，避免短时间批量生成。
- **交互阻塞**：生成/删除命令加 `--confirm`；不要启动 `notebooklm chat start`。
- **旧 nlm 命令**：如果需要旧版 `nlm` 命令（notebooklm-cli），两个 CLI 可并存。`nlm` 和 `notebooklm` 是独立的工具。

## 参考

- GitHub: https://github.com/teng-lin/notebooklm-py
- 功能速查表：见 [references/功能速查表.md](references/功能速查表.md)
- 中文触发词索引：见 [references/中文触发词.md](references/中文触发词.md)
