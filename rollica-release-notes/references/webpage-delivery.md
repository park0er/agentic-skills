# Release Webpage Delivery

Read this reference only when creating, validating, publishing, or deploying a Rollica release webpage.

## Artifact selection

Choose artifacts from the destination rather than producing every variant by habit:

- **HD directory (default for hosting):** `index.html` plus `assets/`; preserves original media, keeps HTML small, and allows caching.
- **Lightweight self-contained HTML:** use for hosts that require one file or impose upload/payload limits. Optimize copies, do not mutate the HD originals.
- **HD self-contained HTML:** use only when the user explicitly needs a portable single file and accepts its size.

Observed during v0.0.2: the Protofly upload path through `mcporter` became unreliable near an approximately 880 KB payload, while a 580 KB page succeeded. Treat this as historical evidence, not a stable platform contract; measure or probe the current path before relying on it.

## Fit a size-limited host without losing resolution

Apply the levers in this order and stop as soon as the artifact fits. Never start at the bottom.

1. **Change format first.** Re-encoding UI screenshots as WebP at quality 76–80, with pixel dimensions unchanged, measured 32–49% smaller than JPEG quality 80 on the v0.0.2 captures with no visible loss. This alone often closes the gap.
2. **Then lower quality**, in small steps, checking that on-screen text in the screenshot stays crisp.
3. **Reduce pixel dimensions last.** Downsampling is the one lever that destroys detail the reader can no longer recover by enlarging, and it directly weakens click-to-enlarge. If the page has a lightbox, size each capture for the enlarged view, not for its thumbnail slot.
4. Keep the HD originals byte-identical throughout, and report the achieved numbers per artifact so the trade-off is auditable.

### Probe a transport limit without creating garbage

A size ceiling rarely reports itself as a size error. Observed forms: `RangeError: Maximum call stack size exceeded` with empty stdout, a silent empty success response, and `OSError: Argument list too long`.

- Suspect payload size when the same call succeeded with a smaller artifact minutes earlier.
- Find the ceiling with a **non-mutating** tool on the same transport — for example a list or read call padded with a dummy field — and binary-search the padding size. This locates the limit without creating throwaway resources on the host.
- Build the deliverable to roughly 90% of the measured ceiling, then record the measurement with the release so the next person does not rediscover it.

## Known destinations

Confirm these against current evidence rather than assuming they still hold, and never guess a value that is not listed here.

- **Repository:** `https://git.n.xiaomi.com/biz-ai-lab/rollica`, working branch `develop`. The Next.js web surface lives under `apps/web`.
- **Production web host:** `https://rollica.ad.miui.com` — the official site, external-network accessible. Web sign-in is `https://rollica.ad.miui.com/login`. Release pages live at `/release/v0-0-<patch>`, verified live for v0.0.2 as `https://rollica.ad.miui.com/release/v0-0-2`. Keep the version path hyphenated so matchers do not read a dotted version as a file extension.
- **Staging web host:** `http://staging-rollica.ad.xiaomi.srv`, same `/release/v0-0-<patch>` path. Office-network only. Use it for review, never as the link a reader-facing document advertises. The v0.0.2 changelog shipped pointing at the staging release page, which readers outside the office network cannot open — check this every release and prefer the production URL in any published copy.
- **Internal one-file page host:** Protofly, `https://protofly.v.mitvos.com/view/<resource_id>`. Company-network link, no per-person authorization once visibility is public. Verified for v0.0.2 as resource `PF26080512180017ABD9`.

### Desktop installation, all platforms

Never publish only the platform you happen to be running. Cover Mac Silicon, Mac Intel, and Windows, and state per platform whether a manual reinstall is required or the auto-updater handles it.

- **Canonical source:** the dedicated Feishu doc 《Rollica安装》 (`BLV7w8PnDiR600kABBjcjrLwnVb`). Read it for the current per-platform packages instead of hardcoding download links into a release page, and cross-check that the changelog and the release page agree with it.
- **Package naming:** `rollica-desktop-<version>-<platform>` with platform `mac-arm64` / `mac-x64` (both `.dmg`) and `windows-x64` (`.exe`). Verified at v0.0.2: mac-arm64 ≈ 229 MB, mac-x64 ≈ 230 MB, windows-x64 ≈ 169 MB.
- **Update feed:** FDS, `http://cnbj1-fds.api.xiaomi.net/rollica/rollica-version/<platform>/` (generic provider, `latest` channel). Confirmed from the shipped app's `app-update.yml` for `mac-arm64`; the sibling platform segments follow the same naming by convention, so verify one before citing it.
- **Upgrade-path wording is per platform and per release.** At v0.0.2 only Mac Silicon needed a one-time manual reinstall, while Mac Intel and Windows received the update automatically. State this explicitly so users on auto-updating platforms are not told to reinstall.
- Also list the non-desktop entry points when the audience needs them: the web host above, and the Feishu app (search Rollica in Feishu) for in-Feishu notifications.
- Include the first-launch Gatekeeper guidance for macOS when the audience contains new Mac users; 《Rollica安装》 carries per-macOS-version steps.

## Page contract

Keep the webpage synchronized with the approved Markdown and Feishu source:

- Real Rollica logo and favicon when available, sourced not invented. Prefer the repository. When repository checkout is unavailable — for example `multica repo checkout` reporting that the repo is not configured for this workspace — fall back to the shipped desktop bundle: `/Applications/Rollica.app/Contents/Resources/app.asar` contains `out/renderer/assets/rollica-icon01-*.png` (512×512, transparent corners, near-white rounded tile with a dark mark), extractable by parsing the asar header. Verify a fallback asset programmatically — corner alpha, opaque bounding box, luminance split — instead of trusting its filename.
- Version, date, headline, concrete scenario, feature/improvement/fix sections, acknowledgements, and approved installation/download details.
- Link back to the current Feishu source when the audience can access it.
- Accurate audience and artifact wording; remove “内部草案” and draft-only meta from a published page.
- Captions tied to the correct release item.
- Responsive layout without horizontal overflow.
- Click-to-enlarge media with keyboard focus, Enter/Space activation, Escape/background close, focus return, scroll lock, and synchronized caption.
- Zero external CDNs; use system fonts and local assets.
- Reveal animations must fail visible, never blank. A scroll-reveal rule that unconditionally sets `opacity:0` blanks the entire page whenever JavaScript or IntersectionObserver does not run, which happens in embeds, restricted viewers, and reader modes. Gate the hidden state on a script-set class such as `html.js`, and add a timer fallback that reveals everything if the observer never fires. Losing the animation is acceptable; losing the content is not.

Use a version path with hyphens, such as `/release/v0-0-2/`, on both the production and staging web hosts. This avoids treating dotted versions as file extensions in matchers. See "Known destinations" for the current hosts.

## Draft-to-published sweep

Draft markers hide outside the visible copy. When a page moves from internal draft to published, clear every one of these and then assert that each stale string occurs zero times:

1. Draft badge or status chip.
2. Draft callout / notice block.
3. Footer wording, including any “请勿对外分享”-style line that now contradicts the approved audience.
4. `<title>` suffix and `<meta name="description">`.
5. Release date — check every occurrence, not the first.
6. Source-document link — typically present in both the navigation and the footer.
7. Artifact description, when the sentence still describes the previous variant or media count.

Search the built file for the old date, the old document token, the draft label, and the superseded wording, confirm each count is zero, then confirm the new date and new link appear the expected number of times.

## Access and deployment safety

- A public URL is not equivalent to a company-internal link. Confirm public access explicitly when screenshots or copy originate from internal systems.
- Prefer a dedicated release path or a new static project. Never replace an existing app root merely to host release notes.
- When deploying through the Rollica Web app, start from a clean remote baseline, add only the release artifact and narrowly required routing, verify the remote branch has not advanced, and keep the commit atomic.
- Do not include unrelated local commits or uncommitted files. Do not change Matrix/Ingress/host rules when the existing catch-all already routes the release path.
- For a new public static project such as Cloudflare Pages, use a dedicated project name and verify that no existing project was modified.
- Treat publishing, pushing, and deployment as separate authorized mutations. Stop before the first one the user did not request.

## Local validation

Validate observable behavior, not only source text:

1. Compare generated copy with Markdown and Feishu for version, date, links, section order, attribution, installation details, and media count.
2. Search for stale versions, old document tokens, superseded wording, draft labels, and incorrect artifact descriptions.
3. Check every local image/resource resolves; preserve originals in the HD directory.
4. Render at representative desktop, compact desktop/tablet, and mobile widths (for example 1400, 900, and 375 px) and confirm no horizontal overflow.
5. Open and close the lightbox by pointer and keyboard; verify focus return and scroll restoration.
6. Check logo/favicon, alt text, captions, navigation links, and console errors.
7. When the page enters `apps/web`, run the narrow Web tests and a production build. Add a route/static-resource test when routing changes.

### Prove it with measurements, not screenshots

Visual inspection of a rendered page may be unavailable — image-reading can be blocked by tool limits, and a screenshot cannot prove focus behavior anyway. Drive a headless browser and assert on the DOM instead. Each check below is a pass/fail number:

- **Overflow:** per breakpoint, `document.documentElement.scrollWidth === clientWidth`. To attribute a failure, walk elements whose right edge exceeds the viewport and skip any that sit inside an ancestor with `overflow-x: auto|hidden|scroll`, so intentionally scrollable wide tables do not read as bugs.
- **Media:** count images with `naturalWidth > 0` and compare against the expected total. Remember an intentionally emptied lightbox `<img>` legitimately reports 0.
- **Lightbox:** click a capture programmatically, assert the open state, the enlarged image fits the viewport, and the caption matches that item; dispatch `Escape` and a background click and assert it closed; assert the scroll lock was applied and released.
- **Errors:** install an error listener before load and assert zero console errors.
- **Brand:** assert the logo's `naturalWidth > 0` so a broken asset cannot pass unnoticed.

Two headless traps that produce false results if ignored:

- **Viewport floor.** Chrome headless clamps the window to roughly 500 px wide, so `--window-size=375` renders a 500 px layout and crops the screenshot to 375 px. That looks exactly like horizontal overflow but is an artifact. Test narrow widths by hosting the page in a 375 px-wide `iframe` and measuring inside it.
- **Viewport-height heroes.** A hero using `min-height: 100svh` expands to fill whatever window height you request, so a tall full-page screenshot captures only the hero. Measure each section's `offsetTop` first, then capture or assert section by section.

## Online validation

After deployment:

- Confirm the pipeline or provider reached a terminal success state and identify the deployed commit/version.
- Load the stable URL and a cache-busting URL when appropriate.
- Verify HTML and every media asset return successfully; compare byte hashes with the local HD directory when fidelity matters.
- Repeat the main lightbox, responsive, link, and console checks on the real domain.
- Confirm the live access policy matches the approved audience.
- Report both the stable URL and an immutable/version URL when the host provides one.

Do not describe a deployment as complete while the pipeline is still running or when only the HTML—not its images and interaction—has been checked.
