# Data Contract Reference

How the generated interview app stores answers, what protects them from loss, and what file formats it produces. This contract is implemented inside `templates/interview-app.html` — do not modify the JS that implements it.

For the visual / interactive version of this document, open `README.html` in a browser.

## The 4 storage layers

Same pattern as the V2 architecture diagram in `README.html`:

| Layer | Where | What | Role |
|---|---|---|---|
| **L1** | Browser localStorage<br>key: `<storage-key>` | All answers, skipped state, current_index, last_saved | **Primary store · single source of truth** — every save writes here |
| **L2** | Local disk JSON file<br>`~/Downloads/<storage-key>-backup-<timestamp>.json` | Snapshot of L1 at export time | **Backup · disaster recovery** — user-controlled, explicit |
| **L3** | JS memory (`state` variable) | Current session's reactive state | **Runtime buffer** — flushed to L1 on every change |
| **L4** | `<script id="schema">` inside the HTML | Question schema (topics, questions, kinds) | **Read-only structure** — does NOT contain answers |

L4 is just the question definitions baked into the file at generation time. L1 is what carries the user's actual answers.

## L1 schema (localStorage value)

Stored as a JSON-stringified object under the configured `STORAGE_KEY`. Schema version 1:

```json
{
  "answers": {
    "<question-id>": {
      "text": "user's answer",
      "saved_at": "2026-05-18T..."
    }
  },
  "skipped": {
    "<question-id>": true
  },
  "current_index": 5,
  "last_saved": "2026-05-18T...",
  "schema_version": 1,
  "created": "2026-05-18T..."
}
```

Empty answer text → entry deleted from `answers` (so an answered-then-cleared question becomes "not answered" again, not "answered with empty string"). Skipping a question without typing → entry added to `skipped`. Typing into a skipped question un-skips it automatically.

## Save trigger redundancy (5 paths)

Critical user requirement: data must not be lost. The template implements 5 redundant save triggers. Removing any one weakens the contract:

| # | Event | When it fires | Why |
|---|---|---|---|
| 1 | `input` (debounced 200ms) | Every keystroke into `<textarea>` | Most frequent path. 200ms debounce avoids per-keystroke disk thrash. |
| 2 | `blur` (immediate) | textarea loses focus | Last-mile save before user clicks elsewhere; bypasses debounce. |
| 3 | navigation (immediate, twice) | Click 上一题 / 跳过 / 下一题 | Saves before AND after switching `current_index` to prevent torn state. |
| 4 | `beforeunload` | Tab close, browser quit, URL change | Last chance the browser gives JS to persist data. |
| 5 | `visibilitychange` | Page becomes hidden (tab switch, minimize, app switch) | Earlier than `beforeunload`; especially important on mobile (iOS often skips beforeunload). |

The save function is idempotent — calling it 5 times in sequence is fine, just costs ~5 setItem operations.

## Save state UI

The header has a `<span class="save-state">` indicator with three states:

- **`saved`** (default, olive dot, "已保存 HH:MM:SS") — last save succeeded, idle
- **`saving`** (clay dot, "保存中…") — debounce timer running OR mid-write
- **`error`** (warn-red dot, "保存失败！") — `setItem` threw (quota exceeded, storage disabled, etc.); also surfaces a top banner instructing user to immediately export JSON

The pulse animation on the dot is intentional: subtly reassures the user that auto-save is alive.

## JSON export format (L2)

When user clicks "导出 JSON", the app writes:

```json
{
  "app": "interviewer",
  "storage_key": "<storage-key>",
  "schema_version": 1,
  "exported_at": "2026-05-18T...",
  "state": {
    "answers": { ... },
    "skipped": { ... },
    "current_index": 5,
    "last_saved": "...",
    "schema_version": 1
  }
}
```

Filename: `<storage-key>-backup-<ISO-timestamp>.json` (timestamp colons replaced with `-`).

The `app` and `schema_version` fields are sanity checks for import: the app warns if importing a file that doesn't claim to be from `interviewer` v1.

## JSON import behavior

When user clicks "导入 JSON":
1. File picker opens
2. Read file, JSON.parse
3. If `parsed.app !== 'interviewer' || parsed.schema_version !== 1` → confirm dialog: "this looks like a different format, continue?"
4. Merge incoming `state.answers` and `state.skipped` into current state — **incoming wins** for collisions, but existing answers not in the import are preserved
5. Apply `current_index` from incoming if numeric
6. saveStateNow() to flush merged state to L1
7. Re-render
8. Toast: "导入成功，数据已合并"

Merge strategy is "additive last-write-wins": you can interview on Mac A, export, import on Mac B, answer more questions, and you don't lose any answers from either device.

## Reset behavior

The "重置" button is destructive but archive-first:

1. Confirm dialog #1: "建议先点'导出 JSON'备份"
2. Confirm dialog #2: "这会删除你所有已输入的内容，不可恢复"
3. **Before wiping**: `localStorage.setItem(STORAGE_KEY + '-archive-' + Date.now(), <current state>)` — the old data lives forever in a separate, timestamped key. Recoverable via DevTools → Application → Local Storage if needed.
4. State reset to `defaultState()`
5. saveStateNow() to flush empty state
6. Re-render
7. Toast (warn): "已重置。旧数据已归档为 -archive-* 备份键"

This is intentionally not user-facing: power users can hand-recover from DevTools, but the typical user flow doesn't expose it. The archive key naming makes it discoverable.

## Schema version migration

If a future version of this skill bumps the schema version (e.g., adds a new field to `state`), the loadState() function:

1. Reads the stored JSON
2. If `parsed.schema_version !== <expected>` → archives old data to `<STORAGE_KEY>-legacy-<timestamp>` (separate from -archive-*) and falls back to defaultState()
3. Logs the legacy archive key so a tech-savvy user can manually port

This means **schema bumps never silently destroy data**. They quarantine it in a sibling key and start fresh.

## Failure modes & mitigations

| Scenario | Data loss? | Mitigation |
|---|---|---|
| Browser crashes mid-typing | ✓ No (the last completed 200ms cycle is saved) | input debounce + blur fallback |
| Power loss | ✓ No | localStorage.setItem is synchronous on disk |
| Tab close / browser quit | ✓ No | beforeunload + visibilitychange |
| localStorage quota exceeded | ⚠️ Latest write lost | Red banner + red save indicator → user manually exports JSON |
| User clicks Reset by accident | ✓ Recoverable from DevTools | 2× confirm + auto-archive to `-archive-*` key |
| Schema version mismatch | ✓ Old data archived to `-legacy-*` | loadState() detects mismatch and quarantines |
| User clears browser data | ✗ L1 wiped | Only mitigation is L2 backup user must have exported |
| Cross-device | ✗ L1 not shared across origins | L2 export → email / iCloud / git → L2 import on other device |
| HTML file deleted / corrupted | ✓ L1 survives independently | Regenerate the HTML, L1 is bound to origin not file content |

## origin pinning

`localStorage` is keyed by `(origin, storage_key)`. For `file://` URLs, the origin is roughly "the directory the file lives in" — but exact behavior varies by browser:

- **Chrome / Edge**: Each `file://` HTML is treated as a separate origin (path-specific). Moving the file to a different directory creates a new origin → empty L1.
- **Firefox**: Similar, treats `file://` files as origin-specific.
- **Safari**: Stricter — sometimes sandboxes file:// localStorage entirely.

**Practical guidance for users**: pin the file in one location and always open it from there. Cross-device or cross-location? Use L2 export/import.

## Why no IndexedDB

We use localStorage instead of IndexedDB because:

1. **Synchronous API** — 5-line implementation. IndexedDB requires async transactions; harder to reason about in beforeunload handlers (browsers don't always wait for async cleanup).
2. **Data volume is tiny** — 50 questions × 500 chars × UTF-8 ≈ 30 KB. Far below the 5-10 MB localStorage quota.
3. **Synchronous = simpler save semantics** — when `saveStateNow()` returns, the data is flushed. No "is it actually written yet?" ambiguity.

If a future use case needs > 5 MB or transactional integrity, then IndexedDB. For now, localStorage wins on simplicity.

## Why no backend / DB / cloud

The user requirements explicitly say "别搞太重 — 简单稳定". Adding a backend means:
- Auth (who has access to whose data?)
- Server availability (what if it's down at 11pm?)
- Privacy (data leaves user's machine)
- Deployment (where does it live?)
- Cost

Each of these is a failure mode. localStorage + JSON export hits the simplicity sweet spot: data lives on the user's machine, recovery is a file pickup, and the system has zero parts to maintain.

If a future use case needs collaboration or cross-device sync, that's a different skill. This skill is single-user introspection.
