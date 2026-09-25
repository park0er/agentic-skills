import { execSync } from "child_process";
import { existsSync, lstatSync } from "fs";
import { dirname, join } from "path";
import { generateBatScript, type TerminalOptions } from "./script.js";

// 路径是否可达。注意：不能用 existsSync。
// Windows Terminal 经 Microsoft Store 安装时，wt.exe 是「应用执行别名」
// （App Execution Alias），本质是指向 Program Files\WindowsApps 的符号链接 /
// reparse point。existsSync 会跟随链接去 stat 目标，而目标 ACL 锁定会抛
// EACCES，于是把真实存在的别名误判为「不存在」。lstatSync 不跟随链接，
// 只判断别名本身是否存在，才是正确做法。
function pathReachable(p: string): boolean {
  try {
    lstatSync(p);
    return true;
  } catch {
    return false;
  }
}

// 查找 wt（Windows Terminal）的可执行路径。
// 关键：必须返回「全路径」而非 boolean。因为 wt 的执行别名只在交互式
// shell / 资源管理器中生效，对 execSync 拉起的 cmd.exe 子进程不可见
// （`cmd /c "wt ..."` 会报 'wt' is not recognized）。只有用全路径才能在
// 子进程里稳定拉起。
function findWt(): string | null {
  // 1) where 能找到就直接用（PATH 中有真实 wt 的少数情况）
  try {
    const out = execSync("where wt", { encoding: "utf-8", stdio: "pipe" });
    const first = out.split(/\r?\n/).map((l) => l.trim()).find(Boolean);
    if (first && pathReachable(first)) return first;
  } catch {}

  // 2) 硬路径探测：WindowsApps 下的执行别名 + 各版本安装目录
  const winAppsDir = join(process.env.LOCALAPPDATA || "", "Microsoft", "WindowsApps");
  const candidates = [join(winAppsDir, "wt.exe")];
  try {
    if (pathReachable(winAppsDir)) {
      const entries = execSync(`dir /b "${winAppsDir}"`, { encoding: "utf-8", stdio: "pipe" });
      for (const entry of entries.split(/\r?\n/)) {
        if (entry.startsWith("Microsoft.WindowsTerminal")) {
          candidates.push(join(winAppsDir, entry, "wt.exe"));
        }
      }
    }
  } catch {}
  for (const p of candidates) {
    if (pathReachable(p)) return p;
  }
  return null;
}

function findGitBash(): string | null {
  const fromEnv = process.env.CLAUDE_CODE_GIT_BASH_PATH;
  if (fromEnv && existsSync(fromEnv)) return fromEnv;
  try {
    const lines = execSync("where git", { stdio: ["ignore", "pipe", "ignore"] }).toString().split(/\r?\n/);
    for (const line of lines) {
      let dir = line.trim();
      if (!dir) continue;
      dir = dirname(dir);
      for (let i = 0; i < 3; i++) {
        for (const c of [join(dir, "bin", "bash.exe"), join(dir, "usr", "bin", "bash.exe")]) {
          if (existsSync(c)) return c;
        }
        const parent = dirname(dir);
        if (parent === dir) break;
        dir = parent;
      }
    }
  } catch {}
  return null;
}

function ensureGitBash(opts: TerminalOptions): void {
  if (!opts.env.CLAUDE_CODE_GIT_BASH_PATH) {
    const bash = findGitBash();
    if (bash) opts.env.CLAUDE_CODE_GIT_BASH_PATH = bash;
  }
}

export function openTerminalPairWin32(optsA: TerminalOptions, optsB: TerminalOptions): void {
  ensureGitBash(optsA);
  ensureGitBash(optsB);

  const scriptA = generateBatScript(optsA, "A");
  const scriptB = generateBatScript(optsB, "B");

  const wtPath = findWt();
  if (wtPath) {
    // 用全路径调用 wt，绕过执行别名在子进程中不可见的问题。
    // 全路径含空格，需用引号包裹。
    const wt = `"${wtPath}"`;
    // 用单次 wt 调用 + `;` 子命令分隔符，把 new-tab 和 split-pane 原子化执行，
    // 避免两次 execSync 之间的焦点竞态导致分栏失败。
    // -w mimo-eval：使用（或创建）名为 mimo-eval 的 wt 窗口，避免污染 Claude
    // Code 自己的 wt 窗口（如果在 wt 中运行 Claude Code）。
    try {
      const cmd =
        `${wt} -w mimo-eval nt --title "${optsA.title}" cmd /k "${scriptA}"` +
        ` ; sp -V --title "${optsB.title}" cmd /k "${scriptB}"`;
      execSync(cmd, { stdio: "pipe", shell: "cmd.exe" });
      console.log("   📐 已在 Windows Terminal 中创建左右分栏");
      return;
    } catch (e: any) {
      // wt 分栏失败（如 ; 分隔符被 cmd.exe 误解析），尝试分别在同名窗口中打开两个 tab
      try {
        execSync(
          `${wt} -w mimo-eval nt --title "${optsA.title}" cmd /k "${scriptA}"`,
          { stdio: "pipe", shell: "cmd.exe" },
        );
        execSync(
          `${wt} -w mimo-eval sp -V --title "${optsB.title}" cmd /k "${scriptB}"`,
          { stdio: "pipe", shell: "cmd.exe" },
        );
        console.log("   📐 已在 Windows Terminal 中创建两个分栏（分步模式）");
        return;
      } catch {
        console.warn("   ⚠️ Windows Terminal 打开失败，回退到 cmd 窗口");
      }
    }
  }

  // 最终 fallback：用 PowerShell 打开两个独立窗口，尽量让它们不重叠
  const psScript =
    `Start-Process cmd -ArgumentList '/k', '"${scriptA}"' -WindowStyle Normal; ` +
    `Start-Sleep -Milliseconds 200; ` +
    `Start-Process cmd -ArgumentList '/k', '"${scriptB}"' -WindowStyle Normal`;
  try {
    execSync(`powershell -NoProfile -Command "${psScript.replace(/"/g, '\\"')}"`, {
      stdio: "pipe",
      shell: "cmd.exe",
    });
  } catch {
    // 最终 fallback：纯 cmd start
    execSync(`start "${optsA.title}" cmd /k "${scriptA}"`, { stdio: "pipe", shell: "cmd.exe" });
    execSync(`start "${optsB.title}" cmd /k "${scriptB}"`, { stdio: "pipe", shell: "cmd.exe" });
  }
}
