# rollica-release-notes CHANGELOG

## 2026-09-22 — inline-proposer-and-clean-feishu-doc

- 飞书发版文档面向最终用户，彻底移除裸露的 Issue 编号（MIA-NNN），Issue 标记仅在本地 Markdown 中以 `<!-- MIA-NNN -->` 隐性注释留存。
- 条目末尾的提出人致谢句（如“感谢提出人：@姓名”）必须紧跟在条目正文段落末尾同行排版，禁止另起独立段落。
- 飞书协作/发版文档仅包含正文与致谢清单，内部 Issue 审计对照表与剔除条目等附录属于草案走查工具，不写入飞书公开发布文档。

## 2026-08-26 — omit-rollica-team-public-attribution

- 公开发布说明不再出现“感谢 @Rollica Team 提出”或任何等价的内部 Team 提出人署名。
- 混合提出人条目只感谢非 Team 提出人；纯 Team 条目省略感谢句，最终感谢名单同样排除 Rollica Team。
- Issue 内部记录继续保留赵锡盛、吕铁、白吉航等真实提出人，公开口径变化不影响内部溯源。

## 2026-08-26 — add-changelog-source-and-proposer-pass

- 固定读者面《Rollica功能介绍/更新日志》飞书链接，避免页面误链私有单版本草案。
- 按产品负责人给出的 Issue 范围做轻量状态筛选：默认以 `done` / `in_review` 为候选，排除待办、待规划与取消项。
- 增加逐条提出人证据核对，禁止用 Issue 创建者、执行者或评论者身份代替真实提出人；证据不足时集中请产品负责人确认。

## 2026-08-21 — record-verified-hosts-and-all-platform-installers

- 补全发布目标：生产站 `https://rollica.ad.miui.com`（外网可访问，登录 `/login`，发版页 `/release/v0-0-<patch>`，v0.0.2 已验证）与 staging `http://staging-rollica.ad.xiaomi.srv`（仅办公网，只用于评审）；移除上一版"公网域名每次必问"的占位说法。
- 记录 v0.0.2 变更日志把"炫彩网页版介绍"指向了 staging 发版页（办公网外打不开），要求每次发版检查读者面链接必须用生产站。
- 安装信息扩展到全平台，不再只写 Mac Arm：命名规范 `rollica-desktop-<version>-{mac-arm64|mac-x64|windows-x64}`（v0.0.2 实测 229 / 230 / 169 MB），FDS 更新源按平台分段，并要求逐平台说明是"需手动重装一次"还是"自动更新"（v0.0.2 仅 Mac Silicon 需重装）。
- 以《Rollica安装》飞书文档（`BLV7w8PnDiR600kABBjcjrLwnVb`）为安装信息唯一真源，禁止把下载直链硬编码进发版页；同时纳入 Web 入口、飞书应用入口与 macOS 首次启动放行指引。
- 问题门禁新增两问：安装链接是否覆盖全部已发布平台、读者面链接是否误用 staging 域名。

## 2026-08-21 — feishu-media-and-verification-hardening

- 截图敏感内容改为"标记并询问"：只自动遮蔽真凭据（token/key/密码/签名 URL），群名、同事名、内网域名、staging 地址、workspace ID 等一律列清楚交 owner 决定，并记录决定，避免 agent 自行裁剪覆盖产品意图。
- 新增 `references/feishu-media-sync.md`：飞书图片提取契约（`--download-images` 可能返回空 media、签名 URL 带轮换 authcode 与过期、不能用 URL 认图、AI 自动 alt 会打爆空 alt 正则、`<grid><column width-ratio>` 表示并排意图）、重取文档必须留快照并 diff 增量、条目↔截图映射表需按图内容核对。
- 区分两种飞书文档形态：单版本内部草案是内容真源，多版本《功能介绍/更新日志》是读者面；明确页面链哪一个并确认目标读者打得开，禁止链私有草案。
- 压缩阶梯固化为"先换格式 → 再降质量 → 最后才降分辨率"，记录 WebP q76–80 在不改像素尺寸下比 JPEG q80 小 32–49%；补充非写入型二分探测传输上限的安全做法（栈溢出/空响应/argv 超长都不会自报体积问题）。
- 补齐已知发布目标：仓库 `git.n.xiaomi.com/biz-ai-lab/rollica`（`develop`，Web 在 `apps/web`，版本路径连字符化）、桌面端更新分发 FDS 地址、Protofly 单文件内网宿主；公网发布域名明确列为"每次必问、不得从 workspace 名或 staging host 推断"。
- 发布期基础设施故障分诊：内网域名解析失败先比对已知正常域名判断是否远端抖动，退避重试；明确禁止在发版任务里改 VPN/代理/Clash/DNS/路由配置。
- 验收从"渲染确认"升级为可测量断言（逐断点 scrollWidth==clientWidth、图片 naturalWidth 计数、程序化开关 lightbox 与滚动锁、console 零报错、logo 加载），并记录两个 headless 陷阱：Chrome 视口约 500px 下限需用 375px iframe 承载、`min-height:100svh` 首屏导致整页长截图只拍到 hero。
- 页面契约新增两条：品牌资源取用顺序（仓库优先，不可用时从 `Rollica.app` 的 `app.asar` 解 `rollica-icon01-*.png` 并程序化校验）、渐显动画必须 fail-visible（`html.js` 门控 + 定时兜底，禁止无条件 `opacity:0`）。
- 新增"草案→正式"清零式扫描清单（角标、callout、页脚措辞、`<title>`/`<meta>`、所有日期、导航与页脚两处链接、产物描述），要求逐项断言残留为 0。

## 2026-08-20 — expand-rollica-team-attribution

- 将吕铁、白吉航与赵锡盛一起纳入公开署名的 Rollica Team 成员映射。
- 同一条目包含多个 Team 成员时只输出一次 `@Rollica Team`；与非 Team 提出人混合时，非 Team 真实 mention 在前、Team 在后。
- 内部 Issue 继续保留每位真实提出人；最终感谢段不再单列三位 Team 成员。

## 2026-08-20 — complete-feishu-web-release-workflow

- 将现有发版说明 Skill 扩展为 Issue 盘点、Markdown、飞书协作稿、媒体收集、网页生成与部署验收的一体化流程。
- 增加主动补问门禁：范围、验收、署名、权限、安装信息、截图和部署目标不足时先查证，再集中反问，防止漏流程或越权发布。
- 固化高清目录与轻量单文件的选择、内部/公网访问确认、安全子路径部署、响应式与 Lightbox 验证，以及三端内容一致性检查。

## 2026-08-04 — add-release-media-planning

- 增加发版截图和动图的选取标准：可见新功能原则上一项一个主视觉，状态变化优先动图。
- 明确不可见的生命周期优化不强行配图，Bug/改进按理解成本或产品要求补图。
- 固化飞书对应条目下粘贴、隐私检查、下载到本地 `assets/` 并同步 Markdown 的流程。

## 2026-08-04 — sync-feishu-edits-back

- 增加飞书人工改稿定点回写 Markdown 的双向同步流程。
- 回写前必须读取飞书现稿，并将飞书 cite mention 还原为 Markdown `@姓名`。
- 只修改用户指定条目，保留隐藏 Issue 标记，不覆盖其他内容。

## 2026-08-04 — add-concrete-user-scenarios

- 要求重大能力尽量用具体角色、时刻和动作介绍实际使用场景。
- 场景必须来自用户或证据，不得借场景暗示尚未发布的移动端或原生端能力。
- 首次沉淀“销售外出见客户、途中打开电脑继续推进 Work”的写法。

## 2026-08-04 — allow-explicit-story-priority

- 允许产品负责人明确指定某一发版事项的叙事序位。
- 显式序位可以覆盖默认的用户反馈优先排序，但不改变公开署名和内部提出人溯源。
- 验证流程同步区分默认排序与有意的产品叙事例外。

## 2026-08-04 — initial-user-feedback-first-policy

- 初次发布 Rollica 发版说明整理流程。
- 固化“用户反馈优先、老板姓名靠前、赵锡盛公开署名为 Rollica Team”的排序与署名规则。
- 明确公开发版稿与内部 Issue 溯源分离，避免改写真实提出人。
