# Owner 速查 & 选择策略

## 强制调用约定

**Mify 的 `/v1/chat/completions` 调用时，`model` 参数必须是 `{owned_by}/{id}` 格式**，裸 id 一律返回 `HTTP 400 "Param Incorrect: Not supported model"`。

- `"model": "kimi-k2.5"` ✗
- `"model": "xiaomi/kimi-k2.5"` ✓
- `"model": "tongyi/kimi-k2.5"` ✓
- `"model": "siliconflow/moonshotai/Kimi-K2-Thinking"` ✓（原 id 带斜杠也要再在最外层加 owner）

原因：同一个 id 在多个 owner 下共存，网关用裸 id 无法路由。`list_models.py` 输出的 CALL AS 列就是直接可用的字符串。

## Owner 对照表

Mify 网关里同一个 `model id` 可能由多个 `owned_by` 提供，本质是不同上游通道。当前（基于实测）网关有 **13 个 owner 通道**，按接入模型数量排序见下表。

## Owner 对照表

| `owned_by` | 实际上游 | 定位 |
|---|---|---|
| `tongyi` | 阿里云百炼 | 大厂 maas，Qwen / DeepSeek / Kimi 镜像常在这里；SLA 有保障。 |
| `azure_openai` | Azure OpenAI | GPT 系列（gpt-4o/5、o1/o3 等）的主要通道，走 Azure 区域节点。 |
| `siliconflow` | 硅基流动 | 第三方聚合，模型 id 常带 `moonshotai/`、`Pro/` 前缀。 |
| `volcengine_maas` | 火山方舟（字节） | 豆包系 / MoE；模型 id 常见 6 位日期后缀（`-250711`）。 |
| `ppio` | 派欧云 | 第三方聚合，常作备选。 |
| `xiaomi` | 小米自建推理集群 | 成本最低、合规最稳、内部 SLA；MiLM / MiMo 等自研模型独占。 |
| `zhipuai` | 智谱 AI | GLM 系列官方直连。 |
| `baidu_qianfan` | 百度千帆 | 文心等百度系模型。 |
| `wenxin` | 百度文心 | 文心一言官方直连。 |
| `hunyuan` | 腾讯混元 | 混元系列官方直连。 |
| `minimax` | MiniMax 官方 | Abab / MiniMax 系列。 |
| `vertex_ai` | Google Vertex | Gemini 系列。 |
| `cloudml` | 小米 Cloud-ML | 小米内部机器学习平台出口（通常量很小）。 |

上游列表可能会随时调整，以 `list_models.py --all --summary` 实际返回的 `owned_by` 分布为准。

## 推荐选择顺序

一般情况（无特殊合规/版本要求）：

```
xiaomi > tongyi ≈ volcengine_maas > 官方直连（zhipuai/minimax/hunyuan/wenxin）> siliconflow ≈ ppio > azure_openai / vertex_ai
```

### 什么时候偏离默认顺序

- **要最新版本**：官方直连通道（`zhipuai` / `minimax` / `hunyuan` 等）和 `azure_openai` 通常最先拿到新版本；`xiaomi` 自建可能滞后。
- **有合规/数据出境要求**：只选境内节点（`xiaomi` / `tongyi` / `volcengine_maas` / `baidu_qianfan` / `wenxin` / `hunyuan` / `zhipuai` / `minimax`）；**不要用** `azure_openai` / `vertex_ai`，它们数据会出境。
- **要 GPT 系列**：目前只有 `azure_openai`。
- **要 Gemini 系列**：目前只有 `vertex_ai`。
- **已知某 owner 通道不稳**：同名模型换一个 owner 即可，无需改调用代码逻辑（只是 model id 或绑定关系变化）。
- **成本优先**：`xiaomi` 自建（内部计费）通常最便宜。

## Model type 对照

网关里 `model_type` 取值（按数量排序，约 450 个模型的分布）：

| type | 数量量级 | 说明 |
|---|---|---|
| `llm` | 最多（~400） | 对话/文本生成模型，走 `/v1/chat/completions`。 |
| `text-embedding` | ~30 | 嵌入，走 `/v1/embeddings`。**注意连字符：`text-embedding` 而不是 `embedding`**。 |
| `rerank` | ~10 | 重排序模型，endpoint 通常是 `/v1/rerank`（非 OpenAI 标准）。 |
| `speech2text` | ~7 | ASR，走 `/v1/audio/transcriptions`。 |
| `image_generation` | ~3 | 文生图。 |
| `tts` | ~2 | 文本转语音。 |
| `realtime` | ~1 | 实时多模态 API（类似 OpenAI realtime）。 |
| `text_translation` | ~1 | 文本翻译专用。 |

**本 skill 的 `test_model.py` 只支持 `llm` 类型的 smoke test。**其他类型请告知用户要手测。

## 特殊命名模式

有些模型在 id 里就带了 owner 前缀，这是网关为了消除冲突：

| 命名模式 | 含义 |
|---|---|
| `moonshotai/Kimi-K2-Thinking` | siliconflow 通道下的 Moonshot 模型 |
| `Pro/moonshotai/Kimi-K2-Instruct` | siliconflow 的 "Pro"（高优）版本 |
| `kimi-k2.5`（无前缀） | xiaomi 或 tongyi 通道的简写 id |
| `kimi-k2-250711` | 火山方舟的内部版本号（YYMMDD） |
| `MiLM2.1-13B-Chat`、`MiMo-*` | 小米自研模型 |
| `gpt-4o-2024-11-20` 等官方版本号 | 通常是 azure_openai 通道 |

当用户问「最新 X」时，候选常横跨多种命名，应把所有可能的 id 都列给他，然后按上面「偏离默认顺序」条件挑。**不要脑补一个命名**，网关里没有的 id 一定 400。
