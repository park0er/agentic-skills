import { randomUUID } from "crypto";
import { mkdirSync, writeFileSync, readFileSync, existsSync, readdirSync } from "fs";
import { execSync } from "child_process";
import { join } from "path";
import { checkUpdate } from "./update.js";
import { EVAL_CONFIG } from "./eval-config.js";
import { ClaudeProcess } from "./web/claude-process.js";
import { startWebServer, broadcast } from "./web/server.js";

if (await checkUpdate()) { const { execFileSync } = await import("child_process"); try { execFileSync(process.execPath, process.execArgv.concat(process.argv.slice(1)), { stdio: "inherit", env: process.env }); } catch {} process.exit(0); }

const { stateDir, routerURL, registerURL } = EVAL_CONFIG;
const PORT = Number(process.env.PORT) || 3457;

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

// ====== Fetch task from server ======

let modelA = "";
let modelB = "";
let taskId = "";
let taskName = "";

try {
  const resp = await fetch(`${routerURL}v1/eval/task/current`);
  if (resp.ok) {
    const { data } = (await resp.json()) as any;
    if (data) {
      modelA = data.model_a;
      modelB = data.model_b;
      taskId = String(data.id);
      taskName = data.name;
      console.log(`📋 评测任务: ${taskName}`);
    }
  }
} catch {}

if (!modelA || !modelB) {
  // Fallback to default models if no task is configured
  modelA = process.env.MIMO_MODEL_A || "claude-sonnet-4-20250514";
  modelB = process.env.MIMO_MODEL_B || "mimo-v2-pro";
  taskId = "standalone";
  taskName = "独立评测模式";
  console.log(`📋 无远程任务，使用默认模型: A=${modelA}, B=${modelB}`);
}

// CLI 需要 provider/model 格式；任务服务端返回的短名称需要加前缀
// 直接使用 task 下发的模型名，router 会处理映射

// ====== Git worktree setup (from start.ts) ======

function isGitRepo(dir: string): boolean {
  try {
    execSync("git rev-parse --is-inside-work-tree", { cwd: dir, stdio: "pipe" });
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

// Save state
const sessionA = randomUUID();
const sessionB = randomUUID();

function getHeadCommit(dir: string): string {
  try {
    return execSync("git rev-parse HEAD", { cwd: dir, encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return "";
  }
}

function getGitRemoteUrl(): string {
  try {
    return execSync("git remote get-url origin", { cwd: projectDir, encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return "";
  }
}

const startCommit = getHeadCommit(projectDir);
const repoUrl = getGitRemoteUrl();

mkdirSync(stateDir, { recursive: true });
const state = {
  evalId, taskId, taskName,
  startedAt: Date.now(),
  cwd: projectDir, gitInited,
  startCommit,
  worktrees: { A: worktreeA, B: worktreeB },
  sessions: { A: { id: sessionA, model: modelA }, B: { id: sessionB, model: modelB } },
};
writeFileSync(`${stateDir}/current.json`, JSON.stringify(state, null, 2));

// ====== Start Claude processes ======

const procA = new ClaudeProcess();
const procB = new ClaudeProcess();

procA.on("event", (event) => broadcast({ type: "stream_event", side: "A", event }));
procB.on("event", (event) => broadcast({ type: "stream_event", side: "B", event }));
procA.on("stderr", (data) => console.error("[A stderr]", data));
procB.on("stderr", (data) => console.error("[B stderr]", data));
procA.on("error", (err) => console.error("[A error]", err.message));
procB.on("error", (err) => console.error("[B error]", err.message));

console.log(`\n🚀 启动 Claude 进程...`);
console.log(`   模型 A: ${modelA} → ${worktreeA}`);
console.log(`   模型 B: ${modelB} → ${worktreeB}`);

const skipPermissions = true; // web mode needs non-interactive

procA.spawn({
  workdir: worktreeA, model: modelA,
  apiKey: userApiKey, baseURL: routerURL,
  sessionId: sessionA, skipPermissions,
});
procB.spawn({
  workdir: worktreeB, model: modelB,
  apiKey: userApiKey, baseURL: routerURL,
  sessionId: sessionB, skipPermissions,
});

// Wait for both processes to be ready
await Promise.all([
  new Promise<void>((resolve) => procA.once("ready", resolve)),
  new Promise<void>((resolve) => procB.once("ready", resolve)),
]);
console.log("✅ Claude 进程就绪");

// ====== Submit helper ======

async function submitSide(side: "A" | "B", adoption = "", rating = 0, outputRating = 0, feedback = "") {
  const session = side === "A" ? sessionA : sessionB;
  const model = side === "A" ? modelA : modelB;
  const endCommit = getHeadCommit(side === "A" ? worktreeA : worktreeB);

  const payload = {
    evalId, side, sessionId: session, model,
    taskId: taskId || "",
    turnCount: 0, // web mode doesn't easily track turns
    contentLength: 0,
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
      console.log(`✅ Side ${side} 提交成功`);
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
  procA.kill();
  procB.kill();
  server.close();
  process.exit(0);
}

// Auto-submit timeout (8 hours)
const AUTO_SUBMIT_MS = 8 * 60 * 60 * 1000;
const autoSubmitTimer = setTimeout(async () => {
  console.log("⏰ 8 小时超时，自动提交评测结果...");
  await Promise.all([submitSide("A"), submitSide("B")]);
  cleanup();
}, AUTO_SUBMIT_MS);

const server = startWebServer({
  port: PORT,
  onUserMessage: (text: string, side?: string) => {
    console.log(`💬 用户消息 [${side || "both"}]: ${text.slice(0, 50)}...`);
    if (side === "A") {
      procA.sendMessage(text);
    } else if (side === "B") {
      procB.sendMessage(text);
    } else {
      procA.sendMessage(text);
      procB.sendMessage(text);
    }
  },
  onSubmitSide: async (side: string, feedback: { adoption?: string; rating?: number; output_rating?: number; feedback?: string; resubmit?: boolean }) => {
    // 不伪造默认值:用户给什么就提交什么,未填即如实空值(''/0),云端按 rating>0/adoption!='' 判定是否已评分。
    const adoption = feedback?.adoption || "";
    const rating = feedback?.rating || 0;
    const outputRating = feedback?.output_rating || 0;
    const fb = feedback?.feedback || "";
    const isResubmit = feedback?.resubmit || false;
    console.log(`📤 ${isResubmit ? '重新' : ''}提交 Side ${side} 结果 (adoption=${adoption || '未评'}, rating=${rating || '未评'}, output=${outputRating || '未评'})`);
    await submitSide(side as "A" | "B", adoption, rating, outputRating, fb);
    if (isResubmit) {
      // Trigger re-analysis on server
      try {
        await fetch(`${routerURL}v1/eval/analysis/${evalId}/trigger`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${userApiKey}` },
        });
        console.log(`🔄 已触发重新打分`);
      } catch {}
    }
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

broadcast({ type: "eval_started", evalId, modelA, modelB, taskName, sessionA, sessionB });

// Register eval with server (same as terminal start.ts)
try {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 2000);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (userApiKey) headers["Authorization"] = `Bearer ${userApiKey}`;
  await fetch(registerURL, {
    method: "POST", headers,
    body: JSON.stringify({
      evalId, taskId,
      sessions: [
        { side: "A", sessionId: sessionA, model: modelA, cwd: worktreeA },
        { side: "B", sessionId: sessionB, model: modelB, cwd: worktreeB },
      ],
    }),
    signal: ctrl.signal,
  }).catch(() => {});
  clearTimeout(timer);
  console.log("📋 已注册到服务器");
} catch {}

// Inject first message if provided
const firstMessage = process.env.MIMO_FIRST_MESSAGE?.trim();
if (firstMessage) {
  setTimeout(() => {
    procA.sendMessage(firstMessage);
    procB.sendMessage(firstMessage);
    broadcast({ type: "first_message", text: firstMessage });
    console.log(`📝 首句已注入: "${firstMessage.slice(0, 30)}..."`);
  }, 1000);
}

// ====== Open browser ======

const url = `http://localhost:${PORT}`;
try {
  const cmd = process.platform === "darwin" ? "open" : process.platform === "win32" ? "start" : "xdg-open";
  execSync(`${cmd} "${url}"`, { stdio: "pipe" });
} catch {
  console.log(`\n请手动打开浏览器: ${url}`);
}

process.on("SIGINT", cleanup);
process.on("SIGTERM", cleanup);
