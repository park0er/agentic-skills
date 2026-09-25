---
name: paseo-local-dev
description: "Set up, run, test, maintain, and tear down a complete local Paseo development environment for contributing features upstream. Use when the user says: 搭本地 paseo 开发环境 / paseo dev setup / 起 paseo daemon / start dev daemon / 在本地测试 paseo / 跑 paseo e2e / paseo iOS 测试 / paseo 模拟器 / paseo 健康检查 / dev env health / 清理 paseo dev 环境 / paseo dev teardown / paseo-local-dev / 新机器搭 paseo 开发. Covers: forking and cloning the repo, creating a feature worktree, building and running an isolated dev daemon, web app dev server + Playwright e2e, iOS simulator build + test, environment health checks, and full cleanup/teardown. Does NOT manage the production patched daemon on 6767 (use paseo-fork-sync), does NOT handle import issues (use paseo-import-doctor)."
---

# Paseo Local Dev

Full-lifecycle local development environment for contributing features to [getpaseo/paseo](https://github.com/getpaseo/paseo).

## Architecture Overview

```
~/.paseo/                    ← production home (DON'T TOUCH)
<worktree>/.dev/paseo-home/  ← isolated dev home (safe to nuke)
                             
Daemon (dev): 127.0.0.1:6768  ← isolated, PASEO_HOME=worktree/.dev/paseo-home
Daemon (prod): 127.0.0.1:6767 ← production (managed by paseo-fork-sync)
Web app: localhost:8081        ← Metro dev server for app
```

## Prerequisites (auto-install)

Check each; install only if missing:

| Tool | Check | Install |
|------|-------|---------|
| Node 20+ | `node -v` | nvm / volta |
| npm 9+ | `npm -v` | comes with node |
| Xcode CLT | `xcode-select -p` | `xcode-select --install` |
| CocoaPods | `which pod` | `brew install cocoapods` |
| Playwright | `npx playwright --version` | `npx playwright install chromium` |
| applesimutils | `which applesimutils` | `brew install wix/brew/applesimutils` |
| gh CLI | `which gh` | `brew install gh` |

## Phase 1: Fork & Clone

```bash
# One-time: fork on GitHub, clone, add upstream
gh repo fork getpaseo/paseo --clone --remote
cd paseo
git remote rename origin origin  # already done by gh fork
git remote add upstream https://github.com/getpaseo/paseo.git
git fetch upstream
```

## Phase 2: Feature Worktree

Use a dedicated worktree for feature development (keeps main clone clean):

```bash
FEATURE=feat/my-feature
git worktree add ../paseo-features -b $FEATURE upstream/main
cd ../paseo-features
npm install
```

> **Tip**: For PRs stacked on another, branch off that branch instead of `upstream/main`.

## Phase 3: Build & Run Dev Daemon

### 3.1 Build server

```bash
npm run build:server-deps && npm run build:server
```

### 3.2 Seed dev home (first time)

```bash
mkdir -p .dev/paseo-home
# Seed a provider so the app has something to connect to:
cat > .dev/paseo-home/config.json << 'EOF'
{
  "version": 1,
  "daemon": {
    "listen": "127.0.0.1:6768",
    "cors": { "allowedOrigins": ["*"] }
  }
}
EOF
```

### 3.3 Start daemon

```bash
PASEO_HOME=$(pwd)/.dev/paseo-home \
PASEO_LISTEN=127.0.0.1:6768 \
  npm run dev:server
```

Background (detached):
```bash
nohup env PASEO_HOME=$(pwd)/.dev/paseo-home PASEO_LISTEN=127.0.0.1:6768 \
  npm run dev:server > .dev/daemon.log 2>&1 &
echo $! > .dev/daemon.pid
```

### 3.4 Verify daemon alive

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:6768/
# Expect: 404 (no GET / route, but proves HTTP is listening)
```

## Phase 4: Web App Dev + Testing

### 4.1 Start Metro (web)

```bash
cd packages/app
EXPO_PUBLIC_LOCAL_DAEMON=localhost:6768 npx expo start --web --port 8081
```

### 4.2 Run Playwright e2e

The e2e suite spawns its own isolated daemon (dynamic port), does NOT conflict with 6768:

```bash
cd packages/app
npx playwright test --project='Desktop Chrome'
# Single spec:
npx playwright test --project='Desktop Chrome' e2e/assistant-fork-menu.spec.ts
```

### 4.3 Run unit tests

```bash
# Server tests (vitest)
cd packages/server && npx vitest run
# App tests
cd packages/app && npm test
```

### 4.4 Typecheck + Lint + Format

```bash
npm run typecheck --workspace=@getpaseo/server
npm run typecheck --workspace=@getpaseo/app
npx oxlint <files>
npx oxfmt <files>
```

## Phase 5: iOS Simulator Testing

### 5.1 Prerequisites

```bash
# Xcode must be installed (App Store)
xcodebuild -version    # need 15+
which pod || brew install cocoapods
which applesimutils || brew install wix/brew/applesimutils
```

### 5.2 Prebuild native project

```bash
cd packages/app
npx expo prebuild --platform ios
# Generates ios/ directory (gitignored)
```

### 5.3 Install pods

CocoaPods requires UTF-8 locale (common gotcha):
```bash
cd ios
env LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 pod install
cd ..
```

### 5.4 Boot simulator

```bash
# List available:
xcrun simctl list devices available | grep iPhone
# Boot one:
xcrun simctl boot "iPhone 17"
open -a Simulator
```

### 5.5 Build & run on simulator

```bash
cd packages/app
env LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 \
  EXPO_PUBLIC_LOCAL_DAEMON=localhost:6768 \
  PATH=/opt/homebrew/bin:$PATH \
  npx expo run:ios --device "iPhone 17"
```

First build takes 15-25 min (native compile). Subsequent builds are incremental.

### 5.6 Dismiss permission dialogs

```bash
# Grant notifications before launch to suppress the dialog:
applesimutils --byId <UDID> --bundle sh.paseo --setPermissions "notifications=YES"
```

### 5.7 Navigate via deep link

```bash
# Open a specific agent session:
xcrun simctl openurl "iPhone 17" \
  "exp+voice-mobile:///h/<serverId>/agent/<agentId>"
```

### 5.8 Screenshot

```bash
xcrun simctl io "iPhone 17" screenshot /tmp/paseo-ios-screenshot.png
```

## Phase 6: Health Check

Run `scripts/health-check.sh` (see scripts/) to verify:

1. **Daemon liveness**: HTTP probe on 6768
2. **Metro running**: GET `localhost:8081/status` → "packager-status:running"
3. **Typecheck clean**: `npm run typecheck` exits 0
4. **Tests pass**: vitest + app tests exit 0
5. **Lint clean**: oxlint on changed files
6. **iOS build artifacts**: `ios/Pods` exists + `DerivedData` has Paseo.app

## Phase 7: Teardown & Cleanup

### Soft cleanup (keep worktree, remove build artifacts)

```bash
# Stop daemon
kill $(cat .dev/daemon.pid 2>/dev/null) 2>/dev/null
# Remove iOS native build
rm -rf packages/app/ios
# Remove Metro cache
rm -rf packages/app/.expo
# Remove DerivedData for this project
rm -rf ~/Library/Developer/Xcode/DerivedData/Paseo-*
```

### Full cleanup (remove everything)

```bash
# Stop daemon + simulator
kill $(cat .dev/daemon.pid 2>/dev/null) 2>/dev/null
xcrun simctl shutdown all 2>/dev/null
# Remove worktree
cd .. && git worktree remove paseo-features --force
# Remove homebrew deps (optional)
brew uninstall cocoapods applesimutils  # only if not used elsewhere
```

### Retire (when no longer contributing)

```bash
# Remove fork from GitHub
gh repo delete park0er/paseo --yes
# Remove all local clones
rm -rf ~/coding/paseo-contrib
```

## Common Issues

| Symptom | Fix |
|---------|-----|
| `pod install` → Encoding::CompatibilityError | Add `LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8` |
| `gem install cocoapods` hangs on system Ruby | Use `brew install cocoapods` instead |
| Daemon port already in use | `lsof -ti:6768 \| xargs kill` |
| Metro 8081 in use | Kill old Metro: `lsof -ti:8081 \| xargs kill` |
| Playwright timeouts | Ensure daemon not on 6767 (e2e refuses it) |
| iOS build fails "no ios/ dir" | Run `npx expo prebuild --platform ios` first |
| Simulator dialog blocks automation | Use `applesimutils --setPermissions` before launch |
| `cliclick` / AppleScript blocked | Grant Accessibility in System Settings → Privacy |
