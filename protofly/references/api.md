# proto-fly MCP API Reference

5 tools exposed by `https://protofly-mcp.v.mitvos.com/mcp`. All examples below
use mcporter (`mcporter call protofly.<tool>`); the JSON shapes are the same
whether you call via mcporter, MCP-native client, or anywhere else.

Discover the live schema any time with:

```bash
mcporter list protofly --schema
```

---

## `create_resource`

Upload an HTML file. Either creates a brand-new resource (if `resource_id`
omitted) or appends a new draft version to an existing one.

**Why `--args <json>`, not `key:value`**: `file_content` is base64 of the
HTML, often hundreds of KB. Long base64 strings in shell args get split on
`+` / `=` boundaries by zsh/bash and the server returns
`file_content is required`. Always route this call through `upload.py` (uses
`--args` internally).

**Input**

| field | type | req | notes |
|---|---|---|---|
| `filename` | string | ✓ | basename, e.g. `weekly_report_v3.html` |
| `file_content` | string (base64) | ✓ | contents of the HTML file, base64-encoded |
| `description` | string | — | only used on first create, ignored on update |
| `resource_id` | string | — | provide to append a new draft version |

**Output (new resource)**

```json
{
  "resource_id": "PF26051800580010BD05",
  "version": 1,
  "status": 10,
  "preview_url": "https://protofly.v.mitvos.com/preview/PF26051800580010BD05"
}
```

**Output (existing resource)**

Same shape, but `version` is incremented.

**Status codes**: `10` = draft, `20` = published.

---

## `list_resources`

Paginated list of resources owned by the calling user.

**Input**

| field | type | req | notes |
|---|---|---|---|
| `page` | int | — | 1-indexed, default 1 |
| `page_size` | int | — | default 20 |

**Output**

```json
{
  "items": [
    {
      "resource_id": "PF26042712430010BD05",
      "fname": "V6_演示材料.html",
      "description": "...",
      "current_version": 4,
      "published_version": 4,
      "status": 20,
      "visibility": 20,
      "preview_url": "https://protofly.v.mitvos.com/preview/PF26042712430010BD05",
      "created_at": "2026-04-27T12:43:21Z",
      "updated_at": "2026-04-27T15:52:35Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 5
}
```

**Numeric enums**: `status: 10` = draft, `20` = published. `visibility: 10`
= private, `20` = public. (See note in `set_visibility` about the API
returning strings vs ints inconsistently.)

---

## `get_resource`

Resource detail with full version history.

**Input**

| field | type | req | notes |
|---|---|---|---|
| `resource_id` | string | ✓ | `PF`-prefixed id |

**Output**

```json
{
  "resource_id": "PF26051800580010BD05",
  "fname": "protofly_skill_smoke.html",
  "description": "...",
  "current_version": 2,
  "visibility": 10,
  "versions": [
    {"version": 2, "status": 20, "size": 0.4, "created_at": "2026-05-18T01:00:35Z"},
    {"version": 1, "status": 20, "size": 0.4, "created_at": "2026-05-18T00:58:45Z"}
  ]
}
```

`size` is in MB (so 0.4 = 400 KB-ish — the field is a float, not an int).

---

## `publish_resource`

Mark a draft version as published. Once published, the `view` URL serves it
to authorized users; before publishing, only `preview` works (owner only).

**Input**

| field | type | req | notes |
|---|---|---|---|
| `resource_id` | string | ✓ | |
| `version` | int | — | defaults to the latest draft |

**Output**

```json
{
  "resource_id": "PF26051800580010BD05",
  "published_version": 1,
  "published_url": "https://protofly.v.mitvos.com/view/PF26051800580010BD05"
}
```

The `view` URL is stable across versions — same URL always serves whichever
version is currently published.

---

## `set_visibility`

Switch resource between authorized-only and link-shareable.

**Input**

| field | type | req | notes |
|---|---|---|---|
| `resource_id` | string | ✓ | |
| `visibility` | enum | ✓ | `"private"` or `"public"` |

**Output**

```json
{
  "resource_id": "PF26051800580010BD05",
  "visibility": "public"
}
```

**Inconsistency to know about**: `set_visibility` echoes `visibility` as a
**string** (`"public"` / `"private"`), but `get_resource` and
`list_resources` return it as an **integer** (10 = private, 20 = public).
Same semantic, different wire format. Both helper scripts treat the field
opaquely so this doesn't trip anything up — but if you parse responses by
hand, expect both shapes.

---

## URL conventions

| URL | Who can see | Stable across versions? |
|---|---|---|
| `https://protofly.v.mitvos.com/preview/<rid>` | owner only (always — even when private→public) | yes — always points to the latest draft |
| `https://protofly.v.mitvos.com/view/<rid>` | depends on `visibility` (private = authorized list; public = anyone with the link, still inside Xiaomi internal network) | yes — always points to the latest published version |

---

## Error cases worth recognizing

| Symptom | Cause | Fix |
|---|---|---|
| `file_content is required` after passing it | shell split a long base64 string | use `upload.py` (or call with `--args <json>`) |
| HTTP 401 from mcporter | token expired or revoked | `status.py` to confirm; reinstall via `install_token.py` |
| `Cannot reach https://protofly-mcp.v.mitvos.com` | not on Xiaomi VPN / internal network | reconnect, retry |
| `forbidden` on `view` link from another user | resource is `private` and they're not authorized | either add them in protofly web console or `set_visibility public` if user explicitly OK with that |
