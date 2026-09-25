// 全量拉取飞书招聘「简历评估」列表。
// 用法：在 workdir 写 ./hire_task.json，然后
//   multica browser nodejs < scripts/fetch_evaluation_list.js
//
// hire_task.json:
//   { "activityStatus": 1,          // 0 全部 / 1 待评估 / 2 已评估 / 3 无需评估
//     "filters": "{}",              // 字符串化 JSON；学校 QS200 = {"v2_school":{"enum_list":["4"]}}
//     "out": "candidates.json" }
//
// ⚠ cwd 注意：`multica browser nodejs` 的 cwd 恒为**任务 workdir**（不是你 shell 的 cwd），
//   环境变量也不会传进来。所以 hire_task.json 必须写在任务 workdir 根目录下。
//   脚本里打印了实际 cwd，报错时先看这一行。
//
// 前置：当前 tab 必须停在 mi.feishu.cn/hire 下任意已登录页面（接口用相对路径 + Cookie）。

const fs = await import('node:fs');
console.log('cwd =', process.cwd());
if (!fs.existsSync('./hire_task.json')) {
  throw new Error('当前 cwd 下没有 hire_task.json。cwd = ' + process.cwd() +
                  '  → 把 hire_task.json 写到这个目录里（browser nodejs 的 cwd 恒为任务 workdir）');
}
const CFG = JSON.parse(fs.readFileSync('./hire_task.json', 'utf8'));
const ST = CFG.activityStatus ?? 0;
const FILTERS = CFG.filters ?? '{}';
const OUT = CFG.out ?? 'candidates.json';

const tabs = await browser.listTabs();
const hire = tabs.find(t => /mi\.feishu\.cn\/hire/.test(t.url));
if (!hire) throw new Error('没有已登录的飞书招聘标签页，先打开 mi.feishu.cn/hire');
await browser.switchTab(hire.targetId);
await new Promise(r => setTimeout(r, 800));
console.log('on', await page.url());

const all = [];
for (let off = 0; off < 5000; off += 50) {
  const r = await page.evaluate(async (a) => {
    const resp = await fetch('/atsx/api/evaluation/list_v2/', {
      method: 'POST',
      headers: { 'content-type': 'application/json;charset=UTF-8', 'accept': 'application/json', 'x-requested-with': 'XMLHttpRequest' },
      body: JSON.stringify({ q: '', filters: a.f, activity_status: a.st, offset: a.off, limit: 50 })
    });
    const j = await resp.json();
    if (!j.success) return { err: j.message || 'request failed' };
    return {
      count: j.data.count,
      n: j.data.evaluation_list.length,
      rows: j.data.evaluation_list.map(it => {
        const t = it.talent || {};
        return {
          evalId: it.id, talentId: it.talent_id, appId: it.application_id,
          name: t.name,
          gender: t.gender, genderInfo: t.gender_info && t.gender_info.name,   // 该租户恒为 null
          ug: t.under_graduate_school, ugMajor: t.under_graduate_major,
          grad: t.graduate_school, gradMajor: t.graduate_major, gradYear: t.graduate_year,
          topDegree: t.top_degree_info && t.top_degree_info.name,
          firstDegree: t.first_degree && t.first_degree.name,
          edu: (t.education_list || []).map(e => ({ d: e.degree, s: e.school, m: e.field_of_study, st: e.start_time, et: e.end_time })),
          company: t.recent_company, title: t.recent_title, exp: t.experience_years,
          city: t.current_city && t.current_city.name,
          job: it.job && (it.job.name || it.job.title),
          stage: it.application && it.application.stage && it.application.stage.name,
          source: it.application && it.application.resume_source && it.application.resume_source.name,
          myConcl: it.conclusion_info && it.conclusion_info.name,
          others: (it.same_application_evaluation_list || []).map(x => ({
            who: x.evaluator && x.evaluator.name, c: x.conclusion,
            reason: (x.termination_reason_list || []).map(y => y.name)
          })),
          created: it.biz_create_time
        };
      })
    };
  }, { st: ST, f: FILTERS, off });

  if (r.err) { console.log('ERR at offset', off, r.err); break; }
  all.push(...r.rows);
  console.log('offset', off, 'got', r.n, '/ total', r.count);
  if (r.n < 50) break;
}

fs.writeFileSync(OUT, JSON.stringify(all, null, 1));

// 去重 + 届次分布，方便立刻判口径
const uniq = new Map();
for (const r of all) if (!uniq.has(r.talentId)) uniq.set(r.talentId, r);
const bucket = {}, stage = {}, gy = {};
for (const r of uniq.values()) {
  const m = r.created ? new Date(r.created).toISOString().slice(0, 7) : 'unknown';
  bucket[m] = (bucket[m] || 0) + 1;
  stage[r.stage] = (stage[r.stage] || 0) + 1;
  gy[r.gradYear] = (gy[r.gradYear] || 0) + 1;
}
console.log('\nsaved', all.length, 'records →', OUT, '| unique talents', uniq.size);
console.log('投递批次(按月，判届次用这个):', JSON.stringify(bucket));
console.log('投递阶段:', JSON.stringify(stage));
console.log('graduate_year(脏,仅参考):', JSON.stringify(gy));
console.log('gender 非空条数:', all.filter(x => x.gender != null || x.genderInfo != null).length, '(该租户预期为 0)');
