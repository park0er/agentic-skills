import { openTerminalPairDarwin } from "./darwin.js";
import { openTerminalPairWin32 } from "./win32.js";
import { openTerminalPairLinux } from "./linux.js";
import type { TerminalOptions } from "./script.js";

export type { TerminalOptions };

export function openTerminalPair(
  optsA: TerminalOptions,
  optsB: TerminalOptions,
): void {
  switch (process.platform) {
    case "darwin":
      openTerminalPairDarwin(optsA, optsB);
      break;
    case "win32":
      openTerminalPairWin32(optsA, optsB);
      break;
    case "linux":
      openTerminalPairLinux(optsA, optsB);
      break;
    default:
      console.error(`❌ 不支持的平台: ${process.platform}`);
      process.exit(1);
  }
}
