# Mify Pricing Portal Research

Date: 2026-05-11

## Scope

This note records the current state of the `https://llm.mioffice.cn/gatewayPrice`
pricing portal investigation. The goal is to find a practical way for
`mify-model-gateway` to answer pricing questions without requiring users to
manually copy pricing tables.

## Current Skill Factory State

- The installed skill at `~/.claude/skills/mify-model-gateway` matches the
  active development copy at
  `/Users/park0er/Documents/Coding/PLAYGROUND/Skill_Factory/skills/mify-model-gateway`.
- Per `FACTORY.md`, future changes should be made in Skill Factory first, then
  released by archiving the installed stable copy before replacement.
- The current installed/factory skill does not include the earlier pricing
  patch. The earlier experimental patch still exists at:
  `/Users/park0er/multica_workspaces_desktop-api.multica.ai/7f97e6b9-2db3-489c-a270-4e4c6d354469/7f0a3930/workdir/patch`.

## Verified Interface Behavior

### OpenAI-compatible Mify gateway

`https://api.llm.mioffice.cn/v1/models` remains an availability catalog only.
With a valid local Mify key, `kimi-k2.5` currently returns rows like:

```json
[
  {"id": "kimi-k2.5", "owned_by": "xiaomi", "model_type": "llm"},
  {"id": "kimi-k2.5", "owned_by": "tongyi", "model_type": "llm"},
  {"id": "kimi-k2.5", "owned_by": "moonshot", "model_type": "llm"},
  {"id": "Pro/moonshotai/Kimi-K2.5", "owned_by": "siliconflow", "model_type": "llm"}
]
```

No pricing fields are included. Adding `?include=pricing` still returns the same
model-list schema.

Pricing-looking API paths under `api.llm.mioffice.cn` still do not exist:

- `/v1/pricing`
- `/v1/models/pricing`
- `/v1/usage/pricing`
- `/v1/billing/pricing`
- `/v1/model/pricing`
- `/v1/gateway/pricing`

Observed behavior: OpenAI-compatible paths return `400` with `404 NOT_FOUND`;
non-API paths return openresty `404`.

### Portal host

Unauthenticated requests to `https://llm.mioffice.cn/gatewayPrice` return `302`
to CAS:

```text
location: https://cas.mioffice.cn/login?service=https%3A%2F%2Fp.dun.mioffice.cn%2Fcas%2Fsts%3Ffollowup%3Dhttps%253A%252F%252Fllm.mioffice.cn%252FgatewayPrice...
```

The same CAS gate applies to tested candidate paths under `llm.mioffice.cn`,
including:

- `/api/price`
- `/api/pricing`
- `/api/gatewayPrice`
- `/api/gateway/price`
- `/api/v1/price`
- `/api/v1/pricing`
- `/open-api/price`
- `/open-api/pricing`
- `/v1/pricing`
- `/gateway/pricing`

This means endpoint discovery from unauthenticated curl is not enough; the
portal API must be observed inside an authenticated browser session.

## Browser Session Findings

The user's Chrome session can reach the portal: after opening
`https://llm.mioffice.cn/gatewayPrice`, Chrome reports:

```text
URL: https://llm.mioffice.cn/gatewayPrice
title: 大模型 API 开放平台
```

This confirms the normal Chrome profile has a valid CAS session for the portal.

However, the current Codex run could not use the intended browser-control path:

- The Chrome plugin's direct browser-client bootstrap failed with:
  `privileged native pipe bridge is not available; browser-client is not trusted`.
- Computer Use timed out while trying to read Chrome state.
- AppleScript can read the tab URL/title, but Chrome blocks page JavaScript from
  AppleScript unless the user enables:
  `View > Developer > Allow JavaScript from Apple Events`.

Because page JavaScript execution is disabled, this run could not extract the
logged-in page's `performance.getEntriesByType("resource")` list or fetch the
actual pricing XHR response body.

## Feasibility Assessment

### Best path: capture XHR response, not cookies

The cleanest design is to observe the logged-in page's network response and
cache the pricing payload locally. This avoids storing or exporting CAS cookies.

Expected flow:

1. User opens `https://llm.mioffice.cn/gatewayPrice` in their normal Chrome
   profile.
2. Skill asks the browser automation layer for resource/network entries.
3. Skill identifies the pricing XHR by URL and response shape.
4. Skill reads that response body, normalizes it, and writes a date-stamped
   cache such as `~/.cache/mify-model-gateway/pricing-YYYY-MM-DD.json`.
5. `fetch_pricing.py` answers later queries from cache unless refresh is
   requested.

This is better than cookie extraction because the skill never handles session
cookies directly.

### Acceptable fallback: user-supplied HAR or copied XHR response

If browser automation is unavailable, a practical fallback is:

1. User opens DevTools Network on `gatewayPrice`.
2. User refreshes the page.
3. User exports a HAR or copies the pricing XHR response.
4. A script imports the response into the same cache schema.

This is less automatic but keeps credentials out of the skill.

### Possible but heavier: Chrome extension

A dedicated Chrome extension can read HttpOnly CAS cookies if it has:

```json
{
  "permissions": ["cookies"],
  "host_permissions": ["https://llm.mioffice.cn/*"]
}
```

It could then either fetch the pricing API itself or pass the cookie to a native
helper.

This is technically possible, but distribution is the problem:

- Web Store: user must install and Google review is required.
- Enterprise policy: can be force-installed, but requires Xiaomi IT/admin
  rollout.
- Developer mode unpacked extension: user must manually enable developer mode
  and load/reload the extension.

So an extension is viable only if the team accepts explicit installation or IT
distribution. It is not something a skill can silently install for everyone.

### Avoid: direct cookie-store scraping

Reading Chrome's Cookies database or profile session stores is not a good skill
design. It is brittle, over-privileged, and violates the safer boundary of
"observe a response the browser already received" instead of extracting a login
secret.

## Proposed Implementation Shape

When the actual pricing XHR URL and response schema are known, add pricing as a
separate staged capability:

```text
scripts/fetch_pricing.py
  --source auto
  --source cache
  --source har
  --source browser
  --grep <model>
  --owner <owner>
  --type <model_type>
  --json
```

Recommended source order:

1. Fresh local cache.
2. Browser response capture, when a supported browser bridge is available.
3. HAR/import file.
4. Bundled snapshot only if the team intentionally ships one.

Do not add pricing data to the installed stable skill until the portal response
schema is verified.

## Next Required Evidence

One of these is needed before implementing the parser:

1. Enable Chrome `View > Developer > Allow JavaScript from Apple Events`, then
   run a read-only page-context script to list `performance` resource URLs and
   fetch the pricing XHR response.
2. Use the Codex Chrome plugin in an environment where the native bridge is
   trusted, then capture the Network response from the `gatewayPrice` tab.
3. Manually export a HAR from DevTools Network after refreshing
   `gatewayPrice`.

The needed artifact is only:

- pricing XHR URL
- HTTP method
- request query/body shape, if any
- response JSON shape, with sensitive cookies excluded

