import { readFileSync, existsSync, readdirSync, statSync } from "fs";
import { join } from "path";
import { homedir } from "os";
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

if (!evalId || !side || !sessionId) {
  console.error("❌ 错误：当前终端不是评测终端。");
  console.error("   请在通过 /mimo 启动的评测终端中执行此命令。");
  console.error("   缺少环境变量: MIMO_EVAL_ID, MIMO_SIDE, MIMO_SESSION_ID");
  process.exit(1);
}

const stateFile = `${stateDir}/current.json`;
if (!existsSync(stateFile)) {
  console.error(`❌ 错误：找不到评测状态文件 ${stateFile}`);
  process.exit(1);
}

const state = JSON.parse(readFileSync(stateFile, "utf-8"));

function getGitRemoteUrl(): string {
  try {
    return execSync("git remote get-url origin", { encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return "";
  }
}

function getGitUsername(): string {
  try {
    return execSync("git config user.name", { encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return "";
  }
}

function getHeadCommit(): string {
  try {
    return execSync("git rev-parse HEAD", { encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return "";
  }
}

function countTurns(sid: string): number {
  const projectsDir = join(homedir(), ".claude", "projects");
  if (!existsSync(projectsDir)) return 0;

  try {
    const dirs = readdirSync(projectsDir);
    for (const dir of dirs) {
      const sessionFile = join(projectsDir, dir, `${sid}.jsonl`);
      if (existsSync(sessionFile)) {
        const content = readFileSync(sessionFile, "utf-8");
        const lines = content.split("\n").filter((l) => l.trim());
        let turns = 0;
        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            if (
              data.type === "user" ||
              data.message?.role === "user" ||
              data.message?.role === "human"
            ) {
              turns++;
            }
          } catch {
            if (/"role"\s*:\s*"(human|user)"/.test(line)) {
              turns++;
            }
          }
        }
        return turns;
      }
    }
  } catch {}
  return 0;
}

function getContentLength(sid: string): number {
  const projectsDir = join(homedir(), ".claude", "projects");
  if (!existsSync(projectsDir)) return 0;

  try {
    const dirs = readdirSync(projectsDir);
    for (const dir of dirs) {
      const sessionFile = join(projectsDir, dir, `${sid}.jsonl`);
      if (existsSync(sessionFile)) {
        return statSync(sessionFile).size;
      }
    }
  } catch {}
  return 0;
}

const turnCount = countTurns(sessionId);
const contentLength = getContentLength(sessionId);
const model = state.sessions?.[side]?.model ?? "unknown";
const submitter = getGitUsername();
const repoUrl = getGitRemoteUrl();
const startCommit = state.startCommit || "";
const endCommit = getHeadCommit();

console.log(`\n📤 提交评测结果...`);
console.log(`   Eval ID:  ${evalId}`);
console.log(`   Side:     ${side} (${model})`);
console.log(`   Session:  ${sessionId}`);
console.log(`   提交者:   ${submitter || "未识别"}`);
console.log(`   对话轮次: ${turnCount || "未知"}`);
console.log(`   内容长度: ${contentLength ? (contentLength / 1024).toFixed(1) + ' KB' : "未知"}`);
console.log(`   仓库:     ${repoUrl || "无"}`);
console.log(`   起点commit: ${startCommit ? startCommit.slice(0, 8) : "无"}`);
console.log(`   终点commit: ${endCommit ? endCommit.slice(0, 8) : "无"}`);

// --- Interactive questionnaire (skip if non-TTY, e.g. run by Claude) ---
let adoption = "adopted";
let rating = 3;
let outputRating = 3;
let feedback = "";

// Check env vars first (passed by Claude via SKILL.md)
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
  side,
  sessionId,
  model,
  taskId: taskIdEnv || state.taskId || "",
  turnCount,
  contentLength,
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
    console.log(`\n📊 评测详情: http://mimorouter.llmcore.ai.srv/evaluation/model-submissions`);
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
