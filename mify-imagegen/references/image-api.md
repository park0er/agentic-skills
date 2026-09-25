# Mify Image API quick reference

This file is for the Mify CLI mode. Use it when working with `scripts/image_gen.py` / CLI / API / model controls through Mify `azure_openai/gpt-image-2`.

These parameters describe the Mify image API and bundled CLI surface. Do not assume they are normal arguments on the built-in `image_gen` tool.

## Scope
- This Mify CLI is intended for Mify provider `azure_openai` model `gpt-image-2`.
- The built-in `image_gen` tool and the Mify CLI do not expose the same controls.

## Model summary

| Model | Quality | Input fidelity | Resolutions | Recommended use |
| --- | --- | --- | --- | --- |
| `gpt-image-2` | `low`, `medium`, `high`, `auto` | Always high fidelity for image inputs; do not set `input_fidelity` | `auto` or flexible sizes that satisfy the constraints below | Default for new CLI/API workflows: high-quality generation and editing, text-heavy images, photorealism, compositing, identity-sensitive edits, and workflows where fewer retries matter |

## gpt-image-2 sizes

`gpt-image-2` accepts `auto` or any `WIDTHxHEIGHT` size that satisfies all constraints:

- Maximum edge length must be less than or equal to `3840px`.
- Both edges must be multiples of `16px`.
- Long edge to short edge ratio must not exceed `3:1`.
- Total pixels must be at least `655,360` and no more than `8,294,400`.

Popular sizes:

| Label | Size | Notes |
| --- | --- | --- |
| Square | `1024x1024` | Typical fast default |
| Landscape | `1536x1024` | Standard landscape |
| Portrait | `1024x1536` | Standard portrait |
| 2K square | `2048x2048` | Larger square output |
| 2K landscape | `2048x1152` | Widescreen output |
| 4K landscape | `3840x2160` | Widescreen 4K output |
| 4K portrait | `2160x3840` | Vertical 4K output |
| Auto | `auto` | Default size |

Square images are typically fastest to generate. For 4K-style output, use `3840x2160` or `2160x3840`.

## Endpoints
- Generate: `POST http://model.mify.ai.srv/v1/images/generations`
- Edit: `POST http://model.mify.ai.srv/v1/images/edits`
- Required provider header: `X-Model-Provider-Id: azure_openai`

## Core parameters for GPT Image models
- `prompt`: text prompt
- `model`: `gpt-image-2`
- `n`: number of images (1-10)
- `size`: `auto` by default for `gpt-image-2`; flexible `WIDTHxHEIGHT` sizes are allowed if they satisfy the constraints above
- `quality`: `low`, `medium`, `high`, or `auto`
- `background`: output background behavior (`opaque` or `auto`) for generated output; this is not the same thing as the prompt's visual scene/backdrop
- `output_format`: `png` (default), `jpeg`, `webp`
- `output_compression`: 0-100 (jpeg/webp only)
- `moderation`: `auto` (default) or `low`

## Edit-specific parameters
- `image_url`: one local image encoded as a data URL, or multiple data URLs as a list.
- `mask_url`: optional mask data URL, best-effort. The Feishu sample documents `image_url`, not masks.
- `input_fidelity`: do not set this for Mify `gpt-image-2`

Model-specific note for `input_fidelity`:
- `gpt-image-2` always uses high fidelity for image inputs and does not support setting `input_fidelity`.

## Transparent backgrounds

Mify `gpt-image-2` does not expose the Image API `background=transparent` parameter in this skill. The skill's default transparent-image path is Mify `gpt-image-2` with a flat chroma-key background, followed by local alpha extraction with `python "${HOME}/.agents/skills/mify-imagegen/scripts/remove_chroma_key.py"`.

Use a different tool or model for native transparent output only after the user explicitly confirms that fallback. If the user asks for true/native transparency, the subject is too complex for clean chroma-key removal, or local background removal fails validation, explain the tradeoff and ask before switching.

## Output
- `data[]` list with `b64_json` per image
- The bundled `scripts/image_gen.py` CLI writes either `b64_json` image data or downloaded `url` responses for you.

## Limits and notes
- Input images and masks must be under 50MB.
- Use the edits endpoint when the user requests changes to an existing image.
- Masking is prompt-guided; exact shapes are not guaranteed.
- Large sizes and high quality increase latency and cost.
- Use `quality=low` for fast drafts, thumbnails, and quick iterations. Use `medium` or `high` for final assets, dense text, diagrams, identity-sensitive edits, or high-resolution outputs.
- If a request fails because a specific option is unsupported by Mify `gpt-image-2`, retry manually without that option only when the option is not required by the user. If true transparent output is required, ask before switching tools/models instead of silently dropping the requirement.

## Important boundary
- `quality`, explicit masks, `background`, `output_format`, and related parameters are Mify CLI execution controls.
- Do not assume they are built-in `image_gen` tool arguments.
