import { randomUUID } from "crypto";
import { mkdirSync, writeFileSync, readFileSync, existsSync, readdirSync } from "fs";
import { execSync } from "child_process";
import { join } from "path";
import { checkUpdate } from "./update.js";
import { EVAL_CONFIG } from "./eval-config.js";
import { ClaudeProcess } from "./web/claude-process.js";
import { MimoProcess } from "./web/mimo-process.js";
import { startWebServer, broadcast } from "./web/server.js";
import { ensureMimoCodeUpdated } from "./mimo-update.js";

if (await checkUpdate()) { const { execFileSync } = await import("child_process"); try { execFileSync(process.execPath, process.execArgv.concat(process.argv.slice(1)), { stdio: "inherit", env: process.env }); } catch {} process.exit(0); }

const { stateDir, routerURL, registerURL } = EVAL_CONFIG;
const PORT = Number(process.env.PORT) || 3458;
const MIMO_SERVE_PORT = Number(process.env.MIMO_SERVE_PORT) || 3459;

// ====== Config & Auth ======

import { loadKey, login } from "./auth.js";

let userApiKey = loadKey();
if (!userApiKey) {
  userApiKey = await login();
}

// ====== Project directory ======

const projectDir = process.argv[2] || process.cwd();
if (!existsSync(projectDir)) {
  console.error(`❌ 目录不存在: ${projectDir}`);
  process.exit(1);
}

// ====== Check mimocode installation & update ======
ensureMimoCodeUpdated("mimo");

// ====== Fetch task ======

let model = "";
let taskId = "";
let taskName = "Claude Code vs MiMo Code";

try {
  const resp = await fetch(`${routerURL}v1/eval/task/current?type=agent`);
  if (resp.ok) {
    const { data } = (await resp.json()) as any;
    if (data) {
      taskId = String(data.id);
      taskName = data.name || taskName;
      // Get model from config
      try {
        const config = JSON.parse(data.config || "{}");
        model = config.cli_b?.model || data.model_a || "";
      } catch {}
      if (!model) model = data.model_a || "";
      console.log(`📋 Agent 评测任务: ${taskName}`);
      if (data.reward_multiplier && data.reward_multiplier > 1) {
        console.log(`🔥 赏金任务！本次评测奖励 x${data.reward_multiplier} 倍`);
      }
    }
  }
} catch {}

if (!model) {
  // Fallback: try regular task for model
  try {
    const resp = await fetch(`${routerURL}v1/eval/task/current`);
    if (resp.ok) {
      const { data } = (await resp.json()) as any;
      if (data?.model_a) {
        model = data.model_a;
        if (!taskId) taskId = String(data.id);
      }
    }
  } catch {}
}

if (!model) {
  model = process.env.MIMO_MODEL || "xiaomi/mimo-coder";
  console.log(`📋 使用默认模型: ${model}`);
}

// ====== Random assignment ======

const shuffle = Math.random() > 0.5;
const sideAType = shuffle ? "mimocode" : "claude";
const sideBType = shuffle ? "claude" : "mimocode";
const aliasA = "Alpha";
const aliasB = "Beta";

// ====== Git worktree setup ======

function isGitRepo(dir: string): boolean {
  try {
    execSync("git rev-parse --is-inside-work-tree", { cwd: dir, stdio: "pipe" });
    return true;
  } catch { return false; }
}

function hasCommits(dir: string): boolean {
  try {
    execSync("git rev-parse HEAD", { cwd: dir, stdio: "pipe" });
    return true;
  } catch { return false; }
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

// Cleanup old worktrees
const oldStateFile = `${stateDir}/current.json`;
if (existsSync(oldStateFile)) {
  try {
    const old = JSON.parse(readFileSync(oldStateFile, "utf-8"));
    if (old.worktrees && old.cwd && isGitRepo(old.cwd)) {
      for (const side of ["A", "B"] as const) {
        const p = old.worktrees[side];
        if (p && existsSync(p)) {
          try { execSync(`git worktree remove "${p}" --force`, { cwd: old.cwd, stdio: "pipe" }); } catch {}
        }
      }
      const oldId = old.evalId?.slice(0, 8);
      if (oldId) {
        try { execSync(`git branch -D mimo-eval-${oldId}-A mimo-eval-${oldId}-B 2>/dev/null || true`, { cwd: old.cwd, stdio: "pipe" }); } catch {}
      }
      console.log("🧹 已清理上次评测的 worktree");
    }
  } catch {}
}

// Setup new worktrees
const evalId = randomUUID();
const shortId = evalId.slice(0, 8);
let gitInited = false;

if (!isGitRepo(projectDir)) {
  console.log("📦 初始化 git 仓库...");
  execSync("git init", { cwd: projectDir, stdio: "pipe" });
  execSync("git add -A", { cwd: projectDir, stdio: "pipe" });
  execSync('git commit -m "mimo eval: initial commit" --allow-empty', { cwd: projectDir, stdio: "pipe" });
  gitInited = true;
} else if (!hasCommits(projectDir)) {
  execSync("git add -A", { cwd: projectDir, stdio: "pipe" });
  execSync('git commit -m "mimo eval: initial commit" --allow-empty', { cwd: projectDir, stdio: "pipe" });
  gitInited = true;
}

ensureGitignore(projectDir, ".mimo-worktrees");

const worktreeBase = join(projectDir, ".mimo-worktrees");
const worktreeA = join(worktreeBase, `eval-${shortId}-A`);
const worktreeB = join(worktreeBase, `eval-${shortId}-B`);

mkdirSync(worktreeBase, { recursive: true });
execSync(`git worktree add "${worktreeA}" -b mimo-eval-${shortId}-A`, { cwd: projectDir, stdio: "pipe" });
execSync(`git worktree add "${worktreeB}" -b mimo-eval-${shortId}-B`, { cwd: projectDir, stdio: "pipe" });
console.log("🌲 Worktree 已创建");

// ====== Save state ======

const sessionA = randomUUID();
const sessionB = randomUUID();

function getHeadCommit(dir: string): string {
  try {
    return execSync("git rev-parse HEAD", { cwd: dir, encoding: "utf-8", stdio: "pipe" }).trim();
  } catch { return ""; }
}

function getGitRemoteUrl(): string {
  try {
    return execSync("git remote get-url origin", { cwd: projectDir, encoding: "utf-8", stdio: "pipe" }).trim();
  } catch { return ""; }
}

const startCommit = getHeadCommit(projectDir);
const repoUrl = getGitRemoteUrl();

mkdirSync(stateDir, { recursive: true });
const state = {
  evalId, evalType: "agent", taskId, taskName,
  startedAt: Date.now(),
  cwd: projectDir, gitInited, startCommit,
  worktrees: { A: worktreeA, B: worktreeB },
  sessions: {
    A: { id: sessionA, cliType: sideAType, model: sideAType === "claude" ? model : "", alias: aliasA },
    B: { id: sessionB, cliType: sideBType, model: sideBType === "claude" ? model : "", alias: aliasB },
  },
};
writeFileSync(`${stateDir}/current.json`, JSON.stringify(state, null, 2));

// ====== Start processes ======

const claudeSide = sideAType === "claude" ? "A" : "B";
const mimoSide = sideAType === "mimocode" ? "A" : "B";
const claudeWorktree = claudeSide === "A" ? worktreeA : worktreeB;
const mimoWorktree = mimoSide === "A" ? worktreeA : worktreeB;
const claudeSession = claudeSide === "A" ? sessionA : sessionB;

const claudeProc = new ClaudeProcess();
const mimoProc = new MimoProcess();

claudeProc.on("event", (event) => broadcast({ type: "stream_event", side: claudeSide, event }));
claudeProc.on("stderr", (data) => console.error(`[${claudeSide} Claude stderr]`, data));
claudeProc.on("error", (err) => console.error(`[${claudeSide} Claude error]`, err.message));

mimoProc.on("event", (event) => broadcast({ type: "stream_event", side: mimoSide, event }));
mimoProc.on("stderr", (data) => console.error(`[${mimoSide} MiMo Code stderr]`, data));
mimoProc.on("error", (err) => console.error(`[${mimoSide} MiMo Code error]`, err.message));

console.log(`\n🚀 启动进程...`);
console.log(`   ${aliasA} (Side A): ${sideAType} → ${worktreeA}`);
console.log(`   ${aliasB} (Side B): ${sideBType} → ${worktreeB}`);

// Write mimocode.json config in the MiMo Code worktree
const mimoSessionId = mimoSide === "A" ? sessionA : sessionB;
const mimoConfig = {
  model: `mimorouter/${model}`,
  provider: {
    mimorouter: {
      npm: "@ai-sdk/openai-compatible",
      options: {
        apiKey: userApiKey,
        baseURL: `${routerURL}v1`,
        setCacheKey: true,
        headers: { "X-Eval-Session-Id": mimoSessionId },
      },
      models: {
        [model]: {
          name: model,
        },
      },
    },
  },
  permission: { "*": "allow" },
};
writeFileSync(join(mimoWorktree, "mimocode.json"), JSON.stringify(mimoConfig, null, 2));

// Start Claude process
const claudeReady = new Promise<void>((resolve) => claudeProc.once("ready", resolve));
claudeProc.spawn({
  workdir: claudeWorktree,
  model,
  apiKey: userApiKey,
  baseURL: routerURL.replace(/\/+$/, ""),
  sessionId: claudeSession,
  skipPermissions: true,
});

// Start MiMo Code server
// Start MiMo Code server (no password — local only)
await mimoProc.spawn({
  workdir: mimoWorktree,
  port: MIMO_SERVE_PORT,
});

// Create session in mimo
await mimoProc.createSession();

await claudeReady;
console.log("✅ 双侧进程就绪");

// ====== Submit helper ======

async function submitSide(side: "A" | "B", adoption = "", rating = 0, outputRating = 0, feedback = "") {
  const session = side === "A" ? sessionA : sessionB;
  const cliType = side === claudeSide ? "claude" : "mimocode";
  const sideModel = cliType === "claude" ? model : "";
  const endCommit = getHeadCommit(side === "A" ? worktreeA : worktreeB);

  const payload: any = {
    evalId, evalType: "agent", side, sessionId: session,
    model: sideModel, cliType,
    taskId: taskId || "",
    turnCount: 0, contentLength: 0,
    submitter: "", cwd: projectDir, repoUrl,
    startCommit, endCommit,
    adoption, rating, outputRating, feedback,
    submittedAt: Date.now(),
  };

  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (userApiKey) headers["Authorization"] = `Bearer ${userApiKey}`;
    const resp = await fetch(`${routerURL}v1/eval/submit`, {
      method: "POST", headers, body: JSON.stringify(payload),
    });
    if (resp.ok) {
      console.log(`✅ Side ${side} (${cliType}) 提交成功`);
    } else {
      console.error(`❌ Side ${side} 提交失败 (${resp.status})`);
    }
  } catch (err: any) {
    console.error(`❌ Side ${side} 提交失败: ${err.message}`);
  }
}

// ====== Start web server ======

function cleanup() {
  console.log("\n🛑 正在关闭...");
  claudeProc.kill();
  mimoProc.kill();
  server.close();
  process.exit(0);
}

const AUTO_SUBMIT_MS = 8 * 60 * 60 * 1000;
const autoSubmitTimer = setTimeout(async () => {
  console.log("⏰ 8 小时超时，自动提交评测结果...");
  await Promise.all([submitSide("A"), submitSide("B")]);
  cleanup();
}, AUTO_SUBMIT_MS);

// Kill any existing process on web server port
try {
  const pids = execSync(`lsof -ti :${PORT}`, { encoding: "utf-8", stdio: "pipe" }).trim();
  if (pids) {
    execSync(`kill -9 ${pids.split("\n").join(" ")}`, { stdio: "pipe" });
    await new Promise((r) => setTimeout(r, 500));
  }
} catch {}

const server = startWebServer({
  port: PORT,
  onUserMessage: (text: string, side?: string) => {
    console.log(`💬 用户消息 [${side || "both"}]: ${text.slice(0, 50)}...`);
    if (side === "A") {
      if (sideAType === "claude") claudeProc.sendMessage(text);
      else mimoProc.sendMessage(text);
    } else if (side === "B") {
      if (sideBType === "claude") claudeProc.sendMessage(text);
      else mimoProc.sendMessage(text);
    } else {
      claudeProc.sendMessage(text);
      mimoProc.sendMessage(text);
    }
  },
  onSubmitSide: async (side: string, feedback: { adoption?: string; rating?: number; output_rating?: number; feedback?: string; resubmit?: boolean }) => {
    // 不伪造默认值:用户给什么提交什么,未填即如实空值(''/0)。
    const adoption = feedback?.adoption || "";
    const rating = feedback?.rating || 0;
    const outputRating = feedback?.output_rating || 0;
    const fb = feedback?.feedback || "";
    console.log(`📤 提交 Side ${side} 结果 (adoption=${adoption || '未评'}, rating=${rating || '未评'}, output=${outputRating || '未评'})`);
    await submitSide(side as "A" | "B", adoption, rating, outputRating, fb);
  },
  onEnd: async (feedback?: { adoption?: string; rating?: number; output_rating?: number; feedback?: string }) => {
    clearTimeout(autoSubmitTimer);
    const adoption = feedback?.adoption || "";
    const rating = feedback?.rating || 0;
    const outputRating = feedback?.output_rating || 0;
    const fb = feedback?.feedback || "";
    // 仅当用户实际填了评分/反馈才提交(避免空值覆盖已分别提交的真实评分);未填则不提交,绝不伪造。
    if (adoption || rating || outputRating || fb) {
      console.log("📤 提交评测结果...");
      await Promise.all([
        submitSide("A", adoption, rating, outputRating, fb),
        submitSide("B", adoption, rating, outputRating, fb),
      ]);
    }
    broadcast({ type: "eval_ended" });
    setTimeout(cleanup, 1000);
  },
});

// Broadcast eval started (hide CLI types behind aliases)
// Show CLI types as panel names (not hidden for web mode)
const labelA = sideAType === "claude" ? "Claude Code" : "MiMo Code";
const labelB = sideBType === "claude" ? "Claude Code" : "MiMo Code";
broadcast({
  type: "eval_started", evalId,
  modelA: labelA, modelB: labelB,
  taskName, sessionA, sessionB,
});

// Register with server
try {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 2000);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (userApiKey) headers["Authorization"] = `Bearer ${userApiKey}`;
  await fetch(registerURL, {
    method: "POST", headers,
    body: JSON.stringify({
      evalId, evalType: "agent", taskId,
      sessions: [
        { side: "A", sessionId: sessionA, cliType: sideAType, model: sideAType === "claude" ? model : "", cwd: worktreeA },
        { side: "B", sessionId: sessionB, cliType: sideBType, model: sideBType === "claude" ? model : "", cwd: worktreeB },
      ],
    }),
    signal: ctrl.signal,
  }).catch(() => {});
  clearTimeout(timer);
  console.log("📡 已注册到服务端");
} catch {}

// Inject first message
const firstMessage = process.env.MIMO_FIRST_MESSAGE?.trim();
if (firstMessage) {
  setTimeout(async () => {
    try {
      await claudeProc.sendMessage(firstMessage);
      console.log(`📝 Claude 首句已注入`);
    } catch (e: any) {
      console.error(`❌ Claude 首句注入失败: ${e.message}`);
    }
    // MiMo Code needs extra delay after session creation
    await new Promise(r => setTimeout(r, 2000));
    try {
      await mimoProc.sendMessage(firstMessage);
      console.log(`📝 MiMo Code 首句已注入`);
    } catch (e: any) {
      console.error(`❌ MiMo Code 首句注入失败: ${e.message}`);
    }
    broadcast({ type: "first_message", text: firstMessage });
    console.log(`📝 首句已注入: "${firstMessage.slice(0, 30)}..."`);
  }, 2000);
}

// ====== Open browser ======

const url = `http://localhost:${PORT}`;
try {
  const cmd = process.platform === "darwin" ? "open" : process.platform === "win32" ? "start" : "xdg-open";
  execSync(`${cmd} "${url}"`, { stdio: "pipe" });
} catch {
  console.log(`\n请手动打开浏览器: ${url}`);
}

console.log(`\n🌐 Agent 评测 Web 界面: ${url}`);
console.log(`   ${aliasA} (${sideAType}) | ${aliasB} (${sideBType})`);
console.log(`   评测 ID: ${evalId}`);

process.on("SIGINT", cleanup);
process.on("SIGTERM", cleanup);
