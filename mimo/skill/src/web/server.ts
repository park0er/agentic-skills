import { createServer, type IncomingMessage, type ServerResponse } from "http";
import { readFileSync, readdirSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

// SSE clients
const sseClients: Set<ServerResponse> = new Set();

// Store current eval state for new clients
let currentEvalState: object | null = null;

export function broadcast(data: object): void {
  // Store eval_started state
  if ((data as any).type === "eval_started") {
    currentEvalState = data;
  }

  const payload = `data: ${JSON.stringify(data)}\n\n`;
  for (const client of sseClients) {
    try {
      client.write(payload);
    } catch {
      sseClients.delete(client);
    }
  }
}

function serveHTML(res: ServerResponse): void {
  const html = readFileSync(join(__dirname, "index.html"), "utf-8");
  res.writeHead(200, {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
  });
  res.end(html);
}

function handleSSE(req: IncomingMessage, res: ServerResponse): void {
  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
    "Access-Control-Allow-Origin": "*",
  });
  res.write("\n");

  // Send current eval state to new client immediately
  if (currentEvalState) {
    const payload = `data: ${JSON.stringify(currentEvalState)}\n\n`;
    res.write(payload);
  }

  sseClients.add(res);
  req.on("close", () => sseClients.delete(res));
}

function handlePostMessage(
  req: IncomingMessage,
  res: ServerResponse,
  onMessage: (text: string, side?: string) => void,
): void {
  let body = "";
  req.on("data", (chunk) => (body += chunk));
  req.on("end", () => {
    try {
      const data = JSON.parse(body);
      onMessage(data.text, data.side);
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end('{"ok":true}');
    } catch {
      res.writeHead(400);
      res.end('{"error":"invalid json"}');
    }
  });
}

// ─── History storage ─────────────────────────────────────────────────
const HISTORY_DIR = join(process.env.HOME || "/tmp", ".mimo-eval", "history");

function ensureHistoryDir() {
  if (!existsSync(HISTORY_DIR)) mkdirSync(HISTORY_DIR, { recursive: true });
}

function handleHistoryList(_req: IncomingMessage, res: ServerResponse): void {
  ensureHistoryDir();
  try {
    const files = readdirSync(HISTORY_DIR).filter((f) => f.endsWith(".json")).sort().reverse();
    const summaries = files.map((f) => {
      try {
        const data = JSON.parse(readFileSync(join(HISTORY_DIR, f), "utf-8"));
        return {
          evalId: data.evalId,
          taskName: data.taskName,
          modelA: data.modelA,
          modelB: data.modelB,
          startedAt: data.startedAt,
          endedAt: data.endedAt,
        };
      } catch {
        return null;
      }
    }).filter(Boolean);
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(summaries));
  } catch {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end("[]");
  }
}

function handleHistoryDetail(evalId: string, res: ServerResponse): void {
  ensureHistoryDir();
  const file = join(HISTORY_DIR, `${evalId}.json`);
  if (!existsSync(file)) {
    res.writeHead(404);
    res.end('{"error":"not found"}');
    return;
  }
  try {
    const data = readFileSync(file, "utf-8");
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(data);
  } catch {
    res.writeHead(500);
    res.end('{"error":"read failed"}');
  }
}

function handleSaveHistory(req: IncomingMessage, res: ServerResponse): void {
  let body = "";
  req.on("data", (chunk) => (body += chunk));
  req.on("end", () => {
    try {
      const data = JSON.parse(body);
      ensureHistoryDir();
      const file = join(HISTORY_DIR, `${data.evalId}.json`);
      writeFileSync(file, JSON.stringify(data, null, 2));
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end('{"ok":true}');
    } catch {
      res.writeHead(400);
      res.end('{"error":"invalid json"}');
    }
  });
}

export interface WebServerOptions {
  port: number;
  stateDir?: string;
  onUserMessage: (text: string, side?: string) => void;
  onSubmitSide?: (side: string, feedback: { adoption?: string; rating?: number; output_rating?: number; feedback?: string }) => void;
  onEnd?: (feedback?: { adoption?: string; rating?: number; output_rating?: number; feedback?: string }) => void;
}

export function startWebServer(opts: WebServerOptions): ReturnType<typeof createServer> {
  const server = createServer((req, res) => {
    const url = req.url?.split("?")[0] || "/";

    // CORS preflight
    if (req.method === "OPTIONS") {
      res.writeHead(204, {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      });
      res.end();
      return;
    }

    if (url === "/" && req.method === "GET") {
      serveHTML(res);
      return;
    }

    if (url === "/events" && req.method === "GET") {
      handleSSE(req, res);
      return;
    }

    if (url === "/message" && req.method === "POST") {
      handlePostMessage(req, res, opts.onUserMessage);
      return;
    }

    if (url === "/submit-side" && req.method === "POST") {
      let body = "";
      req.on("data", (chunk) => { body += chunk; });
      req.on("end", () => {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end('{"ok":true}');
        try {
          const data = JSON.parse(body);
          opts.onSubmitSide?.(data.side, data);
        } catch {}
      });
      return;
    }

    if (url === "/end" && req.method === "POST") {
      let body = "";
      req.on("data", (chunk) => { body += chunk; });
      req.on("end", () => {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end('{"ok":true}');
        try {
          const data = JSON.parse(body);
          opts.onEnd?.(data);
        } catch {
          opts.onEnd?.();
        }
      });
      return;
    }

    if (url === "/history" && req.method === "GET") {
      handleHistoryList(req, res);
      return;
    }

    if (url.startsWith("/history/") && req.method === "GET") {
      const evalId = url.slice("/history/".length);
      handleHistoryDetail(evalId, res);
      return;
    }

    if (url === "/save-history" && req.method === "POST") {
      handleSaveHistory(req, res);
      return;
    }

    res.writeHead(404);
    res.end("Not Found");
  });

  server.listen(opts.port, "0.0.0.0", () => {
    console.log(`\n🌐 Web 评测界面已启动: http://0.0.0.0:${opts.port}`);
  });

  return server;
}
