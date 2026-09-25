---
name: rollie-data-dev
description: rollie-data 技能开发发布流程。在 /tmp/rollie-data/ 目录下修改代码后，通过 Skill Factory 流程精准发布到本地各安装目录。触发词："发布 rollie-data"、"rollie-data 发布"、"同步 rollie-data"、"更新 rollie-data skill"。不要用这个 skill 查数，查数用 rollie-data。
---

# rollie-data 开发发布流程

## 目录角色

| 目录 | 用途 | 可编辑 |
|---|---|---|
| `/tmp/rollie-data/skill/rollie-data/` | Git 开发目录 | ✅ 改代码在这里 |
| `~/Documents/Coding/PLAYGROUND/Skill_Factory/skills/rollie-data/` | Factory 真源 | ✅ 发布从这里 |
| `~/.claude/skills/rollie-data/` | Claude Code 安装 | ❌ 禁止直接编辑 |
| `~/.agents/skills/rollie-data/` | Codex 安装 | ❌ 禁止直接编辑 |
| `~/.gemini/config/skills/rollie-data/` | Gemini 安装 | ❌ 禁止直接编辑 |

## Git 工作流

```
develop（稳定分支，不直接改）
  └── xisheng / feature-xxx（开发分支，在这里改）
        ↓ 审阅后合并
      develop
```

**规则**：
1. 开发分支从 develop 拉取，在开发分支上改
2. 改完先提交到开发分支，推送后给盛总审阅
3. 盛总确认后才合并到 develop
4. **绝不自动 push develop**

## 配置文件

首次使用时，脚本会在 `/tmp/rollie-data/.dev-config` 创建配置：

```bash
DEV_BRANCH=xisheng          # 开发分支名
BASE_BRANCH=develop         # 基础分支名
```

没有配置时脚本会询问用户，配置后后续自动读取。

## 发布流程

使用一键发布脚本：

```bash
bash ~/.claude/skills/rollie-data-dev/scripts/publish.sh <label> [--dry-run]
```

### 脚本执行步骤

1. **读取配置**：从 `/tmp/rollie-data/.dev-config` 读取开发分支
2. **精准复制到 Factory**：只复制 skill 文件（排除 state/cookies/__pycache__/.DS_Store/.git）
3. **更新 CHANGELOG**：在 Factory 的 CHANGELOG.md 顶部添加条目
4. **dry-run 发布**：预览 release.sh 输出
5. **正式发布**：执行 release.sh，精准 rsync 到 3 个安装目录
6. **同步回 git**：把 Factory 的改动复制回 git 开发目录，git add + commit
7. **提醒审阅**：提示用户推送开发分支、合并到 develop 前需审阅

### 精准复制规则

**只复制以下目录/文件**（git → Factory）：
- `SKILL.md`
- `__init__.py`
- `CHANGELOG.md`
- `references/`（含 enums/、guides/）
- `scripts/`（不含 __pycache__/、*.pyc）
- `state/.gitkeep`（保留目录结构，不复制内容）

**绝不复制**：
- `state/.cookies.json`（鉴权凭证）
- `state/auth_logs/`（鉴权日志）
- `state/.refresh.lock`
- `scripts/__pycache__/`
- `.DS_Store`
- 任何其他 state/ 下的运行时文件

## 约束规则

1. **Factory 是唯一真源**：所有改动必须经过 Factory 发布
2. **CHANGELOG 强制更新**：每次 release 前必须更新
3. **label 要具体**：描述改动内容，不能写 backup/v2/裸时间戳
4. **SKILL.md description ≤ 1024 字符**
5. **archive 不可修改**
6. **精准复制**：不从 git 全量复制到 Factory，排除敏感文件
7. **Git 分支纪律**：开发在 feature 分支，合并到 develop 需审阅，不自动 push develop
