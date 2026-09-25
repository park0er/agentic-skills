import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { execSync } from "child_process";
import { createInterface } from "readline";
import { checkUpdate } from "./update.js";
import { EVAL_CONFIG } from "./eval-config.js";

await checkUpdate();

const { stateDir, submitURL } = EVAL_CONFIG;

const evalId = process.env.MIMO_EVAL_ID;
const side = process.env.MIMO_SIDE;
const sessionId = process.env.MIMO_SESSION_ID;
const userKey = process.env.MIMO_USER_KEY;
const taskIdEnv = process.env.MIMO_TASK_ID;
const cliType = process.env.MIMO_CLI_TYPE || "mimocode";

if (!evalId || !side || !sessionId) {
  console.error("❌ 错误：当前终端不是评测终端。");
  console.error("   请在通过 /mimocode 启动的评测终端中执行此命令。");
  console.error("   缺少环境变量: MIMO_EVAL_ID, MIMO_SIDE, MIMO_SESSION_ID");
  process.exit(1);
}

const stateFile = `${stateDir}/current.json`;
if (!existsSync(stateFile)) {
  console.error(`❌ 错误：找不到评测状态文件 ${stateFile}`);
  process.exit(1);
}

const state = JSON.parse(readFileSync(stateFile, "utf-8"));

// 代码改动发生在该侧的 worktree 里，而非 skill 安装目录（提交命令会先 cd 到 skill 目录）。
// 所有 git 命令必须显式在 worktree 下执行，否则会跑在 skill 仓库、startCommit 不存在 → 取值全错。
const workdir: string = state.worktrees?.[side] || state.cwd || process.cwd();
// 若回退到了 process.cwd()（提交命令已 cd 到 skill 安装目录），说明 state 缺 worktree/cwd，
// 此时所有 git 采集会跑在 skill 仓库 → 原 bug 静默复发。显式告警而非默默产出错误 diffStat。
if (workdir === process.cwd()) {
  console.warn("⚠️  警告：state 中缺少 worktree/cwd，git 改动统计可能不准确（回退到当前目录）。");
}

// untracked 文件逐个读取数行；超过该上限只计文件数、跳过行数统计，避免病态目录（如未 gitignore 的 node_modules）拖垮提交。
const MAX_UNTRACKED_FILES = 2000;

// 在进程内读取文件数行数：避免起 shell（防命令注入 + 跨平台），并跳过二进制文件。
function countLines(absPath: string): number {
  try {
    const buf = readFileSync(absPath);
    if (buf.includes(0)) return 0; // 含 NUL，视为二进制，不计行数
    const text = buf.toString("utf-8");
    if (text.length === 0) return 0;
    let n = 0;
    for (let i = 0; i < text.length; i++) if (text.charCodeAt(i) === 10) n++;
    if (text[text.length - 1] !== "\n") n++; // 末行无换行也算一行
    return n;
  } catch {
    return 0;
  }
}

function getGitRemoteUrl(): string {
  try {
    return execSync("git remote get-url origin", { cwd: workdir, encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return "";
  }
}

function getGitUsername(): string {
  try {
    return execSync("git config user.name", { cwd: workdir, encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return "";
  }
}

function getHeadCommit(): string {
  try {
    return execSync("git rev-parse HEAD", { cwd: workdir, encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return "";
  }
}

function getGitDiffStat(startCommit: string): { filesChanged: number; insertions: number; deletions: number } {
  let filesChanged = 0;
  let insertions = 0;
  let deletions = 0;

  // 1) 已跟踪文件的改动：用单个 commit（对比工作区，含未提交改动），而非 startCommit..HEAD（commit 到 commit，会漏未提交）。
  //    agent 在 worktree 改文件通常不会 commit，HEAD 仍停在 startCommit，双点 diff 必为 0。
  //    刻意不用 `git add -A`：那会污染用户 worktree 的索引。
  try {
    const ref = startCommit || "HEAD";
    const out = execSync(`git diff --shortstat ${ref}`, { cwd: workdir, encoding: "utf-8", stdio: "pipe" }).trim();
    filesChanged += parseInt(out.match(/(\d+) file/)?.[1] || "0");
    insertions += parseInt(out.match(/(\d+) insertion/)?.[1] || "0");
    deletions += parseInt(out.match(/(\d+) deletion/)?.[1] || "0");
  } catch {
    // 忽略，落到下面的 untracked 统计
  }

  // 2) 新建（untracked）文件：git diff 默认不计入，单独统计文件数与新增行数。
  //    用 -z（NUL 分隔）避免文件名含特殊字符/换行时被 split 拆错或被 quotePath 加引号。
  //    行数统计在进程内做（countLines），不起 shell —— 防命令注入、跨平台、跳过二进制。
  try {
    const out = execSync("git ls-files --others --exclude-standard -z", { cwd: workdir, encoding: "utf-8", stdio: "pipe" });
    const untracked = out ? out.split("\0").filter((l) => l.length > 0) : [];
    filesChanged += untracked.length;
    if (untracked.length <= MAX_UNTRACKED_FILES) {
      for (const f of untracked) {
        insertions += countLines(join(workdir, f));
      }
    }
  } catch {
    // 忽略
  }

  return { filesChanged, insertions, deletions };
}

const diffStat = getGitDiffStat(state.startCommit || "");
const model = state.sessions?.[side]?.model ?? "unknown";
const submitter = getGitUsername();
const repoUrl = getGitRemoteUrl();
const startCommit = state.startCommit || "";
const endCommit = getHeadCommit();

console.log(`\n📤 提交 CLI 评测结果...`);
console.log(`   Eval ID:  ${evalId}`);
console.log(`   Side:     ${side} (${cliType})`);
console.log(`   Model:    ${model || "N/A"}`);
console.log(`   Session:  ${sessionId}`);
console.log(`   提交者:   ${submitter || "未识别"}`);
console.log(`   代码变更: ${diffStat.filesChanged} files, +${diffStat.insertions}/-${diffStat.deletions}`);
console.log(`   仓库:     ${repoUrl || "无"}`);
console.log(`   起点commit: ${startCommit ? startCommit.slice(0, 8) : "无"}`);
console.log(`   终点commit: ${endCommit ? endCommit.slice(0, 8) : "无"}`);

// --- Interactive questionnaire ---
let adoption = "adopted";
let rating = 3;
let outputRating = 3;
let feedback = "";

const envAdoption = process.env.MIMO_ADOPTION?.trim();
const envRating = process.env.MIMO_RATING?.trim();
const envOutputRating = process.env.MIMO_OUTPUT_RATING?.trim();
const envFeedback = process.env.MIMO_FEEDBACK?.trim();

if (envAdoption || envRating) {
  const adoptionMap: Record<string, string> = { "1": "adopted", "2": "partial", "3": "rejected" };
  adoption = adoptionMap[envAdoption || "1"] || "adopted";
  rating = Math.max(1, Math.min(5, parseInt(envRating || "3") || 3));
  outputRating = Math.max(1, Math.min(5, parseInt(envOutputRating || "3") || 3));
  feedback = envFeedback || "";
  console.log(`\n📋 用户反馈: 采用=${adoption}, 体感=${rating}/5, 效果=${outputRating}/5${feedback ? ', 反馈="' + feedback + '"' : ''}\n`);
} else if (process.stdin.isTTY) {
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  const ask = (q: string): Promise<string> => new Promise((resolve) => rl.question(q, resolve));

  console.log(`\n────────────────────────────────────────`);
  console.log(`📋 请回答以下问题（帮助我们了解你的体验）`);
  console.log(`────────────────────────────────────────\n`);

  console.log(`1️⃣  你是否采用了这一侧的代码产出？`);
  console.log(`   [1] ✅ 采用 — 直接使用或基于它继续开发`);
  console.log(`   [2] ⚠️  部分采用 — 参考了思路，但做了较大修改`);
  console.log(`   [3] ❌ 未采用 — 没有使用这一侧的输出`);
  const adoptionInput = await ask(`   请输入 (1/2/3): `);
  const adoptionMapLocal: Record<string, string> = { "1": "adopted", "2": "partial", "3": "rejected" };
  adoption = adoptionMapLocal[adoptionInput.trim()] || "adopted";

  console.log(`\n2️⃣  使用体感打分 (1-5):`);
  console.log(`   交互过程是否流畅、理解力如何、是否需要反复纠正`);
  console.log(`   [1] 😫 很差  [2] 😕 较差  [3] 😐 一般  [4] 🙂 不错  [5] 🤩 完美`);
  const ratingInput = await ask(`   请输入 (1-5): `);
  rating = Math.max(1, Math.min(5, parseInt(ratingInput.trim()) || 3));

  console.log(`\n3️⃣  产出效果打分 (1-5):`);
  console.log(`   最终代码/输出的正确性、完整性、可用性`);
  console.log(`   [1] 😫 很差  [2] 😕 较差  [3] 😐 一般  [4] 🙂 不错  [5] 🤩 完美`);
  const outputRatingInput = await ask(`   请输入 (1-5): `);
  outputRating = Math.max(1, Math.min(5, parseInt(outputRatingInput.trim()) || 3));

  console.log(`\n4️⃣  补充反馈:`);
  feedback = (await ask(`   > `)).trim();

  rl.close();
  console.log(`\n────────────────────────────────────────\n`);
} else {
  console.log(`\n⚡ 非交互模式，使用默认值提交\n`);
}

const payload = {
  evalId,
  evalType: "agent",
  side,
  sessionId,
  model,
  cliType,
  taskId: taskIdEnv || state.taskId || "",
  diffStat,
  submitter,
  submittedAt: Date.now(),
  cwd: state.cwd,
  repoUrl,
  startCommit,
  endCommit,
  adoption,
  rating,
  outputRating,
  feedback,
};

try {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (userKey) {
    headers["Authorization"] = `Bearer ${userKey}`;
  }

  const resp = await fetch(submitURL, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (resp.ok) {
    const data = await resp.json().catch(() => ({}));
    console.log(`✅ 提交成功！(HTTP ${resp.status})`);
    if (data.data?.username) console.log(`   用户: ${data.data.username}`);
    if (data.data?.both_submitted) {
      console.log(`✅ 双端已提交完成，分析已触发`);
    } else {
      console.log(`⏳ 等待对方提交...`);
    }
    console.log(`\n📊 评测详情: http://mimorouter.llmcore.ai.srv/evaluation/agent-submissions`);
  } else {
    const text = await resp.text().catch(() => "");
    console.error(`❌ 提交失败 (HTTP ${resp.status})`);
    console.error(`   URL: ${submitURL}`);
    if (text) console.error(`   响应: ${text.slice(0, 300)}`);
    process.exit(1);
  }
} catch (err: any) {
  console.error(`❌ 提交失败：无法连接服务器`);
  console.error(`   URL: ${submitURL}`);
  console.error(`   错误: ${err.message}`);
  console.log("\n📋 提交数据（可手动重试）：");
  console.log(JSON.stringify(payload, null, 2));
}
