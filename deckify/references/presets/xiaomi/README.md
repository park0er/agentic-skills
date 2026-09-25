# presets/xiaomi — Xiaomi brand preset

Frozen output bundle from a previous deckify run on `https://www.mi.com/global/`. Drop this in when the user wants a Xiaomi-style deck and you want to skip Phase 1 / Phase 2 recon entirely.

## When to use

The user asks for "a Xiaomi-style deck", "按小米官网调性出 deck", "小米风 PPT", or otherwise names Xiaomi as the brand reference. Instead of running the 6-phase recon pipeline, hand the downstream slide-builder agent the artifacts in this directory and tell it: **"Build the deck from `xiaomi-PPT-Design-System.md`. The §ENGINEERING-DNA chapters are non-negotiable; §BRAND-VARIABLE is locked to Xiaomi values — do not retune."**

## What's in here

| File | Size | Role |
|------|------|------|
| `xiaomi-PPT-Design-System.md` | 70 KB | DS contract (中文版). The whole Xiaomi recipe — palette, typography, logo embed, slide-type emphasis, §ENGINEERING-DNA verbatim from `references/ds-template.md`. This is what you feed the builder. |
| `xiaomi-deck.html` | 115 KB | 9-slide verification deck rendered against the DS above. Visual proof that the DS spec works; also a copy-paste source for slide skeletons. |
| `source/brand.json` | 4.4 KB | LLM-synthesized brand recon: palette, typography, logo, mood. Phase 1e output. |
| `source/decisions.json` | 1.3 KB | Phase 2 decision snapshot — language=zh, MiSans Latin via Xiaomi CDN, slide-emphasis Type A/F/H/J. |
| `source/pages.txt` | 0.8 KB | The 7 mi.com subpages used as the recon corpus. |
| `source/assets/logo.svg` / `.png` / `.dataurl` / `.embed.html` / `.report.json` | ~17 KB | Logo in 5 forms. `logo.embed.html` is the inline `<symbol viewBox="0 0 112 112">` snippet — drop straight into a deck `<svg>` `<defs>`. |

## Locked brand values (do not retune downstream)

| Token | Value |
|-------|-------|
| `--brand-primary` | `#FF6700` (xiaomi-orange — single accent, 6 pages × 24 occurrences) |
| `--ink` / display | `#191919` |
| `--paper` | `#FFFFFF` |
| `--stage` | `#000000` (cinematic photography backgrounds) |
| `--link` | `#1D4ED8` |
| Display + body font | `MiSans Latin` via `https://i02.appmifile.com/i18n/fonts/MiSansLatin/index.css` |
| CJK fallback chain | `-apple-system → BlinkMacSystemFont → 'Helvetica Neue' → 'PingFang SC' → 'Microsoft YaHei' → sans-serif` |
| Slide-type emphasis | Type A (cinematic cover) → F (image+specs) → H (data table) → J (poster) |
| Mood | "engineered cinematic confidence" |
| License notice | The logo PNG/SVG and brand colours are Xiaomi property. Internal-use only. |

## How the builder agent should call this

1. Read `xiaomi-PPT-Design-System.md` end-to-end — that is the contract.
2. For the logo, paste `source/assets/logo.embed.html` into the deck's `<svg>` `<defs>` (preferred) or use the data URL in `source/assets/logo.dataurl`. **Never** restyle the logo with CSS `fill:` — it is a two-tone glyph and `currentColor` will collapse it.
3. Match deck structure to the slide-emphasis order in `source/decisions.json`.
4. Run the standard deckify hard-checks (`evals/hard_checks.py`) on the produced deck before declaring done.

## How this bundle was produced

This is the verbatim output of one full deckify Phase 1–6 run on `https://www.mi.com/global/` (with `pages.txt` covering 7 representative subpages). It is shipped here so future "Xiaomi deck" requests can skip Phase 1 / 2 / 3 — saving a network round-trip + a confirmation round + a DS write.

## Refreshing this preset

To regenerate, run deckify from scratch on `https://www.mi.com/global/`, copy the resulting `~/deckify/decks/xiaomi/` and recon JSON back into this directory, and bump the deckify CHANGELOG. Do **not** hand-edit the markdown or HTML to stay in sync — re-run the pipeline.
