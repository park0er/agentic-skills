---
name: icloud-materialization-doctor
description: Use when diagnosing macOS iCloud Drive sync stuck-states in either direction. Download-side — "dataless" files where `st_size > 0 && st_blocks == 0`, no `.icloud` placeholder, but local disk has zero bytes — classic placeholder checks falsely report ready. Upload-side — `brctl status` shows `sig:<file-pending>` with stuck `[active]` sessions, `brctl quota` hangs, other devices never receive the file. Triggers include iCloud 卡住没下载/上传, bird stuck, fileproviderd stuck, agent-sync-doctor reports ready but files missing, macOS 12+ File Provider issues.
---

# icloud-materialization-doctor

iCloud Drive sync 在 macOS 12+ 上有两类典型卡死，本 skill 都管：

- **下载侧**（v1 起）：文件在云端，本地以 File Provider "dataless" 形态挂着
  （`st_size > 0 && st_blocks == 0`），`ls` / Finder 看不出毛病但实际拿不到字节。
- **上传侧**（v2 加入）：文件在本地有完整内容，但永远推不上 iCloud。`brctl
  status` 显示 `sig:<file-pending>` + `[active]` session 一挂数小时；其他设备拿
  不到这个文件。

两条路问题表现完全不同，但**很多时候病根都是 sync engine 在某层挂死或被压垮**。
本 skill 的职责：**给出准确的诊断 + 在能确定的范围内提供安全干预**，对不能
证明因果的"补救手段"明确标注为相关性而非因果（见后面 *Correlation, not
causation* 一节）。

## 下载侧：dataless 表现

macOS 12+ 起，`.icloud` placeholder 退役，"未下载"的新表现形式：

- 文件名正常（没有 `.icloud` 后缀）
- `stat -f %z`（逻辑 size）是真实大小
- `stat -f %b`（物理 block 数）= **0**
- `ls` / Finder 里看上去一切正常
- `find -name '*.icloud' | wc -l` = 0（假阳性）

这种状态下 `bird` / `fileproviderd` **坚持认为自己已经同步完了**，所以经典的
`agent-sync-doctor` / `claude-sync-doctor` 中的"placeholder 计数 == 0"就会
**错误地报告 iCloud 已就绪**。

## 上传侧：永远在 [active] 但永不完成

典型表现（来自 2026-05-13 / 14 多台机器观察 + `brctl status` 抓取）：

- 单文件 `up:needs-upload` + `sig:<file-pending>` + `tsig:<pending>`：
  bird 启动了 upload session（所以 status 显示 `[active]`），但本地 content
  signature 从来没算出来，**session 永远不能进入 body 传输阶段**
- `[active] last:1.13h ago` 这种看似活跃实则呆滞的 session 累积成千上万条
- `brctl quota` 命令 hang 不返回（**这本身就是强信号** —— quota RPC 走的
  是 control plane，hang 说明 cloudd ↔ CloudKit 通讯卡了）
- "0 字节文件能传，几 KB 文件就卡" —— 暗示 body upload 通道走不通
  （MTU / CDN / 网络中间设备可疑）

## 什么时候用

**下载侧（dataless）触发条件：**

- 用户说"iCloud 卡住了没下载"、"Mac B 推上去了 Mac A 拉不下来"
- `find -name '*.icloud'` 查完是 0 但用户仍然报告数据不完整
- Codex session rollouts（`~/.codex/sessions/**`）或 Claude projects
  （`~/.claude/projects/**`）里大文件 `ls -lh` 看着对、`cat` 读空或 hang
- 切机交接流程的 "iCloud drain" 这一步需要判断**真实**下载完成度

**上传侧（upload-stuck）触发条件：**

- 用户说"iCloud 一直转圈"、"上传不动了"、"另一台 Mac 拿不到我新建的文件"
- `brctl status` 里 `sig:<file-pending>` 长时间不收敛
- `brctl quota` 命令 hang
- agent-sync-doctor 的 sync 看似成功但其他 device 没接到改动

**不要用于：**

- 纯符号链接漂移 —— 用 agent-sync-doctor
- Codex SQLite WAL / JSON merge —— agent-sync-doctor
- iCloud 以外的云盘（OneDrive、Google Drive） —— 它们的 placeholder / sync
  语义不同
- 不是 macOS 12+ 的系统（老 Mac 仍然用 `.icloud` 后缀，agent-sync-doctor 的
  经典检查就够用）

## 核心原理（一句话）

```
dataless = (st_size > 0) && (st_blocks == 0)
```

扫一遍目标树、对每个 regular file 做 `os.stat()`、挑出 `st_blocks == 0` 但
`st_size > 0` 的，就是 File Provider dataless 文件。**没有任何一类有效的
iCloud Drive 文件会是这个状态。**

## 修复阶梯

本 skill 的 `fix` 子命令按阶梯推进，每一级都比上一级更侵入：

| 级别 | 动作 | 代价 | 副作用 |
|---|---|---|---|
| 1 | **stat-walk nudge**：递归 `os.stat()` 所有文件 | 几秒，无网络 | 无 |
| 2 | **poll drain**：轮询 dataless 计数，最多 `--deadline` 秒 | 等待，无网络 | 无 |
| 3 | **force-read**（仅 `--force-read`）：对仍 dataless 的文件 `head -c 1` | 阻塞直到字节到位 | 有带宽 / 时间代价 |
| 4 | **daemon kick**（不自动执行，仅打印指引） | `killall bird fileproviderd` | daemons 自动重启，fetch 队列重置 |
| 5 | **toggle iCloud Drive**（仅指引） | 系统设置层面 | 需要用户手动 |

**关键经验**：级别 1（stat-walk）对**绝大多数**卡住的 dataless 文件就够用
—— 遍历 stat 本身会把这些路径重新推回 File Provider 的关注范围，把挂起
的 fetch 重排入队。级别 3 的 force-read 是对顽固文件的兜底。

## 使用方式

脚本位置（按实际安装地决定）：

```
~/.claude/skills/icloud-materialization-doctor/scripts/icloud_materialization_doctor.py
~/.agents/skills/icloud-materialization-doctor/scripts/icloud_materialization_doctor.py
```

### check（只读报告）

```bash
# 默认扫描 agent-sync-doctor 的三个根（AgentSync / ClaudeSync / CodexSync）
python3 $SCRIPT check

# 指定任意路径
python3 $SCRIPT check --paths ~/Documents/MyICloudFolder

# 机器可读 JSON（供 agent-sync-doctor 或任何 driver 解析）
python3 $SCRIPT check --json

# 打印 dataless 样本路径
python3 $SCRIPT check --verbose
```

退出码：`0` = 全部物化、`1` = 存在 dataless、`2` = 没有可扫的路径。

### fix（下载侧实际修复）

```bash
# 仅跑 stat-walk + 轮询（最安全）
python3 $SCRIPT fix

# 加上 force-read 兜底（顽固 dataless 文件 cat 一个字节）
python3 $SCRIPT fix --force-read

# 长文件/慢网络需要更长的 drain 等待
python3 $SCRIPT fix --force-read --deadline 600
```

`fix` **不会**自动 `killall` 任何 daemon；如果阶梯 1-3 跑完仍有 dataless，
脚本会打印出手动升级的下一步。理由：daemon kick 需要用户可见的心理负担，
且本 skill 即便在 Claude Code 的 sandbox 里也能跑（`killall` 在那里会被拒）。

### upload-check（上传侧诊断）

```bash
# 默认扫三个 sync root
python3 $SCRIPT upload-check

# JSON 输出（供 agent-sync-doctor / 其他 driver 解析）
python3 $SCRIPT upload-check --json

# 调高 size threshold，跳过 1 MB 以下的杂件
python3 $SCRIPT upload-check --min-size-mb 50 --top-n 30
```

输出三块：

1. **brctl status 解析**（如可用）：`sig:<file-pending>` 数、`[active]` session 数、
   `pending-sync-up` 数等关键计数。在沙箱里跑会"unavailable" + 解释原因，
   不影响后两块。
2. **Top N 大文件**（>= `--min-size-mb`，按字节降序）：识别 body upload 压力点。
3. **Build-artifact 目录清单**：`node_modules` / `build` / `dist` /
   `__pycache__` / `.next` / `.turbo` / `.pytest_cache` 这些 sync 队列的
   文件碎片化大头，连接 `housekeeping-suggest`。

**首行总会打印 multi-machine caveat**（hostname + 警告"这只是本机的视图"）。
不可关闭。详见 *Multi-machine pitfall*。

退出码：`0` = brctl 报告无 pending 或（brctl 不可用时）无 build artifact 候选；
`1` = 至少一项有问题；`2` = 没有可扫的路径。

### housekeeping-suggest（清理建议，干跑默认）

```bash
# 干跑：只打印将要做什么，不动手
python3 $SCRIPT housekeeping-suggest

# 真跑：rm -rf 列出的 build artifact 目录
python3 $SCRIPT housekeeping-suggest --apply
```

设计原则：

- **只动 build-artifact 类目录**（白名单见脚本 `BUILD_ARTIFACT_DIR_NAMES`），
  其他什么都不碰。即使 `--apply` 也不动 `.git/`、源代码、用户文档、
  Codex sessions JSONL（那些是不可重建的对话历史，明确不在 cleanup 范围内）。
- **干跑必现完整清单**：每个目录的字节数、文件数、绝对路径都列出来，
  让你一眼看清要不要执行。
- **`--apply` 不可逆**：build artifact 走 `rm -rf` 不入 Trash，理由写在
  脚本注释里 —— Trash 在系统盘，大目录会撑爆系统盘。要回收靠重新 build。

**不在本子命令的范围内**（要清理这些得用户自己来）：

- Codex `sessions/*.jsonl`（用户对话历史，不可重建，需用户判断哪些过期）
- Codex `archived_sessions/*`（用户主观判断"不再用了"才能动）
- Claude `projects/*.jsonl`（同理，用户记忆数据）

如果 `housekeeping-suggest` 给出的清单不能解决你的问题，那就**不是这个 skill
该解决**的。再砍数据要进入用户判断领域。

## Multi-machine pitfall

**这是上传侧诊断中最容易踩的坑**，先讲透：

iCloud 的 sync 是**账号级**的，但 `brctl status` 是**机器级**的 —— 它只显示
"本机当前在尝试推什么 / 等什么"。如果你的几台 Mac 都通过 agent-sync-doctor
的 symlink 模式把 `~/.claude` / `~/.codex` / `~/.agents` 指向 iCloud，那么：

- **写改动的机器**和**你正在诊断的机器**经常**不是同一台**。
- 你换到另一台 Mac 上跑 `upload-check`，看到的 pending 队列**不是**之前那台
  Mac 卡住的那批 —— 那批仍然挂在原 Mac 的 bird 里，本机看不见。
- "切到新 Mac 后 brctl 显示 0 pending" **不能证明问题已经解决**。它只能
  证明"本机没积压"。

**怎么判断你站在哪一边**：

```bash
# 看看 ~/.claude 是 symlink 还是 real dir
ls -la ~/.claude
# l rwxr-xr-x ... -> /Users/X/Library/Mobile Documents/.../ClaudeSync/dotclaude
#   ↑ 你是 follower（目录由 iCloud 同步过来；本机 bird 看不到 originator 的 pending）
# d rwxr-xr-x  ...
#   ↑ 你是 originator（这台 Mac 的修改才会进入本机 bird 的 upload 队列）
```

`upload-check` 子命令在每次输出第一段就把这个 caveat 强制打印出来 ——
**不是装饰文字，是诊断纪律的一部分**。

如果你怀疑 stuck 是另一台 Mac 上的，正确做法是**远程到那台 Mac 跑诊断**，
或至少在那台 Mac 上跑一次 `brctl status` 把 pending 数字拍下来。在错的
机器上反复 kill bird、清缓存、删文件，**不会修复另一台 Mac 上的状态**。

## Correlation, not causation

iCloud 上传卡死是分布式系统问题：客户端 daemon、CloudKit 服务端、网络路径、
Apple ID 状态、跨机器 sync 在同时变化。**任何"我做了 X，然后 Y 好转了"的
归因都需要怀疑**：Y 可能是自己好的、是另一台机器把状态推到云之后顺带解开的、
是 Apple 服务端某个 backoff timer 到期的、是网络条件变了的。

下表把"在 stuck 现场常见的干预动作"和"它们的真实证据等级"摆开，使用本 skill
的人**不要把 Probably / Plausible 升级成 "我做这个就能修好"**。

| 干预 | 多少人试过有效（观察） | 我们能证明的机制 | 风险 |
|---|---|---|---|
| `killall bird` (单杀) | 时常报告"杀完队列开始动了" | **未证明**。bird 重启会让 launchd 拉起，新进程读盘上的 sqlite 队列。读这一刻可能"碰巧"赶上服务端重新接受。无独立 reproducer | 极低（launchd 自动拉起，无数据丢失） |
| `killall bird fileproviderd cloudd` (三件套) | 同上 | **未证明**。三个 daemon 一起重启的纯效应 vs. 单杀 vs. 等同等时长，没人做过对照实验 | 低（短暂影响 Photos / Notes / Keychain 同步几秒） |
| 重启电脑 | "重启就好"是民间智慧 | **未证明**。重启耗时 1-2 分钟，足够任何 timeout / retry / TTL 自我修复。**无法区分**"重启起作用"和"等了 2 分钟起作用" | 中（用户工作流中断） |
| GUI 关掉再开 iCloud Drive | 偶有报告有效 | **未证明**。toggle 会触发 fileproviderd 全量重扫，但同时也强制本地数据 stage 进 / 出云端 cache，可能引入新冲突 | 高（误选"从 Mac 移除"会丢本地副本） |
| 切换网络（离开公司 VPN / 企业 WiFi） | 多次报告"换网就传上去了" | **部分可证明**。CloudKit 走 TLS 长连接 + 大 body asset upload；企业网中间设备可能拦 MSS / 干扰 path MTU；切网会重新协商 | 低（可逆） |
| `housekeeping-suggest --apply` 减少文件碎片化 | 在 file count > 数万时**强相关**于队列消化 | **部分可证明**。bird 维护每文件 entry / sqlite 状态；删文件等于不再要 sync 这些 entry。但**这只解释了"删的那些"为什么从队列消失**，不解释"没删的、卡了几小时的文件为啥也跟着活了" | 低（白名单内全是可重建产物） |
| 等待 30 分钟到几小时 | 经常 stuck 自己消失 | **完全合理但证明不了**。CloudKit 上 retry / state-machine timeout 一般在小时级；服务端运维事件通常分钟内修复 | 零 |

**怎么用这张表**：诊断时按"风险从低到高"试 —— `upload-check` 看现状 →
等 30 分钟 → `housekeeping-suggest` 干跑评估 → 必要时 `--apply`
→ 切换网络复测 → 再考虑 daemon kick → 最后才是 GUI toggle。**到任何一步
好转了都不要写"我修好了"**，写"现在 sig:<file-pending> 是 0"就够。

`upload-check` 的 multi-machine caveat 加这张表是本 skill 的**诚实声明**：
我们能给你"看清现场"的工具，但 stuck 的真因常常在你够不到的地方
（CloudKit 服务、企业网、另一台 Mac），别让本 skill 用户产生"我跟着步骤来
就一定能修"的错觉。

## JSON 输出 schema

### check / fix（下载侧）

```json
{
  "schemaVersion": 1,
  "paths": [
    {
      "path": "/Users/.../CloudDocs/ClaudeSync",
      "exists": true,
      "total_files": 46446,
      "dataless_count": 0,
      "dataless_bytes": 0,
      "dataless_samples": [],
      "errors": []
    }
  ],
  "summary": {
    "datalessCount": 0,
    "datalessBytes": 0,
    "totalFiles": 46446,
    "ready": true
  }
}
```

### upload-check（上传侧）

```json
{
  "schemaVersion": 1,
  "subcommand": "upload-check",
  "host": "ParkerdeiMac-303.local",
  "platform": "Darwin 25.4.0",
  "brctl": {
    "sig_pending": 0,
    "active_uploads": 0,
    "pending_sync_up": 0,
    "needs_upload": 0,
    "needs_sync_up": 0,
    "available": false,
    "note": "brctl status hung past 15s — itself a strong stuck signal"
  },
  "topLargestFiles": [
    {"sizeBytes": 561234567, "path": "/Users/.../sessions/.../rollout-...jsonl"}
  ],
  "buildArtifactDirs": [
    {"sizeBytes": 55123456, "fileCount": 6159, "path": "/Users/.../node_modules"}
  ],
  "buildArtifactSummary": {
    "dirCount": 10,
    "totalBytes": 108000000,
    "totalFiles": 7990
  }
}
```

**字段稳定性**：`schemaVersion` 不变更 schema 不破坏；字段追加允许，字段删除
/改名需要 bump 到 2。`brctl.available=false` 时其他 brctl 字段含义无定义
（一般是 0），消费者必须先看 `available`。

## 与 agent-sync-doctor 的配合

agent-sync-doctor 的 `icloud_upload_check()` 只查 `.icloud` placeholder 和
`brctl status` 的 pending 列表，**漏查** File Provider dataless。推荐 agent
-sync-doctor 在其 `run_arrive` / `run_handoff` 流程里 subprocess 调用本 skill：

```python
import subprocess, json, shutil
script = shutil.which("icloud_materialization_doctor.py") or ...
out = subprocess.check_output(
    ["python3", script, "check", "--json", "--paths", str(icloud_root)],
    timeout=60,
)
report = json.loads(out)
dataless_count = report["summary"]["datalessCount"]
ready = report["summary"]["ready"]
```

readiness gate 改为：

```
ready := placeholderCount == 0
      && currentPendingCount == 0
      && datalessCount == 0
```

## 沙箱兼容

macOS 上 `brctl` / `log show` / `fileproviderctl` 在被 sandbox profile 限制
的进程中会直接拒绝（表现为 `Cannot run while sandboxed` /
`Trying to invoke brctl from a sandboxed process`）。本脚本两条路的兼容性：

- **下载侧 `check` / `fix`**：完全不依赖任何外部命令，只用 `os.stat` /
  `os.scandir` / `open`。这三者在任何 macOS sandbox profile 里都通过，所以
  从 Claude Code 沙箱化的 bash 直接跑也行。
- **上传侧 `upload-check`**：会**尝试** invoke `brctl`，15 秒 timeout 内
  没拿到结果就降级。降级后输出仍然有用 —— 大文件清单 + build-artifact
  扫描都是纯文件系统操作，不受沙箱影响。仅 brctl 那一段会说"unavailable"
  + 解释原因。
- **`housekeeping-suggest`**：纯 fs 操作。`--apply` 模式用 `shutil.rmtree`
  做删除（不 spawn `rm` 子进程）。沙箱里能跑（前提是沙箱允许写目标路径）。

## 常见误解

| 误解 | 实际 |
|---|---|
| "macOS 26 没有 dataless 文件，iCloud 现在都是按需下载" | dataless 就是"按需下载"的持久态；只是不再用 `.icloud` 后缀 |
| "`ls` 显示文件存在就代表下载完了" | File Provider 可以在 fs 里挂一个 metadata-only 的节点；`ls` 完全看不出来 |
| "`stat` 只读 inode，不会触发下载" | 一般是这样，但它会把路径推回 File Provider 的关注面，让挂起的 fetch 排队继续 |
| "`.icloud` 文件和 dataless 文件是一回事" | 不是。`.icloud` 是 legacy placeholder 路径；dataless 是 File Provider 路径。macOS 12+ 下两者共存但大部分文件走后者 |
| "只要 `brctl status` 显示 pending=0 就是 ready" | `brctl status` 查的是"待上传到云"，不查"已在云但未下到本机"；下载侧仍要走 `check` |
| "另一台 Mac 上 stuck 的上传，我换到这台 Mac 就能看到" | **不能**。`brctl status` 是机器级，只看本机自己的待推队列。诊断必须在 originator 机器上做 |
| "killall 完之后 pending 立刻降到 0，就是 daemon 卡了" | 是 *correlation*，不是 causation。重启服务的同时 sqlite 队列被重读、网络可能正好恢复、服务端可能正好接受了之前的请求 —— 单杀实验做不出独立证据。见 *Correlation, not causation* 表 |
| "`brctl quota` 返回了配额数字 = iCloud 健康" | quota 走 control plane，asset upload 走 data plane。control plane 通不代表 body upload 通；常见现象是"quota 报得出，但 8 KB 文件传不上去" |
| "删了 build artifact，pending 队列就消化完了" | 你删的那部分肯定从队列消失了（不需要再 sync 了），但**没删的那部分**为啥跟着活了，无法从这一动作单独推出。可能是同时间网络 / 服务端状态变了 |

## 真实现场数据点

### 2026-05-13：下载侧（Mac A 的 dataless 修复）

首次 `check`：

```
AgentSync    dataless=27   bytes=219,123
ClaudeSync   dataless=878  bytes=27,452,801
CodexSync    dataless=1946 bytes=459,401,210   # 含 2 个 200MB+ Codex rollout
```

`.icloud` placeholder 全部为 0 —— 经典检查完全漏。

`fix` 后：三个仓库 dataless 全部归零。**绝大多数**在 stat-walk + 轮询
阶段就完成；只有几个需要 `--force-read` 兜底。总耗时约 2-3 分钟，取决于
那两个 200MB 文件的下载带宽。

### 2026-05-14：上传侧（多机 / 多 daemon stuck 现场）

**初始观察**（在 iMac 上看到的本机 brctl 数字 —— **不是** originator 机器
MacBook Pro 的真实状态）：

```
brctl 解析后：
  sig:<file-pending>          17,036
  [active] upload sessions    11,893
  [pending-sync-up] queued     7,679
  up:needs-upload             11,894

特定文件状态举例：
  ClaudeSync/dotclaude/skills/icloud-materialization-doctor/SKILL.md
    sig:<file-pending>  +  [active] last:11.67h ago

brctl quota                    HANG（>15s 不返回）
```

**做过的动作（按时间顺序）**：

1. `killall bird`（单杀）
2. `killall bird fileproviderd cloudd`（三件套）
3. 重启电脑
4. `housekeeping-suggest --apply`（删 30 个 build artifact 目录，~550 MB；
   同时 mv 一批 archived_sessions 到 Trash）

**结果**：第 4 步 90 秒后 `brctl status` 显示 0 pending；之前那个
SKILL.md 也从 pending 列表消失。**乍看像第 4 步起作用**。

**但事后发现**：诊断和"清理"都在 iMac 上做，原 stuck 是从 MacBook Pro
发起的（用户在 MBP 上 release 了 skill 才有那批 SKILL.md / *.py 的待推）。
iMac 自己**从来没有过那批 stuck**；它看到的"17,036 pending"是 fileproviderd
启动后**短暂同步出来的状态**。换言之：**无法证明**清理动作让 stuck 解开
了 —— 真正的 originator MacBook Pro 上当时发生了什么没人看到。可能 MBP
自己撑过去了；可能 Apple 服务端某个 timer 到期；可能 12 小时累积下来某段
网络条件变了。

**这条数据点的教训**写进了 *Correlation, not causation* 表 + multi-machine
pitfall 章节。后续诊断必须先回答 "你站在 originator 还是 follower 一侧"
再讨论"做什么修复"。

<!-- feishu: (pending; upload when ready) -->
