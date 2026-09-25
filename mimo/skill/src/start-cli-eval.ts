import { randomUUID } from "crypto";
import {
  mkdirSync,
  writeFileSync,
  readFileSync,
  existsSync,
  readdirSync,
  statSync,
} from "fs";
import { execSync } from "child_process";
import { join } from "path";
import { homedir } from "os";
import { checkUpdate } from "./update.js";
import { EVAL_CONFIG } from "./eval-config.js";
import { openTerminalPair } from "./terminal/index.js";
import { ensureMimoCodeUpdated } from "./mimo-update.js";

interface CliEvalTask {
  id: string;
  name: string;
  type: "agent";
  cli_a: { type: "claude" | "mimocode"; model?: string };
  cli_b: { type: "claude" | "mimocode"; model?: string };
}

const CLI_EVAL_DEFAULTS: CliEvalTask = {
  id: "local-cli-eval",
  name: "Claude Code vs MiMo Code",
  type: "agent",
  cli_a: { type: "claude", model: "" },
  cli_b: { type: "mimocode" },
};

if (await checkUpdate()) { const { execFileSync } = await import("child_process"); try { execFileSync(process.execPath, process.execArgv.concat(process.argv.slice(1)), { stdio: "inherit", env: process.env }); } catch {} process.exit(0); }

const { stateDir, routerURL, registerURL } = EVAL_CONFIG;

import { loadKey, saveKey, login } from "./auth.js";

// --- Auth: load key or trigger login ---
let userApiKey = loadKey();

if (process.env.MIMO_INLINE_KEY && userApiKey === process.env.MIMO_INLINE_KEY) {
  saveKey(userApiKey);
  console.log(`🔑 密钥已保存，后续无需重复输入`);
}

if (!userApiKey) {
  userApiKey = await login();
}

const userBaseURL = routerURL;

const cwd = process.env.MIMO_USER_CWD;
if (!cwd) {
  console.error("❌ MIMO_USER_CWD 未设置。");
  console.error("");
  console.error("请通过 /mimocode <prompt> 命令启动评测。");
  process.exit(1);
}

const firstMessage = process.env.MIMO_FIRST_MESSAGE?.trim() || "";

// --- Locate mimocode binary (cross-platform: macOS / Linux / Windows) ---
function findMimoBin(): string {
  const isWin = process.platform === "win32";

  // 1. Windows: 直接走 process.env.PATH，避免 `where` 在中文系统下用 GBK 输出
  //    被 Node 当成 UTF-8 解码后产生 mojibake（如 徐志鹏 → ��־��）。
  if (isWin) {
    const pathEnv = process.env.PATH || process.env.Path || "";
    const exts = [".cmd", ".exe", ".ps1", ""];
    for (const dir of pathEnv.split(";")) {
      const d = dir.trim();
      if (!d) continue;
      for (const ext of exts) {
        const p = join(d, "mimo" + ext);
        if (existsSync(p)) return p;
      }
    }
  } else {
    //    POSIX: command -v 比 which 更通用，在极简容器/busybox 中也可用
    for (const cmd of ["command -v mimo", "which mimo"]) {
      try {
        const result = execSync(cmd, { encoding: "utf-8", stdio: "pipe" }).trim().split(/\r?\n/)[0];
        if (result) return result;
      } catch {}
    }
  }

  // 2. npm global prefix 推导
  try {
    const prefix = execSync("npm prefix -g", { encoding: "utf-8", stdio: "pipe" }).trim();
    const candidates = isWin
      ? [join(prefix, "mimo.cmd"), join(prefix, "mimo.exe"), join(prefix, "mimo.ps1"), join(prefix, "mimo")]
      : [join(prefix, "bin", "mimo")];
    for (const p of candidates) {
      if (existsSync(p)) return p;
    }
  } catch {}

  // 3. 常见全局安装路径硬探测
  const fallbackPaths = isWin
    ? [
        join(process.env.APPDATA || "", "npm", "mimo.cmd"),
        join(process.env.LOCALAPPDATA || "", "pnpm", "mimo.cmd"),
      ]
    : [
        "/usr/local/bin/mimo",
        "/usr/bin/mimo",
        join(process.env.HOME || "~", ".npm-global", "bin", "mimo"),
        join(process.env.HOME || "~", ".local", "share", "pnpm", "mimo"),
        join(process.env.HOME || "~", ".yarn", "bin", "mimo"),
      ];

  for (const p of fallbackPaths) {
    if (existsSync(p)) return p;
  }

  // 4. 全部找不到，返回裸名让后续安装逻辑触发
  return "mimo";
}

let mimoBin = findMimoBin();
ensureMimoCodeUpdated(mimoBin);
mimoBin = findMimoBin();

// Detect CLI versions
function getCliVersion(cmd: string): string {
  try {
    return execSync(`${cmd} --version`, { encoding: "utf-8", timeout: 5000 }).trim();
  } catch {
    return "";
  }
}
const claudeVersion = getCliVersion("claude");
const mimoVersion = getCliVersion(`"${mimoBin}"`);

// --- Fetch task from server (must have agent task configured) ---
let task: CliEvalTask = CLI_EVAL_DEFAULTS;
let taskFound = false;

try {
  const resp = await fetch(`${routerURL}v1/eval/task/current?type=agent`);
  if (resp.ok) {
    const { data } = (await resp.json()) as any;
    if (data) {
      task = {
        id: String(data.id),
        name: data.name,
        type: "agent",
        cli_a: { type: "claude", model: data.model_a || "" },
        cli_b: { type: "mimocode" },
      };
      if (data.config) {
        try {
          const config = JSON.parse(data.config);
          if (config.cli_a) task.cli_a = config.cli_a;
          if (config.cli_b) task.cli_b = config.cli_b;
        } catch {}
      }
      if (!task.cli_a.model && data.model_a) task.cli_a.model = data.model_a;
      taskFound = true;
      console.log(`📋 获取到 Agent 评测任务: ${task.name} (模型: ${task.cli_a.model})`);
      if (data.reward_multiplier && data.reward_multiplier > 1) {
        console.log(`🔥 赏金任务！本次评测奖励 x${data.reward_multiplier} 倍`);
      }
    }
  } else {
    const text = await resp.text().catch(() => "");
    console.error(`❌ 拉取任务失败 (HTTP ${resp.status})`);
    if (text) console.error(`   ${text.slice(0, 200)}`);
    process.exit(1);
  }
} catch (err: any) {
  console.error(`❌ 无法连接服务器: ${err.message}`);
  console.error(`   URL: ${routerURL}v1/eval/task/current?type=agent`);
  process.exit(1);
}

if (!taskFound) {
  console.error("❌ 当前无 Agent 评测任务。");
  console.error("   请在 http://mimorouter.llmcore.ai.srv/ → Agent 评测 → 评测任务 页面创建任务后再试。");
  process.exit(1);
}

if (!task.cli_a.model) {
  console.error("❌ 任务未配置模型，无法启动。");
  console.error("   请在评测任务中设置模型。");
  process.exit(1);
}

// --- Random assignment ---
const shuffle = Math.random() > 0.5;
const sideACli = shuffle ? task.cli_b : task.cli_a;
const sideBCli = shuffle ? task.cli_a : task.cli_b;

const ALIASES = ["Alpha", "Beta"];
const aliasA = ALIASES[0];
const aliasB = ALIASES[1];

// --- Clean up old worktrees from previous eval ---
cleanupOldWorktrees(cwd);

// --- Git + Worktree setup ---
const evalId = randomUUID();
const shortId = evalId.slice(0, 8);

const { worktreeA, worktreeB, gitInited } = setupWorktrees(cwd, shortId);

const sessionA = randomUUID();
const sessionB = randomUUID();

mkdirSync(stateDir, { recursive: true });

const state = {
  evalId,
  evalType: "agent",
  taskId: task.id,
  taskName: task.name,
  startedAt: Date.now(),
  cwd,
  gitInited,
  startCommit: getHeadCommit(cwd),
  repoUrl: getRepoUrl(cwd),
  worktrees: { A: worktreeA, B: worktreeB },
  sessions: {
    A: { id: sessionA, cliType: sideACli.type, model: sideACli.model || "", alias: aliasA },
    B: { id: sessionB, cliType: sideBCli.type, model: sideBCli.model || "", alias: aliasB },
  },
};

writeFileSync(`${stateDir}/current.json`, JSON.stringify(state, null, 2));

// 向服务端注册评测（best-effort）：超时 2s，失败不阻塞终端启动
{
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 2000);
  try {
    const resp = await fetch(registerURL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${userApiKey}`,
      },
      body: JSON.stringify({
        evalId,
        evalType: "agent",
        taskId: task.id,
        sessions: [
          { side: "A", sessionId: sessionA, cliType: sideACli.type, cliVersion: sideACli.type === "claude" ? claudeVersion : mimoVersion, model: sideACli.model || "", cwd: worktreeA, repoUrl: state.repoUrl, startCommit: state.startCommit },
          { side: "B", sessionId: sessionB, cliType: sideBCli.type, cliVersion: sideBCli.type === "claude" ? claudeVersion : mimoVersion, model: sideBCli.model || "", cwd: worktreeB, repoUrl: state.repoUrl, startCommit: state.startCommit },
        ],
      }),
      signal: ctrl.signal,
    });
    if (resp.ok) {
      console.log(`📡 评测已注册到服务端（8h 兜底分析已入队）`);
    } else {
      console.warn(`⚠️  评测注册失败 (HTTP ${resp.status})，不阻塞终端启动`);
    }
  } catch (err: any) {
    if (err.name === "AbortError") {
      console.warn(`⚠️  评测注册超时（2s），不阻塞终端启动`);
    } else {
      console.warn(`⚠️  评测注册失败：${err.message}（不阻塞终端启动）`);
    }
  } finally {
    clearTimeout(timer);
  }
}

console.log(`\n📋 CLI 评测配置已写入 ${stateDir}/current.json`);
console.log(`   Eval ID: ${evalId}`);
console.log(`   Task: ${task.name} (ID: ${task.id})`);
console.log(`   ${aliasA} (Side A): ${sideACli.type} → ${worktreeA}`);
console.log(`   ${aliasB} (Side B): ${sideBCli.type} → ${worktreeB}`);
console.log(`   原始目录: ${cwd}\n`);

const skipPermissions = isDangerouslySkipPermissions(cwd);
if (skipPermissions) {
  console.log("⚠️ 检测到 --dangerously-skip-permissions 模式。");
}

// --- Open terminals ---
function shellEscape(s: string): string {
  return "'" + s.replace(/'/g, "'\\''") + "'";
}

// cmd.exe 参数转义：包在 "..." 中，内部 " 转为 \"，% 转为 %%（避免变量展开）。
function cmdQuote(s: string): string {
  return '"' + s.replace(/%/g, "%%").replace(/"/g, '\\"') + '"';
}

function quoteArg(s: string): string {
  return process.platform === "win32" ? cmdQuote(s) : shellEscape(s);
}

function buildClaudeCommand(
  side: "A" | "B",
  sessionId: string,
  alias: string,
  model: string,
  worktreePath: string,
) {
  const prompt = ` ${quoteArg(firstMessage)}`;
  const env: Record<string, string> = {
    MIMO_EVAL_ID: evalId,
    MIMO_SIDE: side,
    MIMO_SESSION_ID: sessionId,
    MIMO_TASK_ID: task.id,
    MIMO_USER_KEY: userApiKey,
    MIMO_CLI_TYPE: "claude",
    ANTHROPIC_BASE_URL: userBaseURL.replace(/\/+$/, ""),
    ANTHROPIC_API_KEY: userApiKey,
  };
  if (skipPermissions) {
    env.CLAUDE_BYPASS_PERMISSIONS = "true";
  }

  // Write a temporary settings file to override ~/.claude/settings.json env vars
  const evalSettings = join(EVAL_CONFIG.stateDir, "claude-settings.json");
  writeFileSync(evalSettings, JSON.stringify({
    env: {
      ANTHROPIC_BASE_URL: userBaseURL.replace(/\/+$/, ""),
      ANTHROPIC_API_KEY: userApiKey,
    },
  }, null, 2));

  const prefix = process.platform === "win32" ? "*" : "⬤";
  let command = `claude --settings "${evalSettings}" --model "${model}" --session-id "${sessionId}"`;
  if (skipPermissions) {
    command += " --dangerously-skip-permissions";
  }
  command += prompt;

  return {
    title: `${prefix} ${alias}`,
    cwd: worktreePath,
    env,
    command,
  };
}

function buildMimoCodeCommand(
  side: "A" | "B",
  sessionId: string,
  alias: string,
  worktreePath: string,
) {
  const env: Record<string, string> = {
    MIMO_EVAL_ID: evalId,
    MIMO_SIDE: side,
    MIMO_SESSION_ID: sessionId,
    MIMO_TASK_ID: task.id,
    MIMO_USER_KEY: userApiKey,
    MIMO_CLI_TYPE: "mimocode",
  };

  const prefix = process.platform === "win32" ? "*" : "⬤";
  const mimoCmd = process.platform === "win32" ? `"${mimoBin}"` : shellEscape(mimoBin);
  let command = mimoCmd;
  if (firstMessage) {
    command += ` --prompt ${quoteArg(firstMessage)}`;
  }

  const postCommand = [
    `echo ""`,
    `echo "════════════════════════════════════════"`,
    `echo "  MiMo Code 已退出，提交评测结果..."`,
    `echo "════════════════════════════════════════"`,
    `echo ""`,
    `cd ~/.claude/skills/mimo/skill && npx tsx src/submit-cli-eval.ts`,
  ].join("\n");

  return {
    title: `${prefix} ${alias}`,
    cwd: worktreePath,
    env,
    command,
    postCommand,
  };
}

function buildTerminalOpts(
  side: "A" | "B",
  sessionId: string,
  cli: { type: "claude" | "mimocode"; model?: string },
  alias: string,
  worktreePath: string,
) {
  if (cli.type === "claude") {
    return buildClaudeCommand(side, sessionId, alias, cli.model || task.cli_a.model || "claude-opus-4-7", worktreePath);
  }
  return buildMimoCodeCommand(side, sessionId, alias, worktreePath);
}

// Write mimocode.json config in the MiMo Code worktree
const mimoWorktree = sideACli.type === "mimocode" ? worktreeA : worktreeB;
const mimoSide = sideACli.type === "mimocode" ? "A" : "B";
const mimoModel = task.cli_a.model || "";
const mimoSessionId = sideACli.type === "mimocode" ? sessionA : sessionB;
const mimoConfig: Record<string, any> = {
  model: `mimorouter/${mimoModel}`,
  provider: {
    mimorouter: {
      npm: "@ai-sdk/openai-compatible",
      options: {
        apiKey: userApiKey,
        baseURL: `${userBaseURL}v1`,
        setCacheKey: true,
        headers: { "X-Eval-Session-Id": mimoSessionId },
      },
      models: {
        [mimoModel]: {
          name: mimoModel,
        },
      },
    },
  },
};
if (skipPermissions) {
  mimoConfig.permission = { "*": "allow" };
}
writeFileSync(join(mimoWorktree, "mimocode.json"), JSON.stringify(mimoConfig, null, 2));

// Write /mimo command for MiMo Code worktree (registered as TUI slash command)
const mimoCmdDir = join(mimoWorktree, ".mimocode", "commands");
mkdirSync(mimoCmdDir, { recursive: true });
writeFileSync(join(mimoCmdDir, "mimo.md"), `---
description: MiMo 评测提交
---

用户输入: $ARGUMENTS

从用户输入判断命令：

- \`submit\` 或 \`提交\` → 执行**提交结果**（见下方）
- **其他任何输入（包括为空、含义不明确）→ 不要猜测，不要执行任何操作**，直接输出以下帮助：

\`\`\`
📋 MiMo 评测命令：

  /mimo submit                  提交当前终端的评测结果

示例：
  /mimo submit
  /mimo 提交
\`\`\`

输出帮助后停止，不要做其他事情。

---

## 提交结果（/mimo submit 或 /mimo 提交）

**提交前用纯文本对话询问用户以下问题**（直接用文字输出问题让用户回复）：

一次性列出所有问题，让用户一次回复：

\`\`\`
请回答以下评测问题：

1. 是否采用了这一侧的代码产出？（输入 1/2/3）
   1=采用  2=部分采用  3=未采用

2. 使用体感打分 1-5（交互流畅度、理解力、是否需要反复纠正）

3. 产出效果打分 1-5（代码正确性、完整性、可用性）

4. 补充反馈（可选，无内容直接跳过）
\`\`\`

等用户回复后解析答案（如 "2 3 4" 或 "2，3，4，没什么问题"），然后执行：

\`\`\`bash
cd ~/.claude/skills/mimo/skill && MIMO_EVAL_ID="${evalId}" MIMO_SIDE="${mimoSide}" MIMO_SESSION_ID="${mimoSessionId}" MIMO_TASK_ID="${task.id}" MIMO_USER_KEY="${userApiKey}" MIMO_CLI_TYPE="mimocode" MIMO_ADOPTION="用户的选择1/2/3" MIMO_RATING="体感评分1-5" MIMO_OUTPUT_RATING="效果评分1-5" MIMO_FEEDBACK="用户的反馈文本" npx tsx src/submit-cli-eval.ts
\`\`\`

执行后告诉用户提交结果（成功或失败）。

如果报错"当前终端不是评测终端"，说明环境变量未注入；提醒用户在 MiMo Code 终端内执行 /mimo submit 完成提交（MiMo Code 侧不会在退出时自动提交）。
`);
console.log(`📝 已写入 MiMo Code 配置: ${mimoWorktree}/mimocode.json`);
if (skipPermissions) {
  console.log(`   ↳ 已为 MiMo Code 配置 permission: {"*":"allow"}，与 Claude 侧同等免授权`);
}

console.log("🚀 正在打开终端...\n");

openTerminalPair(
  buildTerminalOpts("A", sessionA, sideACli, aliasA, worktreeA),
  buildTerminalOpts("B", sessionB, sideBCli, aliasB, worktreeB),
);

console.log(`✅ 已打开两个终端：`);
console.log(`   ⬤ ${aliasA} — ${worktreeA}`);
console.log(`   ⬤ ${aliasB} — ${worktreeB}`);

const claudeSide = sideACli.type === "claude" ? aliasA : aliasB;
const mimocodeSide = sideACli.type === "mimocode" ? aliasA : aliasB;

console.log(`\n⚠️ 重要：`);
console.log(`   • 两个终端的首句内容必须完全一样，否则 AB 评测无效`);
console.log(`   • 完成后必须在两个终端分别执行 /mimo submit 提交，才算有效评测`);
if (firstMessage) {
  console.log(`\n📝 评测 Prompt:`);
  console.log(`   "${firstMessage}"`);
}
console.log(`\n📊 评测详情: http://mimorouter.llmcore.ai.srv/evaluation/agent-submissions`);

// ====== Helper functions ======

function isGitRepo(dir: string): boolean {
  try {
    execSync("git rev-parse --is-inside-work-tree", {
      cwd: dir,
      stdio: "pipe",
    });
    return true;
  } catch {
    return false;
  }
}

function hasCommits(dir: string): boolean {
  try {
    execSync("git rev-parse HEAD", { cwd: dir, stdio: "pipe" });
    return true;
  } catch {
    return false;
  }
}

function getHeadCommit(dir: string): string {
  try {
    return execSync("git rev-parse HEAD", { cwd: dir, encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return "";
  }
}

function getRepoUrl(dir: string): string {
  try {
    return execSync("git remote get-url origin", { cwd: dir, encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return "";
  }
}

function getGitRoot(dir: string): string {
  try {
    return execSync("git rev-parse --show-toplevel", { cwd: dir, encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return "";
  }
}

function setupWorktrees(projectDir: string, id: string): { worktreeA: string; worktreeB: string; gitInited: boolean } {
  let gitInited = false;

  if (!isGitRepo(projectDir)) {
    console.log("📦 当前目录非 git 仓库，正在初始化...");
    execSync("git init", { cwd: projectDir, stdio: "pipe" });
    execSync("git add -A", { cwd: projectDir, stdio: "pipe" });
    execSync('git commit -m "mimo eval: initial commit" --allow-empty', {
      cwd: projectDir,
      stdio: "pipe",
    });
    gitInited = true;
    console.log("   ✓ 已初始化 git 仓库并创建初始提交");
  } else if (!hasCommits(projectDir)) {
    execSync("git add -A", { cwd: projectDir, stdio: "pipe" });
    execSync('git commit -m "mimo eval: initial commit" --allow-empty', {
      cwd: projectDir,
      stdio: "pipe",
    });
    gitInited = true;
  }

  ensureGitignore(projectDir, ".mimo-worktrees");

  const worktreeBase = join(projectDir, ".mimo-worktrees");
  const pathA = join(worktreeBase, `eval-${id}-A`);
  const pathB = join(worktreeBase, `eval-${id}-B`);

  mkdirSync(worktreeBase, { recursive: true });

  execSync(`git worktree add "${pathA}" -b mimo-eval-${id}-A`, {
    cwd: projectDir,
    stdio: "pipe",
  });
  execSync(`git worktree add "${pathB}" -b mimo-eval-${id}-B`, {
    cwd: projectDir,
    stdio: "pipe",
  });

  console.log("🌲 已创建 worktree 隔离环境");

  return { worktreeA: pathA, worktreeB: pathB, gitInited };
}

function ensureGitignore(dir: string, entry: string) {
  const gitignorePath = join(dir, ".gitignore");
  try {
    if (existsSync(gitignorePath)) {
      const content = readFileSync(gitignorePath, "utf-8");
      if (content.split("\n").some((line) => line.trim() === entry)) return;
      writeFileSync(gitignorePath, content.trimEnd() + "\n" + entry + "\n");
    } else {
      writeFileSync(gitignorePath, entry + "\n");
    }
  } catch {}
}

function cleanupOldWorktrees(currentCwd: string) {
  const stateFile = `${stateDir}/current.json`;
  if (!existsSync(stateFile)) return;

  try {
    const oldState = JSON.parse(readFileSync(stateFile, "utf-8"));
    const oldCwd = oldState.cwd;
    if (!oldCwd || !isGitRepo(oldCwd)) return;

    // 仅清理「同一仓库」的上一条评测 worktree。跨仓库切换时保留旧仓库的
    // worktree，避免误删另一个项目里尚未提交/合并的评测产物。
    const oldRoot = getGitRoot(oldCwd);
    const curRoot = getGitRoot(currentCwd);
    if (oldRoot && curRoot && oldRoot !== curRoot) {
      console.log(`ℹ️ 上次评测在另一个仓库（${oldRoot}），其 worktree 保留未清理`);
      return;
    }

    const worktrees = oldState.worktrees;
    if (!worktrees) return;

    for (const side of ["A", "B"] as const) {
      const path = worktrees[side];
      if (path && existsSync(path)) {
        try {
          execSync(`git worktree remove "${path}" --force`, {
            cwd: oldCwd,
            stdio: "pipe",
          });
        } catch {}
      }
    }

    const oldId = oldState.evalId?.slice(0, 8);
    if (oldId) {
      try {
        execSync(
          `git branch -D mimo-eval-${oldId}-A mimo-eval-${oldId}-B 2>/dev/null || true`,
          { cwd: oldCwd, stdio: "pipe" },
        );
      } catch {}
    }

    const worktreeBase = join(oldCwd, ".mimo-worktrees");
    if (existsSync(worktreeBase)) {
      try {
        const remaining = readdirSync(worktreeBase);
        if (remaining.length === 0) {
          execSync(`rmdir "${worktreeBase}"`, { stdio: "pipe" });
        }
      } catch {}
    }

    console.log("🧹 已清理上次评测的 worktree");
  } catch {}
}

function isDangerouslySkipPermissions(userCwd: string): boolean {
  if (process.env.CLAUDE_BYPASS_PERMISSIONS === "true" || process.env.CLAUDE_BYPASS_PERMISSIONS === "1") {
    return true;
  }
  const mode = readPermissionModeFromSession(userCwd);
  if (mode !== null) {
    return mode === "bypassPermissions";
  }
  const getInfo = process.platform === "win32" ? getProcessInfoWin32 : getProcessInfoPosix;
  const seen = new Set<number>();
  let pid = process.ppid;
  for (let i = 0; i < 12; i++) {
    if (!pid || pid <= 0 || seen.has(pid)) break;
    seen.add(pid);
    const { cmdline, ppid } = getInfo(pid);
    if (cmdline.includes("--dangerously-skip-permissions")) return true;
    pid = ppid;
  }
  return false;
}

function getProcessInfoWin32(pid: number): { cmdline: string; ppid: number } {
  try {
    const out = execSync(
      `powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter 'ProcessId = ${pid}') | Select-Object CommandLine, ParentProcessId | ConvertTo-Json -Compress"`,
      { encoding: "utf-8", stdio: "pipe" },
    ).trim();
    if (!out) return { cmdline: "", ppid: 0 };
    const obj = JSON.parse(out);
    return {
      cmdline: typeof obj?.CommandLine === "string" ? obj.CommandLine : "",
      ppid: Number.isFinite(obj?.ParentProcessId) ? Number(obj.ParentProcessId) : 0,
    };
  } catch {
    return { cmdline: "", ppid: 0 };
  }
}

function getProcessInfoPosix(pid: number): { cmdline: string; ppid: number } {
  try {
    const cmdline = execSync(`ps -p ${pid} -o args=`, { encoding: "utf-8", stdio: "pipe" }) || "";
    const ppidOut = execSync(`ps -p ${pid} -o ppid=`, { encoding: "utf-8", stdio: "pipe" }) || "";
    const ppid = parseInt(ppidOut.trim(), 10);
    return { cmdline, ppid: Number.isFinite(ppid) ? ppid : 0 };
  } catch {
    return { cmdline: "", ppid: 0 };
  }
}

function readPermissionModeFromSession(userCwd: string): string | null {
  const slug = userCwd.replace(/[\\/:.]/g, "-");
  const projectDir = join(homedir(), ".claude", "projects", slug);
  if (!existsSync(projectDir)) return null;

  const sessionId = process.env.CLAUDE_CODE_SESSION_ID;
  let jsonl = sessionId ? join(projectDir, `${sessionId}.jsonl`) : "";
  if (!jsonl || !existsSync(jsonl)) {
    let bestMtime = 0;
    jsonl = "";
    for (const f of readdirSync(projectDir)) {
      if (!f.endsWith(".jsonl")) continue;
      const p = join(projectDir, f);
      const m = statSync(p).mtimeMs;
      if (m > bestMtime) { bestMtime = m; jsonl = p; }
    }
  }
  if (!jsonl) return null;

  try {
    const lines = readFileSync(jsonl, "utf-8").split("\n");
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i].trim();
      if (!line || !line.includes('"permission-mode"')) continue;
      try {
        const obj = JSON.parse(line);
        if (obj.type === "permission-mode" && typeof obj.permissionMode === "string") {
          return obj.permissionMode;
        }
      } catch {}
    }
  } catch {}
  return null;
}
