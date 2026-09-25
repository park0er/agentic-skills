# 飞书招聘接口与字段参考

全部在**已登录的页面上下文里**用 `page.evaluate` + 相对路径 `fetch` 调用（带上登录 Cookie）。
不要用 curl / wget，不要拼绝对域名。

必带请求头：

```js
{'content-type':'application/json;charset=UTF-8','accept':'application/json','x-requested-with':'XMLHttpRequest'}
```

## 为什么必须走接口

`/hire/application-biz/evaluation/list` 的表格是 **canvas 渲染**的：

```js
document.body.innerText
// → "返回 我的任务 简历评估 面试 待安排面试 ... 283 个结果 表头设置 1 2 3 4 5 6 50 条/页"
```

一行候选人数据都没有。`document.querySelectorAll('table')` 返回空，也没有 shadow DOM。
页面里有 6 个 `<canvas>`，数据全画在上面。所以"截图 + OCR"和"抓 DOM"都不要试。

## 1. 评估列表（主取数口）

```
POST /atsx/api/evaluation/list_v2/
{
  "q": "",
  "filters": "{}",                 // 字符串化的 JSON；页面上的学校筛选是 {"v2_school":{"enum_list":["4"]}}（4 = QS200）
  "activity_status": 1,            // 0 全部 / 1 待评估 / 2 已评估 / 3 无需评估
  "offset": 0,
  "limit": 50                      // 50 稳定可用
}
```

响应：`data.evaluation_list[]`、`data.count`（总数）。
**`data.total_count` 恒为 0，不要用它**；分页到 `list.length < limit` 为止。

页签语义（重要）：
- `1 待评估` — 你还没评，投递活着 → **直接能给结论、能约面**
- `2 已评估` — 你给过结论了
- `3 无需评估` — **别人已经处理掉、你一次都没评过** → 这是「回捞池」
- `0 全部` ≈ 1 + 2 + 3

### 每条记录的关键字段

| 字段 | 含义 |
|---|---|
| `id` | **evaluation_id**，提交结论要用它 |
| `talent_id` | 人才 ID，拼详情页 URL 用 |
| `application_id` | 投递 ID |
| `talent.name` | 姓名 |
| `talent.under_graduate_school` / `under_graduate_major` | **本科**院校 / 专业（按本科判档就用这个） |
| `talent.graduate_school` / `graduate_major` / `graduate_year` | 最高学历院校 / 专业 / 毕业年（**year 脏，见下**） |
| `talent.top_degree_info.name` | 最高学历（本科 / 硕士 / 博士 / 其他） |
| `talent.first_degree.name` | 第一学历 |
| `talent.education_list[]` | `{degree, school, field_of_study, start_time, end_time}` 全部学历 |
| `talent.recent_company` / `recent_title` / `experience_years` | 最近公司 / 职位 / 年限 |
| `talent.current_city.name` | 所在地 |
| `talent.gender` / `gender_info` | **恒为 null**，见"性别"一节 |
| `job.name` | 投递岗位 |
| `application.stage.name` | **投递阶段**：已终止 / 简历初筛 / 简历评估 / 面试 / Offer / 待入职 / 已入职 |
| `application.resume_source.name` | 来源（官网 / 内推 / 招聘Agent / 人才库…） |
| `conclusion_info.name` | **我的**结论（未评估 / 通过 / 不通过） |
| `same_application_evaluation_list[]` | 同一投递其他评估人：`{evaluator.name, conclusion, termination_reason_list}` |
| `biz_create_time` | 进入评估任务的时间（毫秒）→ **判届次用这个** |

### 判届次

`graduate_year` 由候选人自填，同一届里 2026 / 2027 / 空混在一起。
可靠做法是按 `biz_create_time` 聚类：

```js
new Date(r.biz_create_time).toISOString().slice(0,7)   // 按月分桶
```

同一届校招的投递集中在同几天。先打印月份分布，选出当届那个桶，把口径讲给用户。

### 学校筛选枚举

页面上的「学校」筛选器 `v2_school.enum_list`：`"4"` = QS200。
这个标签是按**最高学历**院校打的，所以会放进一堆"本科普通、硕士冲上来"的人。
**按本科筛就不要依赖它**，直接 `filters: "{}"` 全量拉下来自己判。

## 2. 可选列定义（确认某字段到底有没有）

```
GET /atsx/api/evaluation/evaluation_list_header/?activity_status=0
```

返回 `header_list[]`，每项带 `id` / `name` / `data_field`。用来证明"这个字段系统里根本没有"。
已确认：**没有任何 gender / 性别 列**。

## 3. 简历全文（详情页）

```
https://mi.feishu.cn/hire/talent/<talent_id>
```

附件 PDF 已被平台解析成文本，直接读 `document.body.innerText` 就有全文。
轮询到长度稳定（连续两次相同且 > 1500）再取，否则会拿到半成品。

详情页独有、列表接口拿不到的信息：
- **其他投递（N）** 的历史评估记录：谁拒过、什么时候、评语原文
- 笔试成绩：能力倾向计算机自适应测验（分数）、知识型员工心理风险、定制化报告测验
- 报告入口：综合笔试报告、**2027届小米AI潜力模型报告**、GPI 个性报告
- 面试记录：轮次、面试官、时间、打分、能力考察记录原文
- 终止详情：终止前阶段 + 终止原因（筛选未通过 / 我们拒绝了候选人 / 其他）
- 平台给的标签：QS200 / QS100 / USNews100 / 985院校 / 211院校 / C9 / BAT / TMD / 互联网100强 / 内推 / 大使推荐

这些信息判断价值很高（比如"2023 年投过 7 个岗位全被拒"），读的时候要一并记下。

## 4. 提交评估结论（写操作）

```
POST /atsx/api/evaluation/evaluate/
{"conclusion": 1, "evaluation_id": "<id>"}
```

`conclusion`：`1` = 通过，`2` = 不通过。

UI 等价操作是两步：点「通过」（按钮变绿带勾）→ 评价框（**非必填**）→ 点「提交」。
只点「通过」不点「提交」不会发出任何请求。

UI 路径的两个坑：
- `getByRole('button', {name:'提交'})` 会 **matched 2 elements**（有个隐藏的同名按钮）。
  用 `[...document.querySelectorAll('button')].filter(b=>b.innerText.trim()==='提交' && b.getBoundingClientRect().width>0)` 取到真实那个，再 `page.mouse.click(x, y)`。
- 页面上只有一对「通过 / 不通过」按钮，父节点 innerText 是 `"<你的名字> | 通过 | 不通过"`。点前先验证这个上下文，别点到历史评估记录里的文字。

提交后**必须复查**：

```js
// 用 list_v2 activity_status=2 查 conclusion_info.name 是否已变成「通过」
```

## 5. 权限边界

「候选人」模块 `/hire/application/list` 是全量投递视图（能直接约面、能跨阶段搜）。

```
POST /atsx/api/application/list_v4/
{"q":"","filters":"{}","sidebar_search_info":{"job_active_status":1,...},
 "job_process_id":"<流程id>","list_type":1,"stage_id":"<阶段id>","limit":20,"offset":0}
```

**对只挂面试官角色的账号，所有阶段都返回 `count: 0`** —— 因为它只显示你作为招聘负责人的职位。
可用池就是「我的任务 / 简历评估」那几个页签。上手先确认，别在这里浪费一轮。

招聘流程与阶段 ID：

```
GET /atsx/api/application/list_job_process_for_switch/?switch_scene=2
```

常规校招流程 `7178028100281057388`，阶段：简历初筛 / 测评 / 笔试 / 简历评估 / 面试 / 加面 / 面试通过 / offer意向 / Offer / 签约中 / 待入职 / 已入职。

## 性别：系统里没有

这个租户**不采集性别**：

- `talent.gender` 和 `talent.gender_info` 在全量记录里 **100% 为 null**
- 候选人详情页没有性别栏
- `evaluation_list_header` 的可选列里也没有

所以"男性优先"这类排序只能**按姓名推测**。要求：

1. 报告里明确标注"性别为姓名推测"
2. 判不准的标 `?` 并给出人数
3. 少数简历正文里自己写了性别（`性别：女`、`23 岁｜女`、英文名 Jessica/Jason 之类）——这些可以标 ✓ 表示已确认，其余保持"推测"
4. 不要把推测当事实写进结论

## 其他易错点

| 现象 | 处理 |
|---|---|
| `page.evaluate` 里串了十几个 fetch → `Runtime.evaluate timed out` | 拆成每次 2–3 个请求 |
| `browser.selectTab is not a function` | 正确方法名是 `browser.switchTab(targetId)` |
| `require is not defined` | browser nodejs 里用 `await import('node:fs')` |
| 简历只抓到 12 个字符（"该人才不存在"） | talent_id 用错了；别把 `education_list[].id` 当 talent_id |
| 同一人多条记录 | 按 `talent_id` 去重，但每条投递的 `stage` 要分别保留 |
| 截图翻页后全白 | file:// 与滚动后的合成问题；用 `page.evaluate` 读 DOM 验证内容，或临时 `display:none` 掉首屏再截 |
