# 数据与查询合同

## 来源
- 数据库页面：https://cloud.mioffice.cn/new-devx/database/sql?treeId=518453&appName=rollica-server&resourceType=postgresql&resourceId=140082&appId=374181
- Prod / 中国-北京 / adx_ai_multica / public。先核对实际环境，不向 QA 查询后冒充生产。
- 版式来源：MIA-289（28897690-854c-4a42-947e-f5b62e473397）附件；用户于2026-09-08确认去掉事件前后模块后的30天版。
- SQL是每次只读查询，不创建表、视图、存储过程或固定统计服务。本技能没有专用 SQL 文件。

## 日期与身份
- Asia/Shanghai，start 00:00:00+08 包含，end+1日00:00:00+08不包含。
- public."user": id, name, email, created_at。按 lower(btrim(email)) 归并身份；name可取 min(name)，注册日取最早账号创建日期，accounts为账号数。
- 只纳入 created_at < 截止时间的现存账号；不要把今天新注册者算进昨天全集。零消息用户也保留。
- 不通过 member 表复制行。会话 creator_id 和 member 类型评论 author_id 均对应 user.id，而非 member.id。
- 历史schema可能改变：仅需核对相关列，不扫描凭证或其他不相关字段。

## 消息
- Work：chat_message m JOIN chat_session s ON s.id=m.chat_session_id；m.role='user' AND m.message_kind='message'，按 s.creator_id 归属。
- Issue：comment.author_type='member'，按 author_id 归属；可审计 type 分布，2026-09-08所查最近7天均为 comment。不同type出现时核对含义，不静默改变口径。
- 两路先按相同时间边界过滤，再 UNION ALL 聚合。按 (created_at AT TIME ZONE 'Asia/Shanghai')::date 分天。
- 统计数据库现存普通消息记录，不等于唯一人工发送行为；导入、fork复制等若保留为普通消息也会进入现有口径，不擅自“修正”或声称已排除。
- 不含 AI、工具事件、Agent评论、token消耗、登录/浏览。不能用此报表判断升级造成流失。

## 渲染脚本输入
完整 JSON；或查询 UI 导出的 CSV，仅一个 report 字段、一行JSON。

```json
{
  "start": "2026-01-01",
  "end": "2026-01-30",
  "observed_at": "2026-01-31T01:00:00+00:00",
  "all_work": 3,
  "all_issue": 2,
  "unmatched": 0,
  "users": [
    {"name":"示例用户","email":"sample@example.invalid","registered":"2025-12-01","accounts":1,"total":5,"daily":[[0,3,0],[4,0,2]]},
    {"name":"零消息示例","email":"zero@example.invalid","registered":"2026-01-10","accounts":1,"total":0,"daily":[]}
  ]
}
```

daily 是稀疏数组，每项 [从start起的0基日期索引, Work条数, Issue条数]，按日升序，无重复日，省略0/0日。用户按总量降序、同分按email升序输出。统计全部事件的 all_work/all_issue，与用户聚合独立计算，unmatched审计未找到user的事件。

## 浏览器操作经验
- 浏览器句柄/节点号是临时的，必须重新发现；不要把此会话旧编号写死。
- SQL编辑器可能为 Monaco。先点编辑器，再用该环境正确的全选快捷键。2026-09 Mac CUA 的 super+a有效，Control_L+a未清空文本，曾导致拼接SQL。
- 执行前/失败后核对页面实际提交的SQL；别点击历史记录的“执行”误跑其他语句。
- 有“执行中”时等结果；成功后导出当前结果CSV，确认字段report及日期。UI历史区可能包含高风险旧SQL，不执行它们。
- 大JSON只读到前几屏不足以交付。CSV完整下载后由脚本解析、核对行数和聚合。
- 浏览器阻止local file/登录/权限时遵循工具限制；文件面板可作为交付，不能另起服务绕过禁令。
