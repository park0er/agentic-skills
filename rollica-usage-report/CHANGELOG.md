# rollica-usage-report CHANGELOG

## 2026-09-21 — add-rollica-repository-target

- 纳入 Rollica 仓库 `.agents/skills/rollica-usage-report/` 共享发布目标。
- Issue 状态回写改用当前已登录的 Rollica CLI，个人包装器仅作为可选能力。
- 维护流程增加 Rollica 仓库同步、验证和 checkpoint commit。

## 2026-09-08 — initial-usage-heatmap-report

- Initial release：封装用户已确认的近30天HTML格式，完整保留热力图、排名、个人详情与CSV。
- 日期参数化、数据验证和模板渲染，不包含真实用户数据。
- 浏览器只读查数；不固化专用SQL、不自动上传个人明细或下发图标。
