import { spawn, type ChildProcess } from "child_process";
import { EventEmitter } from "events";

export interface ClaudeProcessOptions {
  workdir: string;
  model: string;
  apiKey: string;
  baseURL: string;
  sessionId?: string;
  skipPermissions?: boolean;
}

export class ClaudeProcess extends EventEmitter {
  private proc: ChildProcess | null = null;
  private buffer = "";
  private _ready = false;

  get ready() {
    return this._ready;
  }

  spawn(opts: ClaudeProcessOptions): void {
    const args = [
      "-p",
      "--bare",
      "--verbose",
      "--input-format", "stream-json",
      "--output-format", "stream-json",
      "--model", opts.model,
      "--name", `eval-${opts.sessionId?.slice(0, 8) || "unknown"}`,
    ];

    if (opts.sessionId) {
      args.push("--session-id", opts.sessionId);
    }
    if (opts.skipPermissions) {
      args.push("--dangerously-skip-permissions");
    }

    const env: Record<string, string> = {
      ...process.env as Record<string, string>,
      ANTHROPIC_BASE_URL: opts.baseURL,
      ANTHROPIC_API_KEY: opts.apiKey,
    };
    delete env.ANTHROPIC_AUTH_TOKEN;

    this.proc = spawn("claude", args, {
      cwd: opts.workdir,
      env,
      stdio: ["pipe", "pipe", "pipe"],
    });

    this.proc.stdout?.on("data", (data: Buffer) => {
      this.buffer += data.toString();
      const lines = this.buffer.split("\n");
      this.buffer = lines.pop() || "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const event = JSON.parse(trimmed);
          this.emit("event", event);
        } catch {
          // skip non-JSON lines
        }
      }
    });

    // Mark ready on next tick (so listeners set up after spawn() can catch this event)
    process.nextTick(() => {
      this._ready = true;
      this.emit("ready");
    });

    this.proc.stderr?.on("data", (data: Buffer) => {
      this.emit("stderr", data.toString());
    });

    this.proc.on("close", (code) => {
      this._ready = false;
      this.emit("close", code);
    });

    this.proc.on("error", (err) => {
      this.emit("error", err);
    });
  }

  sendMessage(text: string): void {
    if (!this.proc?.stdin || this.proc.stdin.destroyed) {
      this.emit("error", new Error("Process not running"));
      return;
    }
    const msg = JSON.stringify({
      type: "user",
      message: { role: "user", content: text },
    });
    this.proc.stdin.write(msg + "\n");
  }

  kill(): void {
    if (this.proc) {
      this.proc.stdin?.end();
      this.proc.kill("SIGTERM");
      this.proc = null;
      this._ready = false;
    }
  }

  get pid(): number | undefined {
    return this.proc?.pid;
  }
}
