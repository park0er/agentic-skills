---
name: xiaomi-gemini
description: Use when installing, running, checking, repairing, or using the local Xiaomi Gemini OpenAI-compatible proxy. It exposes one local OpenAI Base URL and API key, then routes Mify models from api.llm.mioffice.cn plus Gemini OpenAI-compatible models through one LaunchAgent-backed localhost service. Triggers on xiaomi_gemini, Gemini proxy, OpenAI compatible proxy, local model proxy, Base URL aggregation, LaunchAgent repair/status for this proxy.
---

# Xiaomi Gemini Proxy

本 skill 管理一个独立本地 OpenAI-compatible 聚合代理，不依赖 `mify-model-gateway`：

- 对外暴露一个本机 Base URL：`http://127.0.0.1:<port>/v1`
- 默认接受任意客户端 API key：客户端按 OpenAI 方式填任意非空 `Authorization: Bearer <key>` 即可
- 内部转发到两个上游：Mify OpenAI-compatible 和 Gemini OpenAI-compatible
- 通过 LaunchAgent 开机启动，脚本和配置都放在用户目录，不写入项目仓库

## 安全边界

- 不要把 Mify/Gemini 上游 key 写进项目源码、文档、commit、skill 的 `SKILL.md` 或 references。
- 上游 key 只允许写入 `~/.config/xiaomi-gemini/config.json`，该文件由 `manage_proxy.py install` 创建并 `chmod 600`。
- skill 源码只包含脚本和默认模型清单，不包含真实 key。

## Gemini 工具调用兼容

Gemini 3 工具调用多轮对话要求把模型返回的 thought signature 原样带回。OpenAI-compatible 响应里 signature 位于：

```text
choices[].message.tool_calls[].extra_content.google.thought_signature
```

很多 OpenAI 客户端会丢掉 `extra_content` 这个 Google 私有字段，导致第二轮工具结果回传时报错 `Function call is missing a thought_signature`。代理会按 `user` 字段（没有则按本机客户端 IP）缓存 tool call id 对应的 signature，并在后续 Gemini 请求中自动回填缺失字段。

如果上游客户端先把 Chat Completions 转成 Responses 协议再转回来，消息历史可能被重建，`tool_call.id`、函数名或 assistant/tool 消息结构都可能变化。代理会按三层顺序补签名：先按 tool call id，其次按函数名，最后在当前会话只有一个最近 signature 时用最新 signature 兜底。代理也会解析 Gemini 流式 SSE 响应里的 `choices[].delta.tool_calls[].extra_content.google.thought_signature`。

验证这个兼容层：

```bash
python3 "$SKILL_DIR/scripts/test_gemini_tool_signature.py"
```

## 默认模型

Mify 上游默认暴露：

- `zhipuai/glm-5.2`
- `minimax/MiniMax-M3`
- `ppio/pa/gpt-5.5`
- `xiaomi/mimo-v2.5-pro`
- `xiaomi/mimo-v2.5`
- `deepseek/deepseek-v4-pro`

Gemini 上游默认暴露：

- `gemini-3.1-pro-preview`
- `gemini-3.5-flash`

## 常用命令

设定：

```bash
SKILL_DIR="$HOME/.agents/skills/xiaomi-gemini"
```

首次安装，必须传入两个上游 key：

```bash
python3 "$SKILL_DIR/scripts/manage_proxy.py" install \
  --mify-key '<MIFY_KEY>' \
  --gemini-key '<GEMINI_KEY>'
```

查看状态：

```bash
python3 "$SKILL_DIR/scripts/manage_proxy.py" status
```

打印客户端要填的 OpenAI 配置：

```bash
python3 "$SKILL_DIR/scripts/manage_proxy.py" show-credentials
```

验证某个模型：

```bash
python3 "$SKILL_DIR/scripts/manage_proxy.py" smoke --model gemini-3.5-flash
python3 "$SKILL_DIR/scripts/manage_proxy.py" smoke --model xiaomi/mimo-v2.5
```

修复代理（重拷贝 runtime 脚本、重写 LaunchAgent、复用已保存 key 并重启）：

```bash
python3 "$SKILL_DIR/scripts/manage_proxy.py" repair
```

如果 key 变了，修复时显式覆盖：

```bash
python3 "$SKILL_DIR/scripts/manage_proxy.py" repair \
  --mify-key '<NEW_MIFY_KEY>' \
  --gemini-key '<NEW_GEMINI_KEY>'
```

停止、重启、卸载：

```bash
python3 "$SKILL_DIR/scripts/manage_proxy.py" stop
python3 "$SKILL_DIR/scripts/manage_proxy.py" restart
python3 "$SKILL_DIR/scripts/manage_proxy.py" uninstall
```

彻底清理 runtime 和保存的 key：

```bash
python3 "$SKILL_DIR/scripts/manage_proxy.py" uninstall --purge
```

## 工作流

### 安装

1. 确认用户提供 Mify key 和 Gemini key。
2. 运行 `install`。
3. 运行 `status` 确认 LaunchAgent loaded 且 healthz ok。
4. 分别用 Gemini 和 Mify 模型跑 `smoke`。
5. 把 `show-credentials` 输出的 Base URL 告诉用户；默认 `OPENAI_API_KEY=anything`，也可填任意非空值。

### 检查状态

先运行：

```bash
python3 "$SKILL_DIR/scripts/manage_proxy.py" status
```

重点看：

- `plist` 是否 exists
- `runtime_script` 是否 exists
- `config` 是否 exists
- `launchd` 是否 loaded
- `healthz` 是否 ok

### 修复

遇到 LaunchAgent 未加载、runtime 脚本丢失、healthz 失败、安装目录漂移时，优先运行：

```bash
python3 "$SKILL_DIR/scripts/manage_proxy.py" repair
```

如果 `repair` 提示缺 key，说明 `~/.config/xiaomi-gemini/config.json` 不存在或损坏，需要用户重新提供 key 后再运行带 key 的 `repair`。

### 客户端接入

客户端按 OpenAI-compatible 填：

```text
OPENAI_BASE_URL=http://127.0.0.1:<port>/v1
OPENAI_API_KEY=anything
```

Chat completions endpoint 是：

```text
http://127.0.0.1:<port>/v1/chat/completions
```

## 文件地图

- `scripts/openai_compatible_proxy.py`：本地 OpenAI-compatible HTTP 代理。
- `scripts/manage_proxy.py`：安装、LaunchAgent 管理、状态检查、修复、smoke test。
- `scripts/test_gemini_tool_signature.py`：Gemini tool calling thought signature 回填回归测试。

运行时文件：

- `~/.local/share/xiaomi-gemini/openai_compatible_proxy.py`
- `~/.config/xiaomi-gemini/config.json`
- `~/Library/LaunchAgents/com.local.xiaomi-gemini-openai-proxy.plist`
- `~/Library/Logs/xiaomi-gemini/proxy.out.log`
- `~/Library/Logs/xiaomi-gemini/proxy.err.log`
