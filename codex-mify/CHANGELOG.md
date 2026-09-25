# codex-mify CHANGELOG

## 2026-06-26 — fix-gemini-slugs

- Corrected Gemini catalog slugs from erroneous `google/gemini-2.5-*` entries to `gemini-3.1-pro` and `gemini-3.5-flash`.
- Kept both Gemini entries at 1M context / 950k effective context in Codex metadata.
- Removed the incorrect provider prefix assumption from docs and model-switch candidates.

## 2026-06-25 — add-gemini-context-wrong-slugs

- Added initial Gemini catalog entries, later corrected on 2026-06-26 because the slugs used the wrong `google/` prefix and version numbers.
- Updated install/model-switch scripts and skill docs for Gemini context handling.
- Kept the existing `ppio/pa/gpt-5.5` 258400 effective-context exception unchanged.

## 2026-06-21 — add-minimax-zhipuai-context

- Added `minimax/MiniMax-M3` and `zhipuai/glm-5.2` to the managed 1M context catalog.
- Updated install/model-switch scripts and skill docs so future catalog regeneration preserves both slugs at 950k effective context.
- Kept the existing `ppio/pa/gpt-5.5` 258400 effective-context exception unchanged.

## 2026-06-21 — ppio-context-258400-exception

- Kept `ppio/pa/gpt-5.5` at 272k catalog context / 258400 effective tokens because the PPIO relay rejects larger prompts.
- Preserved 1M catalog metadata for Xiaomi, Azure OpenAI, and DeepSeek slugs.
- Updated install and model-switch scripts so future runs do not accidentally raise PPIO back to 1M.

## 2026-06-20 — context-window-catalog-1m

- Added automatic `~/.codex/model_catalog.local.json` generation for Mify custom slugs.
- Ensured Codex config writes `model_catalog_json`, `model_context_window = 1000000`, and `model_auto_compact_token_limit = 850000`.
- Updated install/model-switch scripts and docs for `ppio`, `xiaomi`, `azure_openai`, and `deepseek` slugs with 950k effective context windows.
- Clarified that `Not supported model` can be provider support even when local Codex metadata is configured.
