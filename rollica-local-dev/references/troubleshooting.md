# Troubleshooting — Rollica / Multica local dev

Machine paths live in `local-dev.yaml`, not here. Persistent-QA recovery is in
`persistent-qa.md`.

## Table of contents
- Container runtime / China Docker Hub
- Next.js dev: slow first compile + ChunkLoadError
- Daemon must be source-built (the #1 mistake)
- Daemon auth vs IDE/Cloud login are separate
- DB schema cheat-sheet (table/column names)
- Squash/force-push hazard when `origin/main` advanced
- Model discovery / provider display name
- Verifying a task ran

## Container runtime / China Docker Hub
- No `docker` and no Docker Desktop/OrbStack → install Colima:
  `brew install colima docker docker-compose`, then add the compose plugin dir to
  `~/.docker/config.json`: `{"cliPluginsExtraDirs":["/opt/homebrew/lib/docker/cli-plugins"]}`,
  then `colima start`. Verify `docker ps` and `docker compose version`.
- On a CN network `make dev` fails at `pgvector/pgvector:pg17 ... registry-1.docker.io ... EOF`.
  Pre-pull via a mirror and retag (scripts/pgvector-mirror-pull.sh). `docker.m.daocloud.io`
  worked reliably; `pgvector/pgvector:pg17` is the only image `make dev` needs.
- `ensure-postgres.sh` only uses Docker when the DB host is localhost/127.0.0.1/::1.
  A non-local `DATABASE_URL` makes it skip Docker entirely (alternative to Colima
  if you have a remote/managed Postgres with the pgvector extension).

## Next.js dev: slow first compile + ChunkLoadError
- `make dev` runs `next dev --webpack`. Each route compiles on its FIRST request
  (often 20–170s for heavy routes like `/[slug]/agents`). A blank page is usually
  just compiling, not hung. Warm routes with scripts/warm-dev-pages.sh.
- `Runtime ChunkLoadError: Loading chunk .../page failed (timeout ...)` with a
  "(stale)" badge = the browser held an old build manifest while a slow compile
  timed out. Fix: hard refresh (Cmd+Shift+R) after the route is warm.
- Any frontend edit invalidates the chunks of every route importing the changed
  file, so re-warm after changing e.g. `provider-logo.tsx`.
- `Failed to proxy .../ws ... socket has been ended` is a flaky dev WS proxy; the
  board may not live-update. Verify task progress via the daemon log + DB instead.

## Daemon must be source-built (the #1 mistake)
- `make dev` starts only server + web, NOT a daemon (`scripts/dev.sh` runs migrate
  + `go run ./cmd/server` + `pnpm dev:web`).
- The daemon that executes tasks must come from THIS checkout, or local code
  changes (new provider, daemon fix) are not present. `make build` →
  `server/bin/multica`, then `server/bin/multica daemon start --profile local`.
  `daemon start` re-execs `os.Executable()`, so launching the source binary keeps
  the daemon on source code.
- The daemon detects agent CLIs via the login shell PATH. If the CLI under test
  is not on that PATH, pass `MULTICA_<PROVIDER>_PATH=/abs/path` in the daemon's
  environment. Confirm detection in `daemon status` (the `Agents:` line) and that
  a row exists: `select provider,name,status from agent_runtime;`.

## Daemon auth vs IDE/Cloud login are separate
- The CLI/daemon `local` profile stores `{server_url, app_url, workspace_id, token}`
  in `~/.multica/profiles/<profile>/config.json`; the token is a `mul_` PAT.
- A logged-in IDE (e.g. Trae IDE / Multica.app) does NOT authenticate the CLI —
  separate credential stores (often the OS keychain). The CLI needs its own login.
- For a local server you can skip browser OAuth by minting a PAT directly in the
  DB (scripts/local-daemon-login.sh) and using `multica login --token`.
- `multica daemon restart --profile local` re-registers runtimes (e.g. to pick up
  a changed display name) without a fresh login.

## DB schema cheat-sheet
Connect: `docker compose exec -T postgres psql -U multica -d multica -Atc "<SQL>"`.
- `"user"` — reserved word, MUST be double-quoted. Cols: id, email, created_at, ...
- `workspace` — id, slug, name, ...
- `agent_runtime` — provider, name, status, daemon_id, ... (NO `launch_header` col).
- `agent` — runtime_id, name, model, ... (provider lives on agent_runtime, not agent).
- `agent_task_queue` — id, agent_id, issue_id, status, error, session_id, work_dir,
  started_at, completed_at, ... (NO `provider` col).
- `issue` — id, title, status (todo/in_progress/in_review/done/...); NO `identifier` col.
- `comment` — issue_id, author_type, author_id, content, type, ... (the agent's
  reply lands here; NOT `issue_comment`).
- `personal_access_token` — id, user_id, name, token_hash, token_prefix,
  expires_at, revoked, created_at. token_hash = sha256_hex(raw); raw = `mul_`+40hex.

## Squash / force-push hazard when `origin/main` advanced
- When squashing a feature branch with `git reset --soft <base>`, use the branch's
  TRUE base (the parent of your first commit, `git rev-parse <firstcommit>^`), NOT
  `origin/main` — `origin/main` may have moved forward, and resetting to it stages
  hundreds of unrelated files (it would revert main's work if committed).
- Always sanity-check before committing a squash: `git diff --cached --name-only | wc -l`
  should be only YOUR files. If it shows hundreds, you reset to the wrong base —
  recover with `git reset --mixed <your-last-commit>` (working tree is preserved).
- Force-pushing your own fork's PR branch with `--force-with-lease` is fine and is
  how you keep a clean single-commit PR after amending/squashing.

## Model discovery / provider display name
- ACP backends discover models from `session/new` (`models.availableModels`); a
  not-logged-in CLI may return none (or crash on `session/new`), which surfaces as
  an empty model dropdown — log the CLI in first.
- The runtime display name shown in the UI is the daemon's `providerDisplayName`
  (title-cased provider key by default; override per provider in daemon.go).

## Verifying a task ran (without trusting the flaky board WS)
- `tail -f ~/.multica/profiles/local/daemon.log` — shows tool calls and
  `<provider> finished ... status=completed`.
- `select status,error,session_id,started_at,completed_at from agent_task_queue order by created_at desc limit 1;`
- `select created_at,left(content,300) from comment where issue_id='<id>' order by created_at desc limit 3;`
  — confirms the agent posted its result.
