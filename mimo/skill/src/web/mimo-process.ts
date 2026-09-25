import { spawn, execSync, type ChildProcess } from "child_process";
import { EventEmitter } from "events";

export interface MimoProcessOptions {
  workdir: string;
  port: number;
  password?: string;
}

export class MimoProcess extends EventEmitter {
  private proc: ChildProcess | null = null;
  private _ready = false;
  private _port: number;
  private _workdir = "";
  private _sessionId = "";
  private _password: string;
  private _sseAbort: AbortController | null = null;
  // Track tool parts by callID so we can emit tool_use + tool_result correctly
  private _toolParts: Map<string, { emitted: boolean; inputEmitted: boolean }> = new Map();
  // 串行化发送队列:mimo serve 每个 session 同一时刻只能处理一轮,
  // 并发 POST /message 会 409 busy。参考 Claude Code stdin 天然串行的语义,
  // 在本侧维护队列,一轮 POST 完成后再发下一条(协议不同,不照抄实现)。
  private _queue: string[] = [];
  private _draining = false;

  constructor() {
    super();
    this._port = 0;
    this._password = "";
  }

  get ready() {
    return this._ready;
  }

  get sessionId() {
    return this._sessionId;
  }

  async spawn(opts: MimoProcessOptions): Promise<void> {
    this._port = opts.port;
    this._password = opts.password || "";
    this._workdir = opts.workdir;

    // Kill any existing process on the port
    try {
      if (process.platform === "win32") {
        const out = execSync(`netstat -ano | findstr :${opts.port}`, { encoding: "utf-8", stdio: "pipe" }).trim();
        const pids = [...new Set(out.split("\n").map(l => l.trim().split(/\s+/).pop()).filter(Boolean))];
        for (const pid of pids) { try { execSync(`taskkill /F /PID ${pid}`, { stdio: "pipe" }); } catch {} }
      } else {
        const pids = execSync(`lsof -ti :${opts.port}`, { encoding: "utf-8", stdio: "pipe" }).trim();
        if (pids) execSync(`kill -9 ${pids.split("\n").join(" ")}`, { stdio: "pipe" });
      }
      await new Promise((r) => setTimeout(r, 1000));
    } catch {}

    const args = ["serve", "--port", String(opts.port)];

    const env: Record<string, string> = {
      ...process.env as Record<string, string>,
    };
    if (opts.password) {
      env.MIMOCODE_SERVER_PASSWORD = opts.password;
    }

    this.proc = spawn("mimo", args, {
      cwd: opts.workdir,
      env,
      stdio: ["pipe", "pipe", "pipe"],
      shell: true,
    });

    this.proc.on("close", (code) => {
      this._ready = false;
      this.emit("close", code);
    });

    this.proc.on("error", (err) => {
      this.emit("error", err);
    });

    // Wait for "listening on" message in stdout/stderr
    await this.waitForListening();
  }

  private waitForListening(timeout = 30000): Promise<void> {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(`mimo serve did not become ready within ${timeout}ms`));
      }, timeout);

      const check = (data: Buffer) => {
        const text = data.toString();
        this.emit("stderr", text);
        if (text.includes("listening on")) {
          clearTimeout(timer);
          this._ready = true;
          this.emit("ready");
          resolve();
        }
      };

      this.proc?.stdout?.on("data", check);
      this.proc?.stderr?.on("data", check);
    });
  }

  private authHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "x-opencode-directory": this._workdir,
    };
    if (this._password) {
      headers["Authorization"] = `Basic ${Buffer.from(`mimocode:${this._password}`).toString("base64")}`;
    }
    return headers;
  }

  async createSession(): Promise<string> {
    const resp = await fetch(`http://localhost:${this._port}/session`, {
      method: "POST",
      headers: this.authHeaders(),
      body: JSON.stringify({}),
    });
    if (!resp.ok) {
      throw new Error(`Failed to create session: ${resp.status} ${await resp.text()}`);
    }
    const data = await resp.json() as any;
    this._sessionId = data.id || data.sessionID || "";
    // Start listening to mimo's SSE event stream for real-time tool/thinking
    this.startEventListener();
    return this._sessionId;
  }

  // Subscribe to mimo's /event SSE stream.
  // The POST /message response only contains the final text — tool calls, reasoning,
  // and streaming text deltas are pushed via SSE as message.part.updated / message.part.delta.
  private startEventListener(): void {
    this._sseAbort = new AbortController();
    const url = `http://localhost:${this._port}/event`;
    const headers = this.authHeaders();
    delete headers["Content-Type"]; // GET, not POST

    fetch(url, { headers, signal: this._sseAbort.signal })
      .then(async (resp) => {
        if (!resp.ok || !resp.body) {
          this.emit("stderr", `[mimo-sse] failed to connect: ${resp.status}\n`);
          return;
        }
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith("data:")) continue;
            try {
              const data = JSON.parse(trimmed.slice(5));
              this.handleSSEEvent(data);
            } catch {}
          }
        }
      })
      .catch((err: any) => {
        if (err.name !== "AbortError") {
          this.emit("stderr", `[mimo-sse] error: ${err.message}\n`);
        }
      });
  }

  // Translate mimo SSE events into Claude stream-json events for the web UI
  private handleSSEEvent(data: any): void {
    const t = data.type;
    const props = data.properties || {};
    const part = props.part || {};

    // Only process events for our session
    if (props.sessionID && props.sessionID !== this._sessionId) return;

    if (t === "message.part.updated") {
      if (part.type === "tool") {
        const callID = part.callID || part.id;
        const state = part.state || {};
        const tracked = this._toolParts.get(callID);

        if (!tracked) {
          // First time seeing this tool — only emit if we have actual input (skip "pending" with empty input)
          const hasInput = state.input && Object.keys(state.input).length > 0;
          if (hasInput) {
            this._toolParts.set(callID, { emitted: true, inputEmitted: true });
            this.emit("event", {
              type: "assistant",
              message: {
                role: "assistant",
                content: [{
                  type: "tool_use",
                  id: callID,
                  name: part.tool || "tool",
                  input: state.input,
                }],
              },
            });
          } else {
            // Pending state with no input yet — track but don't emit
            this._toolParts.set(callID, { emitted: false, inputEmitted: false });
          }
        } else if (!tracked.emitted && state.input && Object.keys(state.input).length > 0) {
          // We were waiting for input — now emit
          tracked.emitted = true;
          tracked.inputEmitted = true;
          this.emit("event", {
            type: "assistant",
            message: {
              role: "assistant",
              content: [{
                type: "tool_use",
                id: callID,
                name: part.tool || "tool",
                input: state.input,
              }],
            },
          });
        }

        // When completed/error, emit tool_result
        if (state.status === "completed" || state.status === "error") {
          const output = state.output ?? state.error ?? "";
          const displayContent = typeof output === "string" ? output : JSON.stringify(output);
          this.emit("event", {
            type: "user",
            message: {
              role: "user",
              content: [{
                type: "tool_result",
                tool_use_id: callID,
                content: displayContent,
                is_error: state.status === "error",
              }],
            },
          });
          this._toolParts.delete(callID);
        }
      } else if (part.type === "reasoning" && part.text && part.text.trim()) {
        this.emit("event", {
          type: "assistant",
          message: { role: "assistant", content: [{ type: "thinking", thinking: part.text }] },
        });
      }
      // Skip text parts from message.part.updated — they come via message.part.delta
      // (this also filters out the user's own message text being echoed back)
    } else if (t === "message.part.delta") {
      // Streaming text/reasoning delta
      if (props.field === "text" && props.delta) {
        this._streamingParts.add(props.partID);
        this.emit("event", {
          type: "assistant",
          message: { role: "assistant", content: [{ type: "text", text: props.delta }] },
        });
      } else if (props.field === "reasoning" && props.delta && props.delta.trim()) {
        this.emit("event", {
          type: "assistant",
          message: { role: "assistant", content: [{ type: "thinking", thinking: props.delta }] },
        });
      }
    }
  }

  // Track which partIDs are being streamed via delta (to avoid duplicate emission from updated)
  private _streamingParts: Set<string> = new Set();

  // 入队并触发串行发送。调用方无需等待整轮完成(turn 在后台串行执行)。
  async sendMessage(text: string): Promise<void> {
    if (!this._sessionId) {
      this.emit("error", new Error("No session created"));
      return;
    }
    this._queue.push(text);
    this.drain();
  }

  private async drain(): Promise<void> {
    if (this._draining) return;
    this._draining = true;
    try {
      while (this._queue.length > 0) {
        const text = this._queue.shift() as string;
        await this.sendOne(text);
      }
    } finally {
      this._draining = false;
    }
  }

  // 发送单条消息并阻塞到该轮结束。POST /message 期间 SSE 流推送 tool/thinking/text。
  // 若遇 409 busy(上一轮僵死/外部占用),先 abort 解锁再重试一次,自愈卡死 session。
  private async sendOne(text: string, retried = false): Promise<void> {
    // Reset streaming state for this turn
    this._toolParts.clear();
    this._streamingParts.clear();

    try {
      const resp = await fetch(`http://localhost:${this._port}/session/${this._sessionId}/message`, {
        method: "POST",
        headers: this.authHeaders(),
        body: JSON.stringify({
          parts: [{ type: "text", text: text }],
        }),
      });

      if (resp.status === 409 && !retried) {
        // Session busy(上一轮僵死或被占用)→ 主动 abort 解锁,稍后重试一次
        this.emit("stderr", "[mimo] session busy, aborting stuck turn and retrying...\n");
        await this.abort();
        await new Promise((r) => setTimeout(r, 1500));
        return this.sendOne(text, true);
      }

      if (!resp.ok) {
        const errText = await resp.text();
        this.emit("event", { type: "error", message: `HTTP ${resp.status}: ${errText}` });
        return;
      }

      // POST 完成 = 本轮结束;tool/thinking/text 已由 SSE 实时 emit,不解析 body 避免重复
      this.emit("event", { type: "result", subtype: "success" });
    } catch (err: any) {
      this.emit("event", { type: "error", message: err.message });
    }
  }

  // 取消当前正在进行的轮次(opencode: POST /session/:id/abort),释放 busy 锁。
  async abort(): Promise<void> {
    if (!this._sessionId) return;
    try {
      await fetch(`http://localhost:${this._port}/session/${this._sessionId}/abort`, {
        method: "POST",
        headers: this.authHeaders(),
      });
    } catch (err: any) {
      this.emit("stderr", `[mimo] abort failed: ${err.message}\n`);
    }
  }

  // Transform mimo (opencode) response into Claude stream-json events the web UI
  // understands. The frontend iterates message.content as an ARRAY of typed blocks
  // ({type:"text"|"thinking"|"tool_use"} / tool_result), so we must emit blocks,
  // not a joined string — otherwise nothing renders for the MiMo Code side.
  private emitMimoEvents(event: any): void {
    // Full response format: {info: {...}, parts: [...]}
    if (event && event.info && Array.isArray(event.parts)) {
      // Skip echoing the user's own message back as an assistant bubble
      if (event.info.role === "user") return;

      const assistantBlocks: any[] = [];
      const toolResults: any[] = [];

      for (const p of event.parts) {
        if (!p || typeof p !== "object") continue;
        if (p.type === "text") {
          const text = p.text ?? p.content ?? "";
          if (text) assistantBlocks.push({ type: "text", text });
        } else if (p.type === "reasoning") {
          const text = p.text ?? p.content ?? "";
          if (text) assistantBlocks.push({ type: "thinking", thinking: text });
        } else if (p.type === "tool") {
          // opencode tool part: { type:"tool", tool, callID, state:{ input/output, status } }
          const id = p.callID || p.id;
          const state = p.state || {};
          assistantBlocks.push({
            type: "tool_use",
            id,
            name: p.tool || state.title || "tool",
            input: state.input || p.input || {},
          });
          if (state.status === "completed" || state.status === "error" || state.output !== undefined) {
            toolResults.push({
              type: "tool_result",
              tool_use_id: id,
              content: typeof state.output === "string" ? state.output : JSON.stringify(state.output ?? state.error ?? ""),
              is_error: state.status === "error",
            });
          }
        }
        // step-start / step-finish parts carry no displayable content — ignore
      }

      if (assistantBlocks.length) {
        this.emit("event", {
          type: "assistant",
          message: { role: "assistant", content: assistantBlocks },
        });
      }
      if (toolResults.length) {
        this.emit("event", {
          type: "user",
          message: { role: "user", content: toolResults },
        });
      }
      return;
    }

    // Unknown shape — pass through unchanged
    this.emit("event", event);
  }

  kill(): void {
    this._queue = [];
    this._draining = false;
    if (this._sseAbort) {
      this._sseAbort.abort();
      this._sseAbort = null;
    }
    if (this.proc) {
      this.proc.kill("SIGTERM");
      this.proc = null;
      this._ready = false;
    }
    this._toolParts.clear();
    this._streamingParts.clear();
  }

  get pid(): number | undefined {
    return this.proc?.pid;
  }
}
