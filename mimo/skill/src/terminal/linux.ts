import { execSync } from "child_process";
import { generateShellScript, type TerminalOptions } from "./script.js";

function hasCommand(cmd: string): boolean {
  try {
    execSync(`which ${cmd}`, { stdio: "pipe" });
    return true;
  } catch {
    return false;
  }
}

function isInTmux(): boolean {
  return !!process.env.TMUX;
}

const terminalCandidates = [
  { cmd: "gnome-terminal", build: (script: string) => `gnome-terminal -- bash "${script}"` },
  { cmd: "xfce4-terminal", build: (script: string) => `xfce4-terminal -e "bash \\"${script}\\""` },
  { cmd: "konsole", build: (script: string) => `konsole -e bash "${script}"` },
  { cmd: "xterm", build: (script: string) => `xterm -e bash "${script}"` },
];

function openWithTmux(scriptA: string, scriptB: string, titleA: string, titleB: string): void {
  execSync(`tmux new-window -n "mimo-eval" "bash \\"${scriptA}\\""`, { stdio: "pipe" });
  execSync(`tmux split-window -h "bash \\"${scriptB}\\""`, { stdio: "pipe" });
  execSync(`tmux select-pane -t 0 -T "${titleA}"`, { stdio: "pipe" });
  execSync(`tmux select-pane -t 1 -T "${titleB}"`, { stdio: "pipe" });
}

function openWithNewTmuxSession(scriptA: string, scriptB: string, titleA: string, titleB: string): void {
  execSync(`tmux new-session -d -s "mimo-eval" "bash \\"${scriptA}\\""`, { stdio: "pipe" });
  execSync(`tmux split-window -h -t "mimo-eval" "bash \\"${scriptB}\\""`, { stdio: "pipe" });
  execSync(`tmux select-pane -t "mimo-eval:0.0" -T "${titleA}"`, { stdio: "pipe" });
  execSync(`tmux select-pane -t "mimo-eval:0.1" -T "${titleB}"`, { stdio: "pipe" });
}

function openWithDetectedTerminal(scriptA: string, scriptB: string, titleA: string, titleB: string): void {
  const customTerminal = process.env.TERMINAL;
  if (customTerminal && hasCommand(customTerminal)) {
    try {
      execSync(`${customTerminal} -e bash "${scriptA}"`, { stdio: "pipe" });
      execSync(`${customTerminal} -e bash "${scriptB}"`, { stdio: "pipe" });
      return;
    } catch {}
  }

  // 优先尝试 GUI 终端。即使 $DISPLAY/$WAYLAND_DISPLAY 未导出（如 SSH 会话里跑
  // Claude Code）也尝试启动：无显示时 gnome-terminal 等会自行报错退出，被 catch
  // 捕获后自然 fallback 到 tmux/手动提示，不会卡死。有显示变量时优先匹配。
  const hasDisplay = !!(process.env.DISPLAY || process.env.WAYLAND_DISPLAY);
  for (const candidate of terminalCandidates) {
    if (hasCommand(candidate.cmd)) {
      try {
        execSync(candidate.build(scriptA), { stdio: "pipe" });
        execSync(candidate.build(scriptB), { stdio: "pipe" });
        return;
      } catch {
        // 无显示导致启动失败时继续尝试下一个候选 / fallback tmux
        if (!hasDisplay) break;
      }
    }
  }

  // No GUI terminal, fallback to tmux
  if (hasCommand("tmux")) {
    // Kill existing mimo-eval session if any
    try { execSync('tmux kill-session -t "mimo-eval"', { stdio: "pipe" }); } catch {}
    openWithNewTmuxSession(scriptA, scriptB, titleA, titleB);
    console.log("   📐 已创建 tmux session: mimo-eval");
    console.log("   💡 执行 tmux attach -t mimo-eval 进入评测终端");
    return;
  }

  console.error(`❌ 未找到可用的终端。请安装 tmux，或设置 $TERMINAL 环境变量。`);
  console.error(`   你也可以手动执行:`);
  console.error(`     bash "${scriptA}"`);
  console.error(`     bash "${scriptB}"`);
  process.exit(1);
}

export function openTerminalPairLinux(optsA: TerminalOptions, optsB: TerminalOptions): void {
  const scriptA = generateShellScript(optsA, "A");
  const scriptB = generateShellScript(optsB, "B");

  if (isInTmux()) {
    openWithTmux(scriptA, scriptB, optsA.title, optsB.title);
    console.log("   📐 已在 tmux 中创建左右分栏");
  } else {
    openWithDetectedTerminal(scriptA, scriptB, optsA.title, optsB.title);
  }
}
