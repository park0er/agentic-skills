import { createInterface } from "readline";
import { writeFileSync, mkdirSync, existsSync, readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import os from "os";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ENV_PATH = join(__dirname, "..", ".env");
const STATE_DIR = join(os.homedir(), ".mimo-eval");
const CONFIG_PATH = join(STATE_DIR, "config.json");

const rl = createInterface({ input: process.stdin, output: process.stdout });

function ask(question: string, defaultVal: string = ""): Promise<string> {
  const hint = defaultVal ? ` (${defaultVal})` : "";
  return new Promise((resolve) => {
    rl.question(`${question}${hint}: `, (answer) => {
      resolve(answer.trim() || defaultVal);
    });
  });
}

async function main() {
  console.log("=== MiMo 评测 Skill 配置向导 ===\n");

  // 读取现有配置作为默认值
  let existingKey = "";
  let existingRouterURL = "";
  let existingSubmitURL = "";

  if (existsSync(CONFIG_PATH)) {
    try {
      const c = JSON.parse(readFileSync(CONFIG_PATH, "utf-8"));
      existingKey = c.key || "";
    } catch {}
  }

  // 读取 .env 作为默认值
  let existingEnv: Record<string, string> = {};
  if (existsSync(ENV_PATH)) {
    for (const line of readFileSync(ENV_PATH, "utf-8").split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eqIdx = trimmed.indexOf("=");
      if (eqIdx < 1) continue;
      existingEnv[trimmed.slice(0, eqIdx).trim()] = trimmed.slice(eqIdx + 1).trim();
    }
  }

  existingRouterURL = existingEnv.MIMO_ROUTER_URL || "";
  existingSubmitURL = existingEnv.MIMO_SUBMIT_URL || "";

  console.log("获取 key：");
  console.log("  1. 浏览器访问 http://mimorouter.llmcore.ai.srv/ 登录");
  console.log("  2. 进入「Token」页面新建 token（sk- 开头）\n");

  const apiKey = await ask("MiMo Router API Key", existingKey);
  const routerURL = await ask("Router URL", existingRouterURL || "http://mimorouter.llmcore.ai.srv/");
  const submitURL = await ask("Submit URL", existingSubmitURL || "http://mimorouter.llmcore.ai.srv/v1/eval/submit");

  // 保存到 ~/.mimo-eval/config.json（start.ts 读取用）
  mkdirSync(STATE_DIR, { recursive: true });
  writeFileSync(CONFIG_PATH, JSON.stringify({ key: apiKey }, null, 2));
  console.log(`\n已保存 key 到 ${CONFIG_PATH}`);

  // 保存到 .env（eval-config.ts 读取用）
  const lines = [
    "# MiMo 评测 Skill 配置 — 由 `npm run setup` 生成",
    "",
    `MIMO_ROUTER_URL=${routerURL}`,
    `MIMO_SUBMIT_URL=${submitURL}`,
    "",
  ];
  writeFileSync(ENV_PATH, lines.join("\n"), "utf-8");
  console.log(`已保存配置到 ${ENV_PATH}`);

  console.log("\n配置完成！使用方式：");
  console.log("  /mimo <任务描述>    — 启动 AB 评测");
  console.log("  /mimo submit        — 提交评测结果");

  rl.close();
}

main().catch(console.error);
