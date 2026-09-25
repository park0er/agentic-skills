#!/usr/bin/env node
// ============================================================
//  tariq-html · validator
//  Enforces hard rules from SKILL.md:
//    1. Single file (just by being asked to validate one file)
//    2. No arbitrary CDNs (Tailwind / jsdelivr / unpkg / cdnjs / remote
//       <script> / <img>) — but Google Fonts (Mode B) and base64 inline
//       woff2 (Mode C) ARE allowed for typography only
//    2b. Every <img> inlined as a data: URI — no local/relative file refs,
//        so the single .html renders standalone when sent on its own
//    3. UTF-8 declared
//    4. CJK-safe font stack present, with Mode B or Mode C wired up
//       (no bare-system-Songti fallback — was Mode A, retired 2026-05-18)
//    5. <title> non-empty
//    6. At least one <section> or .slide
//    7. Responsive viewport meta
//
//  Usage:
//    node validate.mjs <file.html>
//    node validate.mjs <file.html> --json
//
//  Exit code 0 = pass, 1 = fail.
// ============================================================

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const args = process.argv.slice(2);
const fileArg = args.find(a => !a.startsWith('--'));
const asJson = args.includes('--json');

if (!fileArg) {
  console.error('Usage: node validate.mjs <file.html> [--json]');
  process.exit(2);
}

const filePath = resolve(fileArg);
let html;
try {
  html = readFileSync(filePath, 'utf8');
} catch (err) {
  console.error(`Could not read ${filePath}: ${err.message}`);
  process.exit(2);
}

const checks = [];
function check(name, ok, hint = '') {
  checks.push({ name, ok, hint });
}

// 1. UTF-8
check(
  'UTF-8 declared',
  /<meta\s+charset\s*=\s*["']?utf-8["']?/i.test(html),
  'Add <meta charset="utf-8"> in <head>.'
);

// 2. responsive viewport
check(
  'Responsive viewport meta',
  /<meta\s+name=["']viewport["']\s+content=["'][^"']*width\s*=\s*device-width/i.test(html),
  'Add <meta name="viewport" content="width=device-width, initial-scale=1">.'
);

// 3. <title> non-empty
const titleMatch = html.match(/<title>([^<]*)<\/title>/i);
check(
  '<title> set and non-empty',
  !!(titleMatch && titleMatch[1].trim() && !/^\[/.test(titleMatch[1].trim())),
  'Replace [PAGE_TITLE — ...] placeholder with the real title.'
);

// 4. no arbitrary CDNs — typography-only network (Google Fonts) is allowed,
// everything else is banned. This intentionally lets Mode B (Google Fonts)
// and Mode C (data:font/woff2;base64,...) pass while still blocking
// Tailwind-via-CDN, jsdelivr libraries, remote scripts, and remote images.
//
// Strip out the sanctioned-typography references first so they don't trip the
// remote-<link> generic check.
const htmlForCdnScan = html
  .replace(/<link\s[^>]*href\s*=\s*["']https?:\/\/fonts\.(?:googleapis|gstatic)\.com[^"']*["'][^>]*>/gi, '')
  .replace(/@import\s+(?:url\()?\s*["']?https?:\/\/fonts\.(?:googleapis|gstatic)\.com[^"')\s]*/gi, '');

const externalPatterns = [
  { re: /<link\s[^>]*href\s*=\s*["']https?:\/\//i, label: 'remote <link href="http..."> (only Google Fonts is allowed)' },
  { re: /<script\s[^>]*src\s*=\s*["']https?:\/\//i, label: 'remote <script src="http...">' },
  { re: /<img\s[^>]*src\s*=\s*["']https?:\/\//i, label: 'remote <img src="http..."> (use inline SVG or base64 data:)' },
  { re: /@import\s+(?:url\()?\s*["']?https?:\/\//i, label: '@import url("http...") (only Google Fonts is allowed)' },
  { re: /<link\s[^>]*href\s*=\s*["']\/\//i, label: 'protocol-relative <link href="//...">' },
  { re: /cdn\.jsdelivr\.net|unpkg\.com|cdnjs\.cloudflare\.com|cdn\.tailwindcss\.com/i, label: 'banned CDN (jsdelivr/unpkg/cdnjs/Tailwind)' },
];

const externalHits = externalPatterns.filter(p => p.re.test(htmlForCdnScan)).map(p => p.label);
check(
  'No arbitrary CDNs (Google Fonts permitted; data:font base64 permitted)',
  externalHits.length === 0,
  externalHits.length ? `Found: ${externalHits.join(', ')}` : ''
);

// 4b. every <img> must be self-contained — inlined as a data: URI (base64).
// A relative/local path (src="imgs/foo.png") renders on the author's machine
// but breaks the instant the .html is sent on its own — the whole point of the
// format is a single portable file. Remote http(s) images are already caught by
// check #4; this catches the local-path case that otherwise slips through.
// Allowed: data: URIs, and inline <svg> (which has no src attribute at all).
// Empty src="" is allowed: lightbox / lazy-load placeholders that JS fills at
// runtime with a data: URI carry no file dependency themselves.
const imgSrcs = [...html.matchAll(/<img\s[^>]*?\bsrc\s*=\s*["']([^"']*)["']/gi)].map(m => m[1]);
const nonInlineImgs = imgSrcs.filter(src => src.trim() !== '' && !/^data:/i.test(src.trim()));
check(
  'All <img> inlined as data: URI (no local/remote file refs)',
  nonInlineImgs.length === 0,
  nonInlineImgs.length
    ? `Found ${nonInlineImgs.length} non-inlined image(s), e.g. src="${nonInlineImgs[0].slice(0, 60)}". `
      + 'Embed every raster image as a base64 data: URI so the single .html renders standalone. '
      + 'Compress first (≤1500px wide, JPEG q≈82) to keep the file small. See SKILL.md § "Images must be inlined".'
    : ''
);

// 5. system font stack
const hasSystemFontStack =
  /(-apple-system|system-ui|BlinkMacSystemFont|"Helvetica Neue"|ui-serif|ui-sans-serif|"PingFang SC"|"Microsoft YaHei"|"Noto Sans SC"|"Noto Serif SC")/i.test(html);
check(
  'CJK-aware font stack present',
  hasSystemFontStack,
  'Use the font stack from references/design-tokens.md (must include "Noto Serif SC" / "Noto Sans SC" + CN fallback chain).'
);

// 5c. Mode B or Mode C wired up — bare-system-fallback (Mode A) is no longer
// supported because CN serif degraded to Songti SC on most user machines.
// PASS if EITHER Google Fonts <link> for Noto Serif SC / Noto Sans SC is present
// (Mode B) OR a base64 woff2 @font-face for the same families is present (Mode C).
const hasModeB =
  /<link\s[^>]*href\s*=\s*["']https?:\/\/fonts\.googleapis\.com\/css2?\?[^"']*family=Noto\+(?:Serif|Sans)\+SC/i.test(html);
const hasModeC =
  /@font-face\s*\{[^}]*font-family\s*:\s*["']Noto\s+(?:Serif|Sans)\s+SC["'][^}]*src\s*:\s*url\(\s*["']?data:font\/woff2;base64,/is.test(html);
check(
  'Font Mode B (Google Fonts) or Mode C (base64 inline) wired up',
  hasModeB || hasModeC,
  'Add either the 3-line Google Fonts <link> block (Mode B, default) or a base64 @font-face block (Mode C). See references/design-tokens.md § "Font strategy".'
);

// 5b. CJK fallback in mono stack — kami's lesson: any font-family that may
// render Chinese/Japanese must include a CJK fallback, mono especially. A pure
// `Menlo, Consolas, monospace` renders 中文注释 as tofu boxes on Windows.
const monoStacks = html.match(/font-family:\s*[^;]*?monospace[^;]*;/gi) || [];
const monoMissingCjk = monoStacks.filter(stack =>
  !/("PingFang SC"|"Source Han Sans SC"|"Source Han Serif SC"|"Microsoft YaHei"|"Noto Sans CJK"|"Noto Serif CJK"|"Songti SC"|"STSong"|"Hiragino")/i.test(stack)
);
check(
  'Mono font-family declarations include a CJK fallback',
  monoStacks.length === 0 || monoMissingCjk.length === 0,
  monoMissingCjk.length > 0
    ? `Add a CJK fallback (e.g. "PingFang SC", "Source Han Sans SC") before the final \`monospace\` keyword in: ${monoMissingCjk[0].slice(0, 120)}…  Pure mono stacks render 中文 as tofu on Windows.`
    : ''
);

// 6. at least one <section> or .slide
check(
  'Has at least one <section> or .slide',
  /<section[\s>]/i.test(html) || /class\s*=\s*["'][^"']*\bslide\b/i.test(html),
  'Wrap content in <section>...</section> blocks (or use .slide for deck branch).'
);

// 7. unfilled placeholders — soft warning (not a fail)
const placeholderCount = (html.match(/\[[A-Z][A-Z0-9_·· ]+(?:[—\-: ][^\]]*)?\]/g) || []).length;
const placeholderWarn = placeholderCount > 0;

// ── output ──
const allOk = checks.every(c => c.ok);
const exitCode = allOk ? 0 : 1;

if (asJson) {
  console.log(JSON.stringify({
    file: filePath,
    pass: allOk,
    checks,
    warnings: placeholderWarn ? [`${placeholderCount} unfilled placeholders [LIKE_THIS] — fill before shipping.`] : [],
  }, null, 2));
} else {
  console.log(`\n  tariq-html validator · ${filePath}\n`);
  for (const c of checks) {
    const mark = c.ok ? '[32m✓[0m' : '[31m✗[0m';
    console.log(`  ${mark}  ${c.name}${c.ok ? '' : '\n      [33m→ ' + c.hint + '[0m'}`);
  }
  if (placeholderWarn) {
    console.log(`\n  [33m⚠  ${placeholderCount} unfilled placeholders [LIKE_THIS] — fill before shipping.[0m`);
  }
  console.log(`\n  ${allOk ? '[32mPASS[0m' : '[31mFAIL[0m'}\n`);
}

process.exit(exitCode);
