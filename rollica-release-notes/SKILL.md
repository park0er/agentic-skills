---
name: rollica-release-notes
description: Create, revise, audit, or publish Rollica version introductions from release-project Issues and QA/Staging evidence. Use when整理发版说明或 changelog、创建或同步带真实 @ 的飞书版本介绍、规划截图/GIF、生成轻量或高清发布网页、准备部署版本介绍，或检查整个发布介绍流程是否漏项。Proactively audit missing scope, acceptance, attribution, media, audience/access, installation, and deployment decisions; ask focused questions before unsupported claims or risky publication. Preserve internal Issue provenance while omitting internal Rollica Team proposer acknowledgements from public copy.
---

# Rollica Release Notes

Turn verified release evidence into one synchronized content package: local Markdown, an optional Feishu collaboration document, and an optional release webpage. Make contributors feel heard without overstating what shipped.

## Define the records and lifecycle

- Treat the **Issue record** as internal provenance: real proposers, status, comments, commits, acceptance evidence, and product decisions.
- Treat **Markdown** as the durable local truth source. Keep media under the matching local release directory and retain hidden `<!-- MIA-NNN -->` markers.
- Treat **Feishu** as a collaboration/presentation copy. Preserve the Feishu URL in the Markdown header as `<!-- feishu: URL -->` and sync only intentional edits in either direction.
- Distinguish the two Feishu document shapes; they are not interchangeable. A **single-version draft** (for example 《vX.Y.Z 发版说明（内部草案）》) is the drafting and content-truth surface. The fixed reader-facing **multi-version changelog** is [《Rollica功能介绍/更新日志》](https://mi.feishu.cn/wiki/C9eOwRiB0i3bZVk8uVMcYHOInTh); it aggregates several versions. Name which document is the content source and which one the page links to, and confirm the intended audience can actually open the linked one. Never let the page link to a private draft, and never take copy from the aggregate without confirming that its version section matches the approved draft.
- Treat the **webpage** as a rendered derivative of the approved Markdown plus local media, never as an independent copywriting branch.
- Treat **publishing** as an external write: creating a draft does not authorize sharing, messaging, pushing, or deploying it.
- Treat **Mobile Web / PWA** as Rollica in a mobile browser or installed from that browser. Do not imply a separate native mobile app.

## Run the completeness audit before writing

1. Start from the approximate Issue range supplied by the product owner, then read those Issues in the current release project again. Prefer `rollica-management` when available. For an initial release-notes draft, treat `done` and `in_review` as candidates; exclude `backlog`, `todo`, `planned`, and `cancelled`. Keep `in_progress` and `blocked` unresolved unless the product owner explicitly includes them. An explicit per-Issue inclusion or exclusion overrides this default.
2. Check title, description, status, parent/child scope, proposer, latest comments, explicit QA/Staging acceptance, and release-checklist evidence.
3. Build an include / exclude / unresolved inventory. `done` alone does not prove acceptance; a product-owner decision may deliberately override workflow status, but record that decision.
4. Inspect existing Markdown, Feishu, media, webpage, installation links, and deployment records before recreating anything.
5. Read [release-question-gates.md](references/release-question-gates.md) whenever the request is underspecified or a stage may have been skipped.

Do not ask for information that can be discovered safely. Ask one to three focused questions at a time when an answer changes public claims, permissions, access, or deployment. Continue safe drafting while waiting when possible; pause only the affected publication step.

Proactively remind the user about the next missing stage. Examples: missing proposer data before acknowledgements, missing visuals before webpage generation, a private Feishu draft without a reviewed access plan, or a finished page without an authorized deployment destination.

## Build the approved story

1. Include only approved, accepted scope. Split unfinished sub-scope into a child Issue when requested and exclude it from public claims.
2. Use accurate sections such as 新功能、改进、问题修复. Keep the category honest even when an item receives a prominent visual.
3. Lead with user-visible outcomes, not commits or architecture. Ground a headline in a concrete role-and-moment scenario only when supplied by the user or evidence.
4. Preserve a hidden `<!-- MIA-NNN -->` marker after every public item.
5. Keep a visible or reported exclusion list so the user can review omitted Issues before publication.

## Apply public attribution and ordering

Before drafting acknowledgements, make one lightweight proposer pass over every included item:

- Read the Issue description and relevant comments for an explicit `提出人`, source, quoted feedback, or product decision. Do not infer the proposer from the Issue creator, assignee, implementer, reviewer, or commenter alone.
- Keep an internal audit with Issue, evidence, real proposer(s), rendered public attribution, and unresolved questions. This audit is drafting evidence, not a release-engineering gate and does not need to be published.
- Mark unsupported attribution as unresolved instead of silently adding a generic acknowledgement. Batch only the ambiguous names that the product owner must confirm.

- Treat **赵锡盛**, **吕铁**, and **白吉航** as internal Rollica Team members. Preserve their real names in Issue provenance, but do not render their names or `@Rollica Team` as public proposer acknowledgements.
- For a mixed proposer list, acknowledge only non-Team proposers. For a pure Team item, omit the acknowledgement sentence entirely.
- In public attribution, order priority stakeholders **曾德鋆**, **刘雪娅**, then other named users.
- Treat “无人提出，来自产品经理赵锡盛” as having no public proposer acknowledgement.
- Apply an explicit product-story placement before the default order. Otherwise, within each section place: priority-stakeholder items, other user-backed items, then items without public proposer attribution. Within a tier, order by user impact.
- Use the same public ordering in the final thank-you paragraph. Exclude internal Team members and `Rollica Team`; if no non-Team proposer remains, omit the thank-you list or section instead of inventing an attribution.
- **提出人致谢与正文段落同行**：条目末尾的致谢句（如“感谢提出人：@姓名”或 `<mention-user id="..."/>`）必须直接紧跟在条目说明段落末尾（句号后同行排版），禁止另起一行或独立成段，保持版面紧凑流畅。

Examples:

- `赵锡盛` → 不写公开感谢句。
- `赵锡盛、余婕` → `感谢 @余婕 提出。`
- `曾德鋆、赵锡盛` → `感谢 @曾德鋆 提出。`
- `王桃宇、白吉航、赵锡盛` → `感谢 @王桃宇 提出。`
- `吕铁、白吉航` → 不写公开感谢句。

## Plan and collect release media

Read [feishu-media-sync.md](references/feishu-media-sync.md) before extracting images from a Feishu document or re-syncing a document that changed mid-flight.

- Give each user-visible new feature one primary visual when practical. Prefer a GIF or before/after pair for a state transition; use a static image for a stable screen, menu, badge, or completed state.
- Do not force media for invisible lifecycle, policy, migration, or reliability changes. Add media to fixes and improvements when it materially reduces explanation cost or the user requests it.
- Tell the user exactly what each capture must show and whether it should be an image or GIF. Check tokens, accounts, customer content, local paths, and internal domains before reuse.
- When Feishu is the collaborative draft, ask the user to paste each visual immediately below its item. Download the reviewed originals into the local release assets directory and add relative Markdown links without overwriting unrelated edits.

### Decide screenshot sensitivity by asking, not by editing

Redaction changes what the owner chose to show, so it is their call, not a default.

- Silently redact only true credentials: tokens, API keys, passwords, session cookies, signed URLs, and personal contact details.
- For everything else — visible colleague names, chat or group names including ones labelled 保密 or 禁截图, internal hostnames, staging URLs, workspace IDs, local file paths, unrelated business content — do not crop, blur, or drop the image on your own. List exactly what each image exposes, state the audience you understand it is going to, and let the owner decide.
- Record the owner's decision with the release so a later turn does not re-litigate it or silently reverse it.
- Re-ask only when the audience changes, for example when an internal-link page becomes a public-internet page.

## Create or synchronize the Feishu document

- Use the company Feishu workflow when requested. Resolve people to real Feishu mentions rather than plain `@姓名` text.
- **飞书文档彻底不显示 Issue 编号**：飞书面向读者与团队公开呈现，严禁在条目中暴露裸露的 `MIA-NNN` 编号；编号仅作为隐性 HTML 注释 `<!-- MIA-NNN -->` 保留在本地 Markdown 中供内部溯源，生成飞书内容时剥离。
- **提出人致谢与条目段落同行**：在飞书文档中，条目末尾的致谢句（如 `<mention-user id="..."/>`）必须直接紧跟在条目说明正文段落末尾同行呈现，不换行。
- **飞书文档不收录内部发版审计与移出条目等附录**：飞书发布文档在「感谢每一条真实反馈」后即收尾，不附带“正式发版收录全景对照表”或“移出发版说明条目”等内部流程审计表格；内部审计表仅供本地草案评审使用。
- Creating a private draft must not send messages or grant collaborators. Verify the member list and access after creation. Mention blocks do not authorize notifications.
- If the requested audience or sharing policy is unclear, keep the document private and ask before sharing.
- After upload or download, retain the Feishu link comment in the Markdown header.
- For a user-edited Feishu item, fetch the exact live block, confirm the wording, convert Feishu user cites back to Markdown `@姓名`, patch only that item, and preserve its Issue marker. Markdown becomes the truth source again after the targeted sync.

## Generate and deliver the webpage

Read [webpage-delivery.md](references/webpage-delivery.md) before generating, publishing, or deploying a release webpage.

- In Codex, prefer the Visualize capability for the HTML; elsewhere use the available `tariq-html` workflow. Keep the final artifact self-contained or directory-contained with zero CDN dependencies and CJK-safe system fonts.
- Derive all copy, ordering, attribution, links, date, and media from the approved content package. If the Feishu copy changed, sync it back before rebuilding the page.
- Default to an HD directory build (`index.html` plus `assets/`) for normal hosting. Produce a lightweight self-contained page only when the selected host or user needs it. An HD single-file build is optional, not the default deployment artifact.
- Do not deploy merely because the page is ready. Confirm audience/access, destination, overwrite scope, and authorization immediately before publishing.
- Know the standing destinations before asking where to publish; see "Known destinations" in [webpage-delivery.md](references/webpage-delivery.md). The repository, production and staging web hosts, release path convention, and per-platform desktop packages are recorded there. Publish reader-facing links against the production host, and cover Mac Silicon, Mac Intel, and Windows whenever the page carries installation details.

### Do not repair infrastructure to get a release out

A failing publish step is not a licence to reconfigure the machine.

- When an internal host fails to resolve or connect, query the corporate resolver for both the failing host and a known-good internal host. If the others resolve, treat it as remote flapping: retry with backoff and report the attempts.
- Never modify VPN, proxy, Clash, DNS, routing, or system network configuration as part of a release-notes task, even when a repair skill for it exists. Report the symptom and hand the decision back.
- Distinguish a transport limit from an outage: an opaque interpreter crash or an empty success response usually means payload size, not connectivity. Probe the limit safely as described in [webpage-delivery.md](references/webpage-delivery.md).

## Verify and hand off

- Re-read changed Issues after writes and confirm every included Issue appears exactly once.
- Confirm deferred child scope and excluded Issues do not leak into claims.
- Confirm public attribution/order and internal provenance both remain correct.
- Confirm promised media is present under the right item and has passed the privacy check.
- Confirm Markdown, Feishu, and webpage share the same approved content; search for stale dates, old links, draft labels, and superseded wording.
- Run the format- and deployment-specific checks in [webpage-delivery.md](references/webpage-delivery.md).
- Report source records changed, deliverable links/paths, access state, included/excluded/unresolved scope, tests actually run, and any next missing stage.
- For repository work, include `分端架构影响 / Architecture Impact by Layer`; documentation/skill-only work should state that runtime architecture is unchanged.
