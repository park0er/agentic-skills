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
import { loadKey, saveKey, login } from "./auth.js";

if (await checkUpdate()) { const { execFileSync } = await import("child_process"); try { execFileSync(process.execPath, process.execArgv.concat(process.argv.slice(1)), { stdio: "inherit", env: process.env }); } catch {} process.exit(0); }

const { stateDir, routerURL, registerURL } = EVAL_CONFIG;

// --- Auth: load key or trigger login ---
let userApiKey = loadKey();

// Handle inline key saving
if (process.env.MIMO_INLINE_KEY && userApiKey === process.env.MIMO_INLINE_KEY) {
  saveKey(userApiKey);
  console.log(`🔑 密钥已保存，后续无需重复输入`);
}

if (!userApiKey) {
  userApiKey = await login();
}

const userBaseURL = routerURL;

// MIMO_USER_CWD 必须显式从 SKILL.md 启动命令传入；
// 不再 fallback 到 process.cwd()，否则会把 worktree 创建到 skill 目录里
const cwd = process.env.MIMO_USER_CWD;
if (!cwd) {
  console.error("❌ MIMO_USER_CWD 未设置。");
  console.error("");
  console.error("请通过 /mimo 命令启动评测；如需手动调用，使用：");
  console.error('  ORIG_PWD="$PWD" && cd ~/.claude/skills/mimo/skill && \\');
  console.error('    MIMO_USER_CWD="$ORIG_PWD" npx tsx src/start.ts');
  process.exit(1);
}

// Fetch current task from server
let modelA = "";
let modelB = "";
let taskId = "";
let taskName = "";

const firstMessage = process.env.MIMO_FIRST_MESSAGE?.trim() || "";
if (!firstMessage) {
  console.error("❌ 未提供评测 prompt。");
  console.error("");
  console.error("用法：/mimo <你的开发任务>");
  console.error("示例：/mimo 帮我实现一个登录页面");
  process.exit(1);
}

try {
  const resp = await fetch(`${routerURL}v1/eval/task/current`);
  if (resp.ok) {
    const { data } = (await resp.json()) as any;
    if (data) {
      modelA = data.model_a;
      modelB = data.model_b;
      taskId = String(data.id);
      taskName = data.name;
      console.log(`📋 获取到评测任务: ${taskName}`);
    }
  } else {
    const text = await resp.text().catch(() => "");
    console.error(`❌ 拉取任务失败 (HTTP ${resp.status})`);
    console.error(`   URL: ${routerURL}v1/eval/task/current`);
    if (text) console.error(`   响应: ${text.slice(0, 200)}`);
    process.exit(1);
  }
} catch (err: any) {
  console.error(`❌ 拉取任务失败：无法连接服务器`);
  console.error(`   URL: ${routerURL}v1/eval/task/current`);
  console.error(`   错误: ${err.message}`);
  process.exit(1);
}

if (!modelA || !modelB) {
  console.error("❌ 当前无评测任务，无法启动。");
  console.error("   请联系管理员在 /evaluation 页面创建评测任务。");
  process.exit(1);
}

// CLI 需要 provider/model 格式；任务服务端返回的短名称需要加前缀
// 直接使用 task 下发的模型名，router 会处理映射

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
  taskId,
  taskName,
  startedAt: Date.now(),
  cwd,
  gitInited,
  startCommit: getHeadCommit(cwd),
  worktrees: { A: worktreeA, B: worktreeB },
  sessions: {
    A: { id: sessionA, model: modelA },
    B: { id: sessionB, model: modelB },
  },
};

writeFileSync(`${stateDir}/current.json`, JSON.stringify(state, null, 2));

// 向服务端注册评测（best-effort）：创建 pair + placeholder submissions + 入队 8h 兜底分析
// 超时 2s，失败不阻塞终端启动
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
        taskId,
        sessions: [
          { side: "A", sessionId: sessionA, model: modelA, cwd: worktreeA },
          { side: "B", sessionId: sessionB, model: modelB, cwd: worktreeB },
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

console.log(`\n📋 评测配置已写入 ${stateDir}/current.json`);
console.log(`   Eval ID: ${evalId}`);
if (taskId) console.log(`   Task: ${taskName} (ID: ${taskId})`);
console.log(`   模型 A: ${modelA} → ${worktreeA}`);
console.log(`   模型 B: ${modelB} → ${worktreeB}`);
console.log(`   原始目录: ${cwd}\n`);

const skipPermissions = isDangerouslySkipPermissions(cwd);
if (skipPermissions) {
  console.log("⚠️ 检测到 --dangerously-skip-permissions 模式，评测子终端也将以该模式启动。");
}

// --- Open terminals ---
function shellEscape(s: string): string {
  return "'" + s.replace(/'/g, "'\\''") + "'";
}

function buildTerminalOpts(
  side: "A" | "B",
  sessionId: string,
  modelName: string,
  worktreePath: string,
) {
  const prompt = ` ${shellEscape(firstMessage)}`;
  const env: Record<string, string> = {
    MIMO_EVAL_ID: evalId,
    MIMO_SIDE: side,
    MIMO_SESSION_ID: sessionId,
    MIMO_TASK_ID: taskId,
    MIMO_USER_KEY: userApiKey,
    ANTHROPIC_BASE_URL: userBaseURL.replace(/\/+$/, ""),
    ANTHROPIC_API_KEY: userApiKey,
  };
  if (skipPermissions) {
    env.CLAUDE_BYPASS_PERMISSIONS = "true";
  }

  const prefix = process.platform === "win32" ? "*" : "⬤";
  let command = `claude --model "${modelName}" --session-id "${sessionId}"`;
  if (skipPermissions) {
    command += " --dangerously-skip-permissions";
  }
  command += prompt;

  return {
    title: `${prefix} ${modelName}`,
    cwd: worktreePath,
    env,
    command,
  };
}

console.log("🚀 正在打开终端...\n");

openTerminalPair(
  buildTerminalOpts("A", sessionA, modelA, worktreeA),
  buildTerminalOpts("B", sessionB, modelB, worktreeB),
);

console.log(`✅ 已打开两个终端：`);
console.log(`   ⬤ ${modelA} — ${worktreeA}`);
console.log(`   ⬤ ${modelB} — ${worktreeB}`);
console.log(`\n📝 首句已自动注入: "${firstMessage}"`);
console.log(`AB 评测已经提交到 mimorouter 后台`);
console.log(`\n💡 完成开发后，在每个终端中执行 /mimo submit 提交结果`);
console.log(`⏰ 如未手动 submit ，8 小时后将自动触发评测分析`);
console.log(`   提交后 worktree 会自动清理`);
console.log(`\n📊 评测详情: http://mimorouter.llmcore.ai.srv/evaluation/model-submissions`);

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

function getGitRoot(dir: string): string {
  try {
    return execSync("git rev-parse --show-toplevel", { cwd: dir, encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return "";
  }
}

function setupWorktrees(projectDir: string, id: string): { worktreeA: string; worktreeB: string; gitInited: boolean } {
  let gitInited = false;

  // Ensure git repo exists
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

  // Ensure .mimo-worktrees is gitignored
  ensureGitignore(projectDir, ".mimo-worktrees");

  // Create worktrees
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
  } catch {
    // best effort
  }
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
        } catch {
          // already removed or detached
        }
      }
    }

    // Clean up branches
    const oldId = oldState.evalId?.slice(0, 8);
    if (oldId) {
      try {
        execSync(
          `git branch -D mimo-eval-${oldId}-A mimo-eval-${oldId}-B 2>/dev/null || true`,
          { cwd: oldCwd, stdio: "pipe" },
        );
      } catch {}
    }

    // Remove .mimo-worktrees dir if empty
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
  } catch {
    // old state corrupt, skip
  }
}

// 检测启动方 Claude Code 是否处于 --dangerously-skip-permissions 模式。
// 三档：
// 1、env CLAUDE_BYPASS_PERMISSIONS（用户显式声明，最高优先级）
// 2、读父会话 jsonl 的 permission-mode 事件（Claude Code 自己写的权威来源）
// 3、扫父进程链 cmdline（POSIX 一般可靠；Windows 上 Bash 工具链常断，仅兜底）
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

// 读父 Claude Code 的 session jsonl，取最新一条 permission-mode 事件。
// jsonl 在 ~/.claude/projects/<slug>/ 下，slug = userCwd 中 [\\/:.] 替换为 '-'。
// CLAUDE_CODE_SESSION_ID 在 Windows 的 Bash 工具子进程里通常拿不到，
// 没有时退化为目录下 mtime 最新的 jsonl（即当前活跃会话）。
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