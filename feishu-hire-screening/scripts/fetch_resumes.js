// 批量抓候选人简历全文（详情页 innerText，PDF 已被平台解析成文本）。
// 用法：反复跑到打印 "todo 0" 为止（可断点续跑，结果 append 到 jsonl）
//   multica browser nodejs < scripts/fetch_resumes.js
//
// hire_task.json 追加字段：
//   { "resumeIn": "candidates.json",     // 目标名单，需含 talentId / name
//     "resumeOut": "resumes.jsonl",
//     "batch": 14 }                      // 单次抓多少份，14 份约 90 秒
//
// ⚠ cwd 注意：`multica browser nodejs` 的 cwd 恒为**任务 workdir**（不是你 shell 的 cwd），
//   环境变量也不会传进来。所以 hire_task.json 必须写在任务 workdir 根目录下。
//   脚本里打印了实际 cwd，报错时先看这一行。
//
// 注意：talentId 必须是 talent_id，不要误用 education_list[].id —— 会抓到「该人才不存在」。

const fs = await import('node:fs');
console.log('cwd =', process.cwd());
if (!fs.existsSync('./hire_task.json')) {
  throw new Error('当前 cwd 下没有 hire_task.json。cwd = ' + process.cwd() +
                  '  → 把 hire_task.json 写到这个目录里（browser nodejs 的 cwd 恒为任务 workdir）');
}
const CFG = JSON.parse(fs.readFileSync('./hire_task.json', 'utf8'));
const IN = CFG.resumeIn ?? 'candidates.json';
const OUT = CFG.resumeOut ?? 'resumes.jsonl';
const BATCH = CFG.batch ?? 14;

const targets = JSON.parse(fs.readFileSync(IN, 'utf8'));
const done = new Set();
if (fs.existsSync(OUT)) {
  for (const line of fs.readFileSync(OUT, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    try { done.add(JSON.parse(line).talentId); } catch (e) { /* 跳过坏行 */ }
  }
}
const seen = new Set();
const todo = targets.filter(t => {
  if (!t.talentId || done.has(t.talentId) || seen.has(t.talentId)) return false;
  seen.add(t.talentId); return true;
});
console.log('done', done.size, 'todo', todo.length);
if (!todo.length) { console.log('全部抓完'); }

if (todo.length) {
  await browser.openOrReuseTab('https://mi.feishu.cn/hire/talent/' + todo[0].talentId);
  await new Promise(r => setTimeout(r, 2500));

  for (const t of todo.slice(0, BATCH)) {
    let txt = '';
    try {
      await page.goto('https://mi.feishu.cn/hire/talent/' + t.talentId);
      let prev = -1;
      for (let i = 0; i < 10; i++) {
        await new Promise(r => setTimeout(r, 1100));
        const cur = await page.evaluate(() => document.body.innerText);
        if (cur.length > 1500 && cur.length === prev) { txt = cur; break; }  // 长度稳定才算读完
        prev = cur.length; txt = cur;
      }
    } catch (e) {
      txt = 'ERR:' + String(e).slice(0, 200);
    }
    fs.appendFileSync(OUT, JSON.stringify({ talentId: t.talentId, name: t.name, len: txt.length, txt }) + '\n');
    const flag = txt.length < 500 ? '  ← 异常，检查 talentId' : '';
    console.log(t.name, txt.length, flag);
  }
  console.log('batch finished; 再跑一次继续剩下的');
}
