# CLI reference (`scripts/image_gen.py`)

This file is for the Mify CLI mode. Read it when using `scripts/image_gen.py` / CLI / API / model controls through Mify `azure_openai/gpt-image-2`.

`generate-batch` is a CLI subcommand in this Mify path. The word `batch` in a user request is enough to use it when many distinct Mify image jobs are requested.

## What this CLI does
- `generate`: generate a new image from a prompt
- `edit`: edit one or more existing images
- `generate-batch`: run many generation jobs from a JSONL file

Real API calls require **network access** + a Mify token from `MIFY_IMAGE_API_KEY`, `MIFY_API_KEY`, or `~/.config/mify/credentials`. `--dry-run` does not.

## Quick start (works from any repo)
Set a stable path to the installed skill CLI:

```
export IMAGE_GEN="${HOME}/.agents/skills/mify-imagegen/scripts/image_gen.py"
```

The CLI uses Python stdlib HTTP and does not require the OpenAI Python SDK. Pillow is optional for downscaling and local chroma-key removal.

## Quick start

Dry-run (no API call; no network required; does not require a token):

```bash
python "$IMAGE_GEN" generate \
  --prompt "Test" \
  --out output/imagegen/test.png \
  --dry-run
```

Notes:
- One-off dry-runs print the API payload and the computed output path(s).
- Repo-local finals should live under `output/imagegen/`.

Generate (requires Mify token + network):

```bash
python "$IMAGE_GEN" generate \
  --prompt "A cozy alpine cabin at dawn" \
  --size 1024x1024 \
  --out output/imagegen/alpine-cabin.png
```

Edit:

```bash
python "$IMAGE_GEN" edit \
  --image input.png \
  --prompt "Replace only the background with a warm sunset" \
  --out output/imagegen/sunset-edit.png
```

## Guardrails
- Use the bundled CLI directly (`python "$IMAGE_GEN" ...`) after activating the correct environment.
- Do **not** create one-off runners (for example `gen_images.py`) unless the user explicitly asks for a custom wrapper.
- **Never modify** `scripts/image_gen.py`. If something is missing, ask the user before doing anything else.
- Do not silently leave Mify `gpt-image-2` for a different tool, provider, or model; ask first unless the user explicitly requested that different path.

## Defaults
- Model: `gpt-image-2`
- Supported model for this CLI: `gpt-image-2` through Mify provider `azure_openai`
- Size: `auto`
- Quality: `medium`
- Output format: `png`
- Default one-off output path: `output/imagegen/output.png`
- Background: unspecified unless `--background` is set

## gpt-image-2 size and model guidance

`gpt-image-2` is the default model for new CLI fallback work.

- Use `--quality low` for fast drafts, thumbnails, and quick iterations.
- Use `--quality medium`, `--quality high`, or `--quality auto` for final assets, dense text, diagrams, identity-sensitive edits, and high-resolution outputs.
- Square images are typically fastest. Use `--size 1024x1024` for quick square drafts.
- If the user asks for 4K-style output, use `--size 3840x2160` for landscape or `--size 2160x3840` for portrait.
- Do not pass `--input-fidelity` with `gpt-image-2`; this model always uses high fidelity for image inputs.
- Do not use `--background transparent` with Mify `gpt-image-2`; the default transparent-image workflow uses a flat chroma-key background plus local removal. Ask before using any different tool or model for true native transparency.

Popular `gpt-image-2` sizes:
- `1024x1024`
- `1536x1024`
- `1024x1536`
- `2048x2048`
- `2048x1152`
- `3840x2160`
- `2160x3840`
- `auto`

`gpt-image-2` size constraints:
- max edge `<= 3840px`
- both edges multiples of `16px`
- long edge to short edge ratio `<= 3:1`
- total pixels between `655,360` and `8,294,400`
- outputs above `2560x1440` total pixels are experimental

Fast draft:

```bash
python "$IMAGE_GEN" generate \
  --prompt "A product thumbnail of a matte ceramic mug on a stone surface" \
  --quality low \
  --size 1024x1024 \
  --out output/imagegen/mug-draft.png
```

Final 2K landscape:

```bash
python "$IMAGE_GEN" generate \
  --prompt "A polished landing-page hero image of a matte ceramic mug on a stone surface" \
  --quality high \
  --size 2048x1152 \
  --out output/imagegen/mug-hero.png
```

4K landscape:

```bash
python "$IMAGE_GEN" generate \
  --prompt "A detailed architectural visualization at golden hour" \
  --size 3840x2160 \
  --quality high \
  --out output/imagegen/architecture-4k.png
```

Transparent cutout source request:

Use Mify `gpt-image-2` to make a removable chroma-key source first.

```bash
python "$IMAGE_GEN" generate \
  --prompt "A clean product cutout centered on a perfectly flat solid #00ff00 chroma-key background; no shadows, no reflection, no texture, no watermark" \
  --output-format png \
  --out tmp/imagegen/product-cutout-source.png
```

Then remove the background with `scripts/remove_chroma_key.py`. If the request needs true native transparency, explain that the documented Mify `gpt-image-2` path does not expose native `background=transparent`, and ask before using another tool or model.

## Quality and masks (Mify CLI only)
These are explicit CLI controls. They are not built-in `image_gen` tool arguments.

- `--quality` works for `generate`, `edit`, and `generate-batch`: `low|medium|high|auto`
- `--input-fidelity` is rejected for Mify `gpt-image-2`; image inputs use high fidelity.
- `--mask` is **edit-only** and is sent as `mask_url` on a best-effort basis because the Feishu sample documents `image_url`, not masks.

Example:

```bash
python "$IMAGE_GEN" edit \
  --image input.png \
  --prompt "Change only the background" \
  --quality high \
  --out output/imagegen/background-edit.png
```

Mask notes:
- For multi-image edits, pass repeated `--image` flags. Their order is meaningful, so describe each image by index and role in the prompt.
- The CLI accepts a single `--mask`.
- Image and mask must be the same size and format and each under 50MB.
- Masks must include an alpha channel.
- If multiple input images are provided, the mask applies to the first image.
- Masking is prompt-guided; do not promise exact pixel-perfect mask boundaries.
- Use a PNG mask when possible; the script treats mask handling as best-effort and does not perform full preflight validation beyond file checks/warnings.
- In the edit prompt, repeat invariants (`change only the background; keep the subject unchanged`) to reduce drift.

## Output handling
- Use `tmp/imagegen/` for temporary JSONL inputs or scratch files.
- Use `output/imagegen/` for final outputs.
- Reruns fail if a target file already exists unless you pass `--force`.
- `--out-dir` changes one-off naming to `image_1.<ext>`, `image_2.<ext>`, and so on.
- Downscaled copies use the default suffix `-web` unless you override it.

## Common recipes

Generate with augmentation fields:

```bash
python "$IMAGE_GEN" generate \
  --prompt "A minimal hero image of a ceramic coffee mug" \
  --use-case "product-mockup" \
  --style "clean product photography" \
  --composition "wide product shot with usable negative space for page copy" \
  --constraints "no logos, no text" \
  --out output/imagegen/mug-hero.png
```

Generate + also write a downscaled copy for fast web loading:

```bash
python "$IMAGE_GEN" generate \
  --prompt "A cozy alpine cabin at dawn" \
  --size 1024x1024 \
  --downscale-max-dim 1024 \
  --out output/imagegen/alpine-cabin.png
```

Generate multiple prompts concurrently (async batch):

```bash
mkdir -p tmp/imagegen output/imagegen/batch
cat > tmp/imagegen/prompts.jsonl << 'EOF'
{"prompt":"Cavernous hangar interior with a compact shuttle parked near the center","use_case":"stylized-concept","composition":"wide-angle, low-angle","lighting":"volumetric light rays through drifting fog","constraints":"no logos or trademarks; no watermark","size":"1536x1024"}
{"prompt":"Gray wolf in profile in a snowy forest","use_case":"photorealistic-natural","composition":"eye-level","constraints":"no logos or trademarks; no watermark","size":"1024x1024"}
EOF

python "$IMAGE_GEN" generate-batch \
  --input tmp/imagegen/prompts.jsonl \
  --out-dir output/imagegen/batch \
  --concurrency 5

rm -f tmp/imagegen/prompts.jsonl
```

Notes:
- `generate-batch` requires `--out-dir`.
- generate-batch requires --out-dir.
- Use `--concurrency` to control parallelism (default `5`).
- Per-job overrides are supported in JSONL (for example `size`, `quality`, `background`, `output_format`, `output_compression`, `moderation`, `n`, `model`, `out`, and prompt-augmentation fields).
- `--n` generates multiple variants for a single prompt; `generate-batch` is for many different prompts.
- In batch mode, per-job `out` is treated as a filename under `--out-dir`.
- For many requested deliverable assets, provide one prompt/job per distinct asset and use semantic filenames when possible.

## CLI notes
- Mify `gpt-image-2` supports flexible constrained sizes.
- True native transparent CLI outputs are not exposed by the documented Mify `gpt-image-2` path; use chroma-key removal first and ask before switching tools/models.
- `--prompt-file`, `--output-compression`, `--moderation`, `--max-attempts`, `--fail-fast`, `--force`, and `--no-augment` are supported.
- This CLI is intended for Mify `azure_openai/gpt-image-2`. Do not assume older non-GPT image-model behavior applies here.

## See also
- API parameter quick reference for Mify CLI mode: `references/image-api.md`
- Feishu-sourced Mify request contract: `references/mify-image-api.md`
- Prompt examples shared across both top-level modes: `references/sample-prompts.md`
- Network/token notes for Mify CLI mode: `references/codex-network.md`
- Mify-first transparent image workflow: `SKILL.md` and `${HOME}/.agents/skills/mify-imagegen/scripts/remove_chroma_key.py`
