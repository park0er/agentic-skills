import { execSync } from "child_process";
import { generateShellScript, type TerminalOptions } from "./script.js";

function isInTmux(): boolean {
  return !!process.env.TMUX;
}

function detectTerminal(): "iterm2" | "tmux" | "terminal-app" {
  if (isInTmux()) return "tmux";
  if (process.env.TERM_PROGRAM === "iTerm.app") return "iterm2";
  return "terminal-app";
}

function openWithTmux(scriptA: string, scriptB: string, titleA: string, titleB: string): void {
  execSync(
    `tmux new-window -n "mimo-eval" "\\"${scriptA}\\""`,
    { stdio: "pipe" },
  );
  execSync(
    `tmux split-window -h "\\"${scriptB}\\""`,
    { stdio: "pipe" },
  );
  execSync(`tmux select-pane -t 0 -T "${titleA}"`, { stdio: "pipe" });
  execSync(`tmux select-pane -t 1 -T "${titleB}"`, { stdio: "pipe" });
}

function openWithITerm2(scriptA: string, scriptB: string): void {
  const appleScript = `
    tell application "iTerm2"
      activate
      delay 0.3
      set newWindow to (create window with default profile)
      delay 0.5
      tell current session of current tab of newWindow
        write text "\\"${scriptA}\\""
      end tell
      tell current session of current tab of newWindow
        split vertically with default profile
      end tell
      delay 0.5
      tell second session of current tab of newWindow
        write text "\\"${scriptB}\\""
      end tell
    end tell
  `;
  execSync(`osascript -e '${appleScript.replace(/'/g, "'\\''")}'`);
}

function openWithTerminalApp(scriptA: string, scriptB: string): void {
  const scriptForSide = (scriptPath: string) => `
    tell application "Terminal"
      activate
      do script "\\"${scriptPath}\\""
    end tell
  `;
  execSync(`osascript -e '${scriptForSide(scriptA).replace(/'/g, "'\\''")}'`);
  execSync(`osascript -e '${scriptForSide(scriptB).replace(/'/g, "'\\''")}'`);
}

export function openTerminalPairDarwin(optsA: TerminalOptions, optsB: TerminalOptions): void {
  const scriptA = generateShellScript(optsA, "A");
  const scriptB = generateShellScript(optsB, "B");
  const terminal = detectTerminal();

  switch (terminal) {
    case "tmux":
      openWithTmux(scriptA, scriptB, optsA.title, optsB.title);
      console.log("   📐 已在 tmux 中创建左右分栏");
      break;
    case "iterm2":
      openWithITerm2(scriptA, scriptB);
      console.log("   📐 已在 iTerm2 中创建左右分栏");
      break;
    case "terminal-app":
      openWithTerminalApp(scriptA, scriptB);
      break;
  }
}
