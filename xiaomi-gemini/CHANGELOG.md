# xiaomi-gemini CHANGELOG

## 2026-06-25 — responses-bridge-signature-fallback

- 增强 Gemini thought signature 兼容层：除 tool call id 外，同时按函数名、`default_api:<name>` 缓存和回填。
- 新增最新/唯一 signature 兜底，兼容 Codex++ 这类会在 Responses 与 Chat Completions 间转换并重建消息历史的中间层。
- 支持从 Gemini 流式 SSE 响应的 `choices[].delta.tool_calls[]` 中提取 signature；回归测试覆盖“流式第一轮 + 第二轮 id/name 被重写”的场景。

## 2026-06-24 — gemini-tool-signature-compat

- 新增 Gemini 3 tool calling thought signature 兼容层：缓存 `tool_calls[].extra_content.google.thought_signature`，并在客户端丢失该字段后的后续请求里自动回填。
- 新增 `scripts/test_gemini_tool_signature.py`，模拟 OpenAI 客户端丢弃 `extra_content` 的多轮工具调用场景，防止再次出现 `Function call is missing a thought_signature`。
- 文档补充官方约束与代理兼容策略：按请求 `user` 字段隔离 signature 缓存，没有 `user` 时按本机客户端 IP。

## 2026-06-24 — accept-any-client-key

- 本地 OpenAI-compatible 代理默认接受任意客户端 API key，方便接入只要求填写 key 的客户端。
- 上游 Mify/Gemini 真实 key 仍只保存在 `~/.config/xiaomi-gemini/config.json`，不会暴露给客户端。
- 保留 `--proxy-key` 作为可选严格校验模式；不传则不校验客户端 key。

## 2026-06-24 — increase-smoke-token-budget

- 将 `manage_proxy.py smoke` 的默认 `max_tokens` 从 32 调整为 1024，避免 Gemini 3.5 Flash 在诊断请求中只返回 reasoning 元信息而无可见正文。
- 不改变代理对真实客户端请求的透传行为。

## 2026-06-24 — update-gemini-3-models

- Gemini 默认暴露模型更新为 `gemini-3.1-pro-preview` 与 `gemini-3.5-flash`，匹配当前用户截图里的可选模型。
- 同步更新 smoke 示例，后续安装和 repair 都会写入新的 Gemini 模型清单。

## 2026-06-24 — clean-release-artifacts

- 清理 skill 源目录里的 Python `__pycache__` 编译缓存，避免 release 包包含运行时噪音。
- 不改变代理功能或运行配置；仅重新发布干净 skill 包。

## 2026-06-24 — initial-openai-proxy

- 新增独立 `xiaomi-gemini` skill，专门管理本机 OpenAI-compatible 聚合代理，不改动 `mify-model-gateway`。
- 代理默认聚合 Mify 截图模型与 Gemini OpenAI-compatible 模型，对外统一暴露一个本机 Base URL 和一个本地 API key。
- 新增 LaunchAgent 安装、开机启动、状态检查、修复、卸载和 smoke test 工作流。
- 上游 key 只写入用户本机 `~/.config/xiaomi-gemini/config.json`，不进入 skill 源码或项目仓库。
