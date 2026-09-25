---
name: rollica-pi-model-policy
description: 维护 Rollica 的 Mify/Pi 推荐模型配置。用户要求增加某供应商的模型、修改默认模型、配置思考档位或生成可上传 FDS 的 default-model.json 时使用。查询 Mify 精确路由，核对模型与协议能力，使用对应 Pi 版本验证全部可选档位及工具往返，输出符合仓库协议的完整配置与验证记录。默认只生成候选文件，不上传共用 FDS，不修改用户的 Pi、Claude 或 Codex 配置。
---

# Rollica Pi 推荐模型配置

目标：用户只需说“加一个某供应商的某模型”，最终得到可校验、可复测的完整 `default-model.json`。不要靠模型名字猜思考能力，也不要认为 `reasoning:true` 会继承 Pi 官方目录。

## 1. 确定基线

- 使用 `mify-model-gateway` skill 查询、认证和测试；读取其当前说明。没有 Key 时只报告缺少凭据，不打印、复制或替用户更换其他应用的 Key。
- 定位用户当前 Rollica checkout（不要硬编码某个 worktree）；读取 `openspec/changes/mia-340-managed-pi-runtime/managed-pi-policy-protocol.md`、schema 与 `default-model.json`。
- 只读下载当前 FDS 对象作为编辑基线，和仓库版本比较。失败时注明使用仓库基线，不能宣称它就是线上最新版：
  `https://cnbj1-fds.api.xiaomi.net/rollica/config/default-model/default-model.json`
- staging / production 共用这个对象。生成文件不等于获准发布；只有用户明确要求上传时才上传。
- 查 `apps/desktop/resources/pi/manifest.json`（若移动，用 rg 找实际 manifest）的 Pi 版本。验证 SDK 必须与目标 Pi 版本一致；不能悄悄拿另一套 npm Pi 的目录知识替代。
- 保留用户未要求更改的模型、默认值、endpoint 和兼容配置。默认 GLM 5.3 Flash；新增候选不自动更换默认。

## 2. 查到真实路由和能力

运行 gateway skill 的 `scripts/list_models.py --grep <关键词> --json`。调用 ID 用完整 `owned_by/id`，用户指定原厂就选原厂，不能因为另一云厂商同名就替代。

分别核对：模型可用、思考开关、思考档位、工具调用、上下文/最大输出。参考原厂官方文档及对应 Pi 版本源码；保存链接和日期。文档缺失时以实测为有限证据，不能编造上下文、价格或图像能力。HTTP 200 只证明接收请求，不能证明各档位背后的计算预算真的不同。

## 3. 编辑完整候选文件

复用现有 `endpoints[].routes[].catalogId`，不同协议有差异就指向不同目录，不增加模糊匹配和本地 catalog 快照。

每个推理模型显式写全部七个键：
`off / minimal / low / medium / high / xhigh / max`。

- `reasoning:true` 表示模型支持思考。
- 普通非推理模型写 `reasoning:false`，不编造 thinkingLevelMap；验证脚本只走 off 档及工具往返。
- `thinkingLevelMap` 字符串是发给网关的值；`null` 表示禁用该档位；省略表示 Pi 的默认行为，**不等于禁用**。
- OpenAI 的 off 通常映射 `"none"`；Anthropic 的 off 由 Pi 发 `thinking.type=disabled`，不是发 effort none。
- Mify OpenAI 目录使用 `compat.supportsDeveloperRole:false`，避免 Pi 给推理模型发不兼容的 developer 消息。不要全开 compat，不套到其他网关。
- Mify Anthropic 经验证支持 effort 时使用 `forceAdaptiveThinking:true`；否则 Pi 走 token budget，单写 map 不会转换为 effort。工具兼容项以实测为准，不复制 OpenAI 专属字段。
- 当前基线 Anthropic 使用 `supportsEagerToolInputStreaming:false`、`allowEmptySignature:true`；后者用于网关返回无签名 thinking 的工具后续回传。
- 已发现的协议差异：DeepSeek V4 Flash 的 `minimal` 在 OpenAI 可用，但在 Anthropic effort 被拒，应为 null。未来重新测试，不把历史结果当永恒规则。
- 更新 `revision` 与真实 UTC `publishedAt`。任何内容改动都换 revision；不改 schemaVersion 除非仓库协议也升级。

## 4. 运行两层验证

先用 Rollica 真正的校验器，不另写一套宽松替身：

```sh
node apps/desktop/scripts/validate-pi-policy.mjs /absolute/path/default-model.json
cd server
ROLLICA_PI_POLICY_CANDIDATE=/absolute/path/default-model.json go test ./internal/runtimepolicy -run TestPolicyCandidateRoundTrip -count=1
```

Node 要求 22.18+。Go 检查与服务端相同的字段、引用、host 限制及 JSON 往返，必须保留 null。

在独立临时目录安装匹配版本的 `@earendil-works/pi-ai`（不是全局安装，不改项目依赖）。使用本 skill 的脚本：

```sh
node <skill-dir>/scripts/verify-policy.mjs \
  --policy /absolute/path/default-model.json \
  --sdk-dir /temporary/node_modules/@earendil-works/pi-ai \
  --report /absolute/path/dry-run.json
```

默认仅捕获 Pi 请求，不联网、不读取用户 Pi 文件。确认生成的 role/effort/thinking 字段正确后，用户的模型配置验证请求授权小额测试调用：

```sh
node <skill-dir>/scripts/verify-policy.mjs \
  --policy /absolute/path/default-model.json \
  --sdk-dir /temporary/node_modules/@earendil-works/pi-ai \
  --live --tools --report /absolute/path/verification.json
```

Key 从环境 `MIFY_API_KEY` 提供，可 source 用户已有 credentials；绝不放到参数、候选 JSON、报告或 Issue。脚本验证两种协议、所有启用档位、默认 medium 的 Pi 钳制结果、工具调用及工具结果回传。用 `--model owner/id` 定向排查，交付前跑完整候选。

失败处理：400 参数错误应修配置、重测；401/403 是权限问题，不捏造通过；429/超时先区分临时失败；空内容或输出截断不算通过。不要为了过测试而改写 SDK payload、偷换模型、禁用 TLS 校验、启动代理或修改用户的 Pi 文件。

## 5. 交付与发布

输出：
1. 完整候选 `default-model.json`，不是局部片段。
2. 验证报告：revision、Pi 版本、测试时间、每个协议/模型/档位结果、工具往返和已知限制。
3. 简短说明：新增了什么、默认是否变化、需不需要更新代码。

仓库实现一起变更时，同步内置 fallback、schema、OpenSpec；做独立只读 review 并关闭 P1+，使用当前已登录的 Rollica CLI 更新绑定 Issue、附配置和报告；若本机已有 `rollica-management`，可用其包装器。不默认生成 HTML 或发 Sites。

新字段需要先部署支持它的 Server/桌面端，再上传共用 FDS；旧版本严格校验可能拒绝新策略，保持缓存/内置旧配置。回滚用上一份验证内容加新 revision。普通新增模型不需要新环境变量或数据库迁移。

**不得自动写用户 `~/.pi/agent`**：Rollica 现有设置/推荐同步负责写入，用户手改后暂停跟随的合同保持不变。若需真实 Pi RPC 验证，使用临时 `PI_CODING_AGENT_DIR`，禁用扩展、skill 和会话保存。
