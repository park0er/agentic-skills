# 如何设置 `$MIFY_API_KEY`

Mify skill 的所有脚本都从环境变量 `$MIFY_API_KEY` 读取 token。下面列了**最推荐的方式 0**（让 Claude 帮你一键装）和几种手动后备方式。

## 前置：拿到 token

Mify 的 API key 需要到内部 Mify 控制台申请。如果你没有，问你所在小组的 Mify 对接人，或在「小米 AI 生产力平台」相关飞书群里提个工单。格式形如 `sk-XXXXXXXXX...`（约 50 字符）。

拿到后选下面任一方式安装。

---

## 方式 0：让 Claude/Agent 帮你一键全局装（最推荐）

直接在对话里贴出 token，或提出更换 key 的指令，例如：

> 帮我把 Mify key 换成这个：`sk-你的token`

本 skill 的「一键全局安装与更新协议」会接管并**自动执行多组件同步覆盖**，彻底防漂移：

1. **校验并落盘**：调用 `scripts/install_token.py` 写入凭证文件 `~/.config/mify/credentials`（chmod 600）；
2. **活动环境同步**：执行 `launchctl setenv MIFY_API_KEY` 更新 Launchd 后台环境变量，使其他桌面 App 无需重启即可读取新 Key；
3. **Claude Code 自动同步**：更新 `~/.claude/settings.json` 的 `ANTHROPIC_AUTH_TOKEN`；
4. **Claude Desktop 历史配置清理**：同步更新 `~/Library/Application Support/Claude-3p/claude_desktop_config.json`；
5. **Codex 策略注入同步**：同步更新 `~/.codex/config.toml` 并自动对齐最新 Opus 4-8 代理模型；
6. **代理重启**：自动重启 `com.local.mify-claude-desktop-proxy` 本地代理进程以应用新环境，并验证 `healthz`。

**手动全局更新等价命令**：
如果你想手动触发局部凭证更新，可运行：
```bash
printf %s 'sk-你的token' | python3 ~/.claude/skills/mify-model-gateway/scripts/install_token.py
```
> 注：手动运行此脚本仅更新 `~/.config/mify/credentials` 与 rc 启动项，如需完整全局组件对齐，建议直接让 AI 运行全套协议，或手动更新各配置文件并重启本地代理。

---

## 方式 1：一次性（只在当前 shell 会话生效）

最简单，适合临时用：

```bash
export MIFY_API_KEY=sk-你的token
```

关掉终端就没了。适合脚本短暂 demo 或共享机器上临时操作。

---

## 方式 2：独立 secrets 文件 + zshrc/bashrc source（推荐）

Token 放在专属文件里，`chmod 600` 只有你本人可读，不会被 dotfiles git 仓库或同步工具误带走：

**a. 创建目录和文件：**

```bash
mkdir -p ~/.config/mify && chmod 700 ~/.config/mify

cat > ~/.config/mify/credentials <<'EOF'
# Mify 大模型网关 API Key
export MIFY_API_KEY=sk-你的token
EOF

chmod 600 ~/.config/mify/credentials
```

**b. 在 shell 启动文件里 source 它：**

zsh 用户（macOS 默认）：

```bash
cat >> ~/.zshrc <<'EOF'

# Mify 大模型网关凭据
[ -r "$HOME/.config/mify/credentials" ] && source "$HOME/.config/mify/credentials"
EOF
```

bash 用户把 `~/.zshrc` 换成 `~/.bashrc`（Linux）或 `~/.bash_profile`（macOS 老 bash）。

**c. 让当前终端立即生效（或开新终端）：**

```bash
source ~/.zshrc
```

**验证：**

```bash
echo "len=${#MIFY_API_KEY}, prefix=${MIFY_API_KEY:0:8}..."
# 期望输出：len=50 左右, prefix=sk-XXXXX
```

### 吊销 / 更换 token

为防止密钥漂移和组件失效，**不建议只修改 `~/.config/mify/credentials` 文件**。强烈建议使用 **一键全局更新** 流程：

1. **方式 A：让 Claude 帮你一键全局更新（推荐）**
   在对话中直接发送新 Key 并要求全局更新。Claude 会调用本 Skill 的 `一键全局安装与更新协议`，安全同步地覆盖：
   * `~/.config/mify/credentials`
   * launchd 环境变量 (for GUI Apps like Claude Desktop)
   * `~/.claude/settings.json` (for Claude Code)
   * `~/Library/Application Support/Claude-3p/claude_desktop_config.json`
   * `~/.codex/config.toml` (for Codex)
   * 重启本地 Proxy 代理服务。

2. **方式 B：手动分步更新**
   若需手动更换，请严格按以下步骤顺序操作：
   ```bash
   # 1. 修改凭据文件
   vi ~/.config/mify/credentials
   source ~/.zshrc
   
   # 2. 更新 launchd 环境变量
   launchctl setenv MIFY_API_KEY 'sk-你的新token'
   
   # 3. 顺次手动修改 ~/.claude/settings.json、~/Library/Application Support/Claude-3p/claude_desktop_config.json 和 ~/.codex/config.toml 中对应的旧密钥字段
   
   # 4. 重启本地代理服务
   python3 ~/.claude/skills/mify-model-gateway/scripts/manage_claude_desktop_proxy.py restart
   ```

### 和 git 的关系

如果你把 `~/.zshrc` 放进 dotfiles 仓库（很多开发者会这么做），这套方案天然安全：
- `~/.zshrc` 里只有 `source` 指令，**不含 token**，可以安全提交。
- `~/.config/mify/credentials` 不在仓库里，token 不外泄。

---

## 方式 3：直接 export 到 ~/.zshrc（不推荐）

```bash
echo 'export MIFY_API_KEY=sk-你的token' >> ~/.zshrc
source ~/.zshrc
```

能用但有两个风险：

1. 如果 `~/.zshrc` 进了 dotfiles git 仓库，token 会被提交上去。
2. 共享 / 调试 shell 配置时容易误贴出来。

只在**临时个人机**且不同步 dotfiles 的情况下用。

---

## 对 Claude / subagent 执行 skill 脚本的意义

Claude Code 调用本 skill 的 Bash 工具时，如果你的 shell 已经 export 了 `$MIFY_API_KEY`（方式 2/3 都可以），脚本会自动拿到；但 Claude 的每个 Bash 调用是**独立子 shell**，env 默认继承自父进程。

- **Claude Code CLI 本身**：启动时继承了你 login shell 的 env，所以方式 2 配好后再开 Claude Code，后续 bash 调用就有 token。
- **Agent / subagent**：它们的 bash 会继承父进程 env，所以同样没问题。

如果你验证 skill 脚本说「Missing $MIFY_API_KEY」，先在 Claude 的对话里让它跑：

```bash
echo "MIFY_API_KEY len=${#MIFY_API_KEY}"
```

确认 env 有没有传过来。如果没有，说明你是在 **Claude Code 启动之前** 配置的方式 2 还没生效 —— 重启一次 Claude Code 即可。

---

## 安全底线

以下是**绝对不要做**的事：

- ❌ 把 token 写进 SKILL.md、scripts/、references/、或 skill 目录里任何文件。Skill 是可能被打包分发的。
- ❌ 把 token 写到项目源码、commit message、PR 描述、issue 评论里。
- ❌ 在飞书群、Slack、公开聊天工具里粘贴完整 token。
- ❌ 把 `~/.config/mify/credentials` 放进任何 git 仓库。
- ❌ 共享机器上把 token 写到 `/etc/` 之类全局位置。

泄露了就立刻去 Mify 控制台吊销重发。
