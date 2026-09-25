import { writeFileSync, mkdirSync } from "fs";
import { join } from "path";
import { EVAL_CONFIG } from "../eval-config.js";

export interface TerminalOptions {
  title: string;
  env: Record<string, string>;
  cwd: string;
  command: string;
  postCommand?: string;
}

function getScriptDir(): string {
  const dir = EVAL_CONFIG.stateDir;
  mkdirSync(dir, { recursive: true });
  return dir;
}

export function generateShellScript(opts: TerminalOptions, side: string): string {
  const filePath = join(getScriptDir(), `launch-${side}.sh`);
  const lines = ["#!/bin/zsh -l"];
  for (const [key, value] of Object.entries(opts.env)) {
    lines.push(`export ${key}="${value.replace(/"/g, '\\"')}"`);
  }
  lines.push(`cd "${opts.cwd}"`);
  if (opts.postCommand) {
    lines.push(opts.command);
    lines.push(opts.postCommand);
  } else {
    lines.push(`exec ${opts.command}`);
  }
  writeFileSync(filePath, lines.join("\n") + "\n", { mode: 0o755 });
  return filePath;
}

export function generateBatScript(opts: TerminalOptions, side: string): string {
  const filePath = join(getScriptDir(), `launch-${side}.bat`);
  // chcp 65001 把 cmd 的活动码页切到 UTF-8，让后续行（set / claude 参数）按 UTF-8 解析。
  // 不加这行的话，中文 Windows 下默认 GBK 码页会把 UTF-8 字节误读成 GBK，
  // prompt 里的中文到 claude 时会变乱码（如 "开启子终端" → "寮€鍚瓙缁堢"）。
  // 不加 BOM：部分 cmd.exe 版本会把首行第一个字符吞掉。
  const lines = ["@echo off", "chcp 65001 > nul", `title ${opts.title}`];
  for (const [key, value] of Object.entries(opts.env)) {
    lines.push(`set "${key}=${value}"`);
  }
  lines.push(`cd /d "${opts.cwd}"`);
  if (opts.postCommand) {
    // 主命令正常执行（不用 exec，cmd.exe 没有 exec 语义，执行完后继续下一行）
    lines.push(opts.command);
    // postCommand 来自 Unix 风格脚本，~ 在 cmd.exe 中不展开，需替换为 %USERPROFILE%。
    // 例：cd ~/.claude/skills/... → cd %USERPROFILE%\.claude\skills\...
    // 同时把 Unix 路径分隔符 / 替换为 Windows 的 \，避免部分 cmd 指令解析失败。
    const winPostCmd = opts.postCommand
      .replace(/~\//g, "%USERPROFILE%\\")
      .replace(/^~$/g, "%USERPROFILE%")
      .replace(/\//g, "\\");
    lines.push(winPostCmd);
  } else {
    lines.push(opts.command);
  }
  writeFileSync(filePath, lines.join("\r\n") + "\r\n");
  return filePath;
}
