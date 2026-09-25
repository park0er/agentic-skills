# mify-imagegen CHANGELOG

## 2026-05-21 — restore-official-workflow-depth

- Restored the official imagegen skill's full workflow detail, decision tree, prompt taxonomy, transparent-image guidance, gpt-image-2 notes, and reference-document depth.
- Re-expanded `references/cli.md`, `references/image-api.md`, `references/prompting.md`, and `references/sample-prompts.md` from the official source, with only Mify-specific transport/token/tool substitutions.
- Kept the Mify-specific implementation path: `azure_openai/gpt-image-2` through `http://model.mify.ai.srv/v1/images/generations` and `/images/edits`.
- Migration note: this release intentionally fixes the previous lightweight fork, which was functional but not a full-fidelity replica of the official imagegen workflow.

## 2026-05-20 — initial-mify-image-2

- Created an independent Mify-routed image generation skill based on the official imagegen skill.
- Changed the CLI transport to Mify `azure_openai/gpt-image-2` using the Feishu-documented `/v1/images/generations` and `/v1/images/edits` endpoints.
- Token lookup uses `MIFY_IMAGE_API_KEY`, `MIFY_API_KEY`, or `~/.config/mify/credentials`; the OpenAI SDK and `OPENAI_API_KEY` are not required.
- Transparent images use the chroma-key plus local alpha-removal workflow; no native transparent fallback model is configured in this skill.
