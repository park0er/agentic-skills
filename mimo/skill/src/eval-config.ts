import path from "path";
import os from "os";
import { readFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 自动加载 .env 文件（手动解析，不引入 dotenv 依赖）
function loadDotEnv(): void {
  const envPath = path.join(__dirname, "..", ".env");
  if (!existsSync(envPath)) return;

  const content = readFileSync(envPath, "utf-8");
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx < 1) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, "");
    if (!(key in process.env)) {
      process.env[key] = val;
    }
  }
}

loadDotEnv();

function env(key: string, fallback: string): string {
  return process.env[key] || fallback;
}

export const EVAL_CONFIG = {
  routerURL: env("MIMO_ROUTER_URL", "http://mimorouter.llmcore.ai.srv/"),
  submitURL: env("MIMO_SUBMIT_URL", "http://mimorouter.llmcore.ai.srv/v1/eval/submit"),
  registerURL: env("MIMO_REGISTER_URL", "http://mimorouter.llmcore.ai.srv/v1/eval/register"),
  stateDir: env("MIMO_STATE_DIR", path.join(os.homedir(), ".mimo-eval")),
};
