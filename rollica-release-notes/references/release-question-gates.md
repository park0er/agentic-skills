# Release Question Gates

Use this audit to decide what to discover, what to ask, and what must block publication. Do not turn it into a questionnaire dump.

## Ask only after discovery

First inspect the release project, Issue comments, acceptance evidence, existing release files, linked Feishu document, local assets, release checklist, and deployment history. Mark each item as known, safely inferred, or unresolved.

Batch one to three questions that unblock the most downstream work. State the current evidence and the assumption that cannot safely be made. Keep working on independent stages.

## Public-claim gates

Resolve these before the copy claims a capability shipped:

- Exact version and release date.
- Included, excluded, and deferred Issues.
- QA/Staging acceptance for each included item, or an explicit product-owner override.
- Parent/child scope when only part of an Issue shipped.
- Ambiguous category: new feature, improvement, or fix.
- Missing proposer/source data needed for attribution.
- Headline capability and any concrete scenario the user wants emphasized.

If acceptance or scope is unresolved, keep the item in an unresolved inventory; do not silently omit it or write it as shipped.

## Feishu gates

Resolve these before creating or sharing the document:

- Create a new document or update an existing URL?
- Private working draft or shared publication copy?
- Should names be real mention elements? If yes, verify identity resolution.
- Is notification or messaging requested? A mention is not permission to send a message.
- Does the installation/download section belong in this version?

Default a newly created draft to owner-only access. Never infer sharing from the presence of `@` names.

## Media gates

Resolve before final page generation:

- Which visible items need a screenshot, GIF, or before/after pair?
- What exact UI state must each capture show?
- Are the originals available in Feishu or locally?
- Has every image been checked for tokens, accounts, customer content, local paths, and internal-only domains?
- Should the public/lightweight page downsample media, while the internal/HD page preserves originals?

If media is missing, provide a capture list and continue with a clearly marked draft rather than inventing visuals.

## Web and publication gates

Resolve before external publication:

- Required outputs: preview only, lightweight page, HD directory, HD single file, or more than one.
- Audience: owner-only, company-internal link, authenticated external access, or public internet.
- Destination and stable URL path.
- Whether deployment is authorized now or only preparation is requested.
- Whether an existing app, root route, project, or domain could be overwritten.
- Whether the final page includes install/download links, whether all shipped platforms are covered (Mac Silicon, Mac Intel, Windows), which package is canonical, and which platforms auto-update rather than needing a manual reinstall.
- Whether reader-facing links point at the production host rather than a staging host the audience cannot reach.

Internal screenshots plus a public host is a meaningful privacy boundary; ask explicitly even when the user previously approved another internal link.

## Completion reminders

Before saying the release introduction is finished, check for forgotten transitions:

1. Approved Issue inventory → Markdown draft.
2. Markdown draft → private Feishu collaboration copy.
3. Feishu manual edits → targeted Markdown sync.
4. Media capture list → reviewed originals in local assets.
5. Approved content package → webpage variants.
6. Page ready → explicit audience/access and deployment decision.
7. Deployment → online validation and final links.

Call out the first missing transition as the recommended next step. Do not claim end-to-end completion when only an earlier stage is complete.
