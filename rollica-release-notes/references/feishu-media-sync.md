# Feishu Media Extraction and Re-sync

Read this reference when pulling images out of a Feishu release document, or when the document changed while the release package was already being built.

## Extraction contract

The documented convenience path is not reliable for these documents. Verify what you actually got before building anything on top of it.

- `feishu fetch <url> --download-images` can return an empty `media` array even when the document clearly contains screenshots. In that case the images are inline Markdown links whose target is a signed stream URL, not media tokens, and nothing was downloaded. Always assert the expected image count instead of trusting the command's exit status.
- Extract the inline URLs from the returned Markdown and fetch each one directly. Confirm the real byte format per file rather than trusting the extension: the same document can mix PNG and JPEG.
- Signed stream URLs carry a rotating authorization code and an expiry. Never persist them for a later turn, never share them, and re-fetch the document to obtain fresh URLs every time you need the originals again.
- Because the signed code changes on every fetch, the URL cannot identify an image across fetches. Identify images by their position in the document plus their surrounding item text.
- Feishu may auto-inject AI-generated alt text, turning `![](url)` into `![描述文字](url)`. A pattern that assumes empty alt text will silently match zero images after that happens. Match alt text as optional, and treat a sudden drop to zero matches as a format change, not as "no images".
- Honour layout intent from the document: a `<grid>` with `<column width-ratio=...>` around two images means the author wants them side by side, and the ratio indicates which one is the narrow portrait capture. Reproduce that pairing on the page instead of stacking them.
- Keep the originals untouched in the release assets directory. Optimized copies belong to the page build, never overwriting the source capture.

## Re-sync by diff, never by rebuild

A release document typically changes several times while the package is being assembled. Rebuilding from scratch loses reviewed decisions and hides what actually moved.

1. Persist every fetched Markdown snapshot in the build directory, for example `source-doc.md`.
2. On each re-fetch, diff the new content against the stored snapshot before editing anything.
3. Report the delta to the user in their terms — item added, screenshot added, wording changed, section removed — and state which deliverables it touches.
4. Apply only that delta to the Markdown, the media set, and the page. Then replace the snapshot.
5. Treat structural changes as first-class deltas: a removed draft callout, a new installation section, or an item promoted between sections all change public claims even when no sentence changed.

## Item-to-visual mapping

Release screenshots of the same product look nearly identical, so filename order is not evidence of what an image shows.

- Build an explicit mapping table before writing captions: release item, source file, and the exact state the capture must prove.
- Verify each entry from the image content, not its position — for example a collapsed timeline versus the same timeline expanded, or a badge present versus absent.
- When one item legitimately owns two captures, say which is which in the captions, and keep both under that item.
- After the page is generated, confirm the count and order again: every promised visual present, under the correct item, with a caption that matches the state it actually shows.
- If a capture cannot be matched to an approved item with confidence, ask rather than guessing a caption. A wrong caption reads as a false claim about the release.
