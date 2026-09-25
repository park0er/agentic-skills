import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SKILL_DIR = join(__dirname, "..");
const SKILL_ROOT = join(SKILL_DIR, "..");
const VERSION_FILE = join(SKILL_ROOT, ".version");
const LAST_CHECK_FILE = join(SKILL_ROOT, ".last-check");
const CHECK_INTERVAL_MS = 0; // TODO: 测试完恢复为 24 * 60 * 60 * 1000
const SERVER = process.env.MIMO_SKILL_SERVER || "http://10.58.101.69";

export async function checkUpdate(): Promise<boolean> {
  try {
    if (existsSync(LAST_CHECK_FILE)) {
      const lastCheck = Number(readFileSync(LAST_CHECK_FILE, "utf-8").trim());
      if (Date.now() - lastCheck < CHECK_INTERVAL_MS) return false;
    }

    writeFileSync(LAST_CHECK_FILE, String(Date.now()));

    const resp = await fetch(`${SERVER}/skill/manifest`, { signal: AbortSignal.timeout(5000) });
    if (!resp.ok) return false;

    const { version, files } = await resp.json() as { version: string; files: Record<string, string> };

    const localVersion = existsSync(VERSION_FILE)
      ? readFileSync(VERSION_FILE, "utf-8").trim()
      : "";

    if (version === localVersion) return false;

    console.log("🔄 检测到 skill 新版本，正在更新...");

    for (const [filePath, content] of Object.entries(files)) {
      const dest = join(SKILL_ROOT, filePath);
      mkdirSync(dirname(dest), { recursive: true });
      writeFileSync(dest, content);
    }

    writeFileSync(VERSION_FILE, version);
    console.log("✅ skill 已更新到最新版本");
    return true;
  } catch {
    return false;
  }
}
