import { createServer, type IncomingMessage, type ServerResponse } from "http";
import { mkdirSync, writeFileSync, readFileSync, existsSync } from "fs";
import { createInterface } from "readline";
import { execSync } from "child_process";
import { join } from "path";
import { EVAL_CONFIG } from "./eval-config.js";

const { stateDir, routerURL } = EVAL_CONFIG;
const CONFIG_FILE = join(stateDir, "config.json");
const LOGIN_BASE_URL = routerURL;

export function loadKey(): string {
  if (process.env.MIMO_INLINE_KEY) return process.env.MIMO_INLINE_KEY;
  if (process.env.MIMO_ROUTER_KEY) return process.env.MIMO_ROUTER_KEY;
  if (existsSync(CONFIG_FILE)) {
    try {
      const c = JSON.parse(readFileSync(CONFIG_FILE, "utf-8"));
      if (c.key) return c.key;
    } catch {}
  }
  if (/mimorouter/i.test(process.env.ANTHROPIC_BASE_URL || "") && process.env.ANTHROPIC_API_KEY) {
    return process.env.ANTHROPIC_API_KEY;
  }
  return "";
}

export function saveKey(key: string): void {
  mkdirSync(stateDir, { recursive: true });
  let config: Record<string, unknown> = {};
  if (existsSync(CONFIG_FILE)) {
    try { config = JSON.parse(readFileSync(CONFIG_FILE, "utf-8")); } catch {}
  }
  config.key = key;
  writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
}

/**
 * 完整登录流程：
 * 1. 启动本地 HTTP Server (随机端口)
 * 2. 打开浏览器到 mimorouter /login-for-cli 页面
 * 3. Race: 浏览器回调 vs 用户手动粘贴 key
 * 4. 保存 key 到本地配置
 */
export async function login(): Promise<string> {
  console.log("\n🔐 需要登录 mimorouter 获取 API Key\n");

  // Start local server
  const server = createServer();
  await new Promise<void>((resolve, reject) => {
    server.listen(0, () => resolve());
    server.on("error", reject);
  });
  const addr = server.address();
  const port = typeof addr === "object" && addr ? addr.port : 0;

  const redirectUri = `http://localhost:${port}/callback`;
  const loginUrl = `${LOGIN_BASE_URL}login-for-cli?redirect_uri=${encodeURIComponent(redirectUri)}`;

  // Open browser
  openBrowser(loginUrl);

  console.log("   浏览器已打开，请在 mimorouter 中登录并授权。\n");
  console.log(`   如浏览器未打开，手动访问：`);
  console.log(`   ${loginUrl}\n`);
  console.log("   ─── 或者直接粘贴你的 API Key (sk-开头) ───\n");

  // Race: browser callback vs stdin paste
  let key = "";
  try {
    key = await Promise.race([
      waitForCallback(server, port),
      waitForStdinPaste(),
    ]);
  } catch (err: any) {
    console.error(`\n❌ ${err.message || "登录失败"}`);
  }

  server.close();

  if (!key) {
    console.error("❌ 登录失败：未获取到有效 key");
    process.exit(1);
  }

  saveKey(key);
  console.log(`\n✅ 登录成功！Key 已保存到 ${CONFIG_FILE}`);
  console.log(`   后续无需重复登录。\n`);

  return key;
}

function waitForCallback(server: ReturnType<typeof createServer>, port: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      server.close();
      reject(new Error("登录超时（5分钟）"));
    }, 5 * 60 * 1000);

    server.on("request", (req: IncomingMessage, res: ServerResponse) => {
      const url = new URL(req.url || "/", `http://localhost:${port}`);

      if (url.pathname === "/callback") {
        const key = url.searchParams.get("key") || "";

        if (key && key.startsWith("sk-")) {
          res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
          res.end(`
            <html><body style="font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;background:#1a1a2e;color:#e0e0e0;">
              <div style="text-align:center;">
                <h1 style="color:#51cf66;">✅ 授权成功</h1>
                <p>可以关闭此页面，回到终端继续操作。</p>
              </div>
            </body></html>
          `);
          clearTimeout(timeout);
          resolve(key);
        } else {
          res.writeHead(400, { "Content-Type": "text/html; charset=utf-8" });
          res.end(`
            <html><body style="font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;background:#1a1a2e;color:#e0e0e0;">
              <div style="text-align:center;">
                <h1 style="color:#ff6b6b;">❌ 授权失败</h1>
                <p>未收到有效的 API Key，请重试。</p>
              </div>
            </body></html>
          `);
        }
      } else {
        res.writeHead(404);
        res.end("Not Found");
      }
    });
  });
}

function waitForStdinPaste(): Promise<string> {
  return new Promise((resolve) => {
    if (!process.stdin.isTTY) {
      return; // Never resolves in non-TTY, let callback win
    }

    const rl = createInterface({ input: process.stdin, output: process.stdout });

    const askForKey = () => {
      rl.question("   > ", (answer) => {
        const key = answer.trim();
        if (key.startsWith("sk-") && key.length > 10) {
          rl.close();
          resolve(key);
        } else if (key) {
          console.log("   ⚠️ 无效 key（需以 sk- 开头），请重新输入：");
          askForKey();
        } else {
          // Empty input, keep waiting
          askForKey();
        }
      });
    };
    askForKey();
  });
}

function openBrowser(url: string): void {
  try {
    const cmd = process.platform === "darwin"
      ? `open "${url}"`
      : process.platform === "win32"
        ? `start "" "${url}"`
        : `xdg-open "${url}"`;
    execSync(cmd, { stdio: "pipe" });
  } catch {
    // Browser open failed, user will use manual URL
  }
}
