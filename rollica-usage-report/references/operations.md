# 长期运营记录

- Rollica 项目：Rollica长期运营和数据统计
- Project ID：f5d39a08-664c-4fd3-9794-660feb50ecc6
- Workspace：MiAdsAgent / 7030e6ae-f980-4940-a869-a16ed7f84d12
- 跟踪Issue：MIA-451（0c1e2c76-fdc0-49a8-9abf-59f28a75ffd1）
- 链接：https://rollica.ad.miui.com/miadsagent/issues/0c1e2c76-fdc0-49a8-9abf-59f28a75ffd1
- 用户于2026-09-08批准：每天北京时间09:00独立Codex Scheduled，模型gpt-5.6-luna，reasoning xhigh。调度状态以Codex工具回读为准，技能自身不调度。
- 输出位置由运行提示指定。不要把用户报表或邮箱数据写进技能/Factory，也不要自动上传公开托管平台。
- 运行成功/失败可用当前已登录的 Rollica CLI 向 MIA-451 补一条不含个人数据、本机路径的状态；本机已有 `rollica-management` 时可用其包装器。写前检查 `assignee_type`；如已分配 Agent/Squad，不评论以免唤醒，只向用户报告待同步。重复同一统计截止日期的相同状态不刷评论。
- 首轮真正自动执行完成后才可记录无人值守验收通过；技能单测/历史数据复算不代表Scheduled已跑通。
