#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成单文件 HTML 筛选报告（Swiss 视觉系统）。

用法
----
1. 人工阅读简历后，写一份 verdicts.py 放在 workdir，内容：

    GENDER = {"张三": "男", "李四": "女✓", "王五": "?"}     # ✓ = 简历正文写明
    TIERS  = [("s", "S 档 · 今天就面", "判定标准一句话"),
              ("a", "A 档 · 值得面",  "..."),
              ("b", "B 档 · 可以看",  "..."),
              ("c", "C 档 · 建议过",  "...")]
    # name -> (tier, ai, hot, why, risk)   ai ∈ core|strong|touch|none
    VERDICTS = {"张三": ("s", "core", True, "为什么进（带数字）", "短板")}
    META = {"title": "...", "eyebrow": "...", "lede": "...", "tldr": "...",
            "stats": [("34", "待评估总数"), ("8", "S 档")],
            "notes": [("小标题", "正文 HTML 片段")]}

2. python3 scripts/build_report.py candidates.json out.html

校验
----
每个人都必须有 why 和 risk；缺 risk 会告警但不阻塞（用户明确说不需要时可忽略）。
"""
import json, sys, os, html, importlib.util, pathlib

sys.path.insert(0, os.getcwd())   # 让 verdicts.py 能 import workdir 里的同级模块

AIL = {'core': ('AI 核心', 'core'), 'strong': ('AI 强', 'strong'),
       'touch': ('AI 有接触', 'touch'), 'none': ('AI 无', 'none')}
AR = {'core': 0, 'strong': 1, 'touch': 2, 'none': 3}
GR = {'男': 0, '男✓': 0, '?': 1, '女': 2, '女✓': 2}
e = html.escape

CSS = """:root{--klein:#002FA7;--lemon:#FFED00;--lgreen:#B5DF4A;--orange:#FF6B00;--ink:#111;--mute:#666;
--bg:#fafaf7;--card:#fff;--code-bg:#efefe9;
--sans:"Noto Sans SC","Helvetica Neue",Inter,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
--mono:"SF Mono","JetBrains Mono",Menlo,Consolas,"PingFang SC",monospace}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font-family:var(--sans);font-size:15px;line-height:1.58;color:var(--ink);background:var(--bg);-webkit-font-smoothing:antialiased}
.wrap{max-width:1320px;margin:0 auto;padding:0 5vw}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--mute)}
h1.title{font-size:clamp(32px,5.2vw,62px);font-weight:900;line-height:1.03;letter-spacing:-.02em;margin:14px 0 0;text-align:left}
h1.title em{font-style:italic;color:var(--klein);font-weight:900}
header.hero{padding:52px 0 30px}.lede{max-width:76ch;margin:18px 0 0;font-size:16px;color:#333}
.tldr{display:grid;grid-template-columns:110px 1fr;gap:22px;padding:22px;background:var(--lemon);border:2px solid var(--ink);margin:28px 0 0}
.tldr .label{font-family:var(--mono);font-size:11px;letter-spacing:.2em;font-weight:700;text-transform:uppercase}
.tldr .body{font-size:16px;line-height:1.62}
.tldr .body strong{background:var(--ink);color:var(--lemon);padding:1px 6px;font-weight:700}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));border:2px solid var(--ink);border-right:0;margin:26px 0 0;background:var(--card)}
.stat{padding:16px 18px;border-right:2px solid var(--ink)}
.stat b{display:block;font-size:34px;font-weight:900;letter-spacing:-.03em;line-height:1;color:var(--klein)}
.stat span{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--mute)}
nav.jump{position:sticky;top:0;z-index:20;background:var(--card);border-top:2px solid var(--ink);border-bottom:2px solid var(--ink);margin-top:34px}
nav.jump .inner{max-width:1320px;margin:0 auto;padding:11px 5vw;display:flex;gap:8px;flex-wrap:wrap}
nav.jump a{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-decoration:none;color:var(--ink);border:1px solid var(--ink);padding:5px 10px}
nav.jump a:hover,nav.jump a.on{background:var(--klein);color:#fff;border-color:var(--klein)}
section{padding:46px 0 40px;border-bottom:1px solid var(--ink)}
.sec-head{display:flex;gap:18px;align-items:flex-start;margin-bottom:8px}
.section-num{font-size:44px;font-weight:900;color:var(--klein);letter-spacing:-.04em;line-height:.9;min-width:52px}
.section-title{font-size:27px;font-weight:800;letter-spacing:-.01em;margin:0}
.sec-sub{color:var(--mute);font-size:14px;margin:4px 0 0;max-width:80ch}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(430px,1fr));gap:18px;margin-top:26px}
.card{background:var(--card);border:2px solid var(--ink);padding:18px;transition:transform .12s,box-shadow .12s}
.card:hover{transform:translateY(-2px);box-shadow:6px 6px 0 var(--klein)}
.card-top{display:flex;align-items:center;gap:9px}
.card h3{margin:0;font-size:22px;font-weight:900;letter-spacing:-.01em}
.card .gender{font-family:var(--mono);font-size:12px;color:var(--mute)}
.tags{display:flex;gap:6px;flex-wrap:wrap;margin:9px 0 0}
.tag{font-family:var(--mono);font-size:10px;letter-spacing:.08em;padding:3px 7px;border:1px solid var(--ink);white-space:nowrap}
.tag-core{background:var(--klein);color:#fff;border-color:var(--klein);font-weight:700}
.tag-strong{background:var(--lemon)}.tag-touch{background:#fff;color:var(--mute)}
.tag-none{background:#fff;color:#bbb;border-color:#ddd}
.tag-hot{background:var(--orange);color:#fff;border-color:var(--orange);font-weight:700}
.chip{font-family:var(--mono);font-size:10px;font-weight:700;padding:3px 7px;border:1.5px solid var(--ink);letter-spacing:.06em}
.card .edu{margin:12px 0 0;font-size:13.5px;line-height:1.55;padding:10px;background:var(--code-bg)}
.card .edu b{font-family:var(--mono);font-size:10px;letter-spacing:.1em;color:var(--mute);margin-right:4px}
.card .evi{margin:11px 0 0;font-size:13.5px;line-height:1.68;color:#222}
.card .risk{margin:9px 0 0;font-size:12.5px;line-height:1.6;color:#8a4a00;border-left:3px solid var(--orange);padding-left:9px}
.card .risk b{font-family:var(--mono);font-size:10px;letter-spacing:.1em;color:var(--orange);margin-right:4px}
.filters{display:flex;gap:7px;flex-wrap:wrap;margin:22px 0 0;align-items:center}
.filters .lb{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--mute);margin-right:2px}
.pill{font-family:var(--mono);font-size:11px;padding:5px 11px;border:1.5px solid var(--ink);background:#fff;cursor:pointer}
.pill.on{background:var(--klein);color:#fff;border-color:var(--klein)}
.tbl-wrap{overflow-x:auto;margin-top:20px;border:2px solid var(--ink);background:var(--card)}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:980px}
th{background:var(--ink);color:#fff;font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;padding:10px 9px;text-align:left;font-weight:500;cursor:pointer;white-space:nowrap}
th:hover{background:var(--klein)}
td{padding:10px 9px;border-bottom:1px solid #e4e4de;vertical-align:top}
tr:hover td{background:#f4f4ee}td.nm{font-weight:700;font-size:14px;white-space:nowrap}
.sub{color:var(--mute);font-size:11.5px}
.notes{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:16px;margin-top:22px}
.note{background:var(--card);border:1px solid var(--ink);padding:16px}
.note h4{margin:0 0 7px;font-family:var(--mono);font-size:11px;letter-spacing:.12em;color:var(--klein)}
.note p,.note ul{margin:0;font-size:13.5px;line-height:1.62;color:#333}.note ul{padding-left:17px}
footer{padding:34px 0 60px;color:var(--mute);font-size:12.5px;font-family:var(--mono)}
.count{font-family:var(--mono);font-size:11px;color:var(--mute);margin-left:6px}
@media(max-width:640px){.tldr{grid-template-columns:1fr;gap:10px}.cards{grid-template-columns:1fr}}"""

JS = """(function(){var F={tier:'all',ai:'all',g:'all'};
var tb=document.querySelector('#t tbody'),rs=[].slice.call(tb.rows),c=document.getElementById('cnt');
function ap(){var n=0;rs.forEach(function(r){var ok=(F.tier==='all'||r.dataset.tier===F.tier)&&(F.ai==='all'||r.dataset.ai===F.ai)&&(F.g==='all'||r.dataset.g===F.g);r.style.display=ok?'':'none';if(ok)n++;});c.textContent='当前显示 '+n+' 人';}
document.querySelectorAll('.pill').forEach(function(p){p.addEventListener('click',function(){var f=p.dataset.f;document.querySelectorAll('.pill[data-f="'+f+'"]').forEach(function(q){q.classList.remove('on');});p.classList.add('on');F[f]=p.dataset.v;ap();});});ap();
var d={};document.querySelectorAll('#t th').forEach(function(th){th.addEventListener('click',function(){var k=+th.dataset.k;d[k]=!d[k];
var s=rs.slice().sort(function(a,b){var x=a.cells[k].innerText.trim(),y=b.cells[k].innerText.trim();var nx=parseFloat(x),ny=parseFloat(y);var cc=(!isNaN(nx)&&!isNaN(ny))?nx-ny:x.localeCompare(y,'zh');return d[k]?cc:-cc;});
s.forEach(function(r){tb.appendChild(r);});});});
var se=[].slice.call(document.querySelectorAll('section')),lk=[].slice.call(document.querySelectorAll('nav.jump a'));
window.addEventListener('scroll',function(){var y=window.scrollY+120,i0=0;se.forEach(function(s,i){if(s.offsetTop<=y)i0=i;});lk.forEach(function(l,i){l.classList.toggle('on',i===i0);});});})();"""


def gkey(g):
    return 'm' if g.startswith('男') else ('f' if g.startswith('女') else 'u')


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else 'candidates.json'
    out = sys.argv[2] if len(sys.argv) > 2 else 'report.html'
    spec = importlib.util.spec_from_file_location('v', 'verdicts.py')
    v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)

    pool = {}
    for r in json.load(open(src)):
        pool.setdefault(r['name'], r)

    missing = [n for n in v.VERDICTS if n not in pool]
    unjudged = [n for n in pool if n not in v.VERDICTS]
    if missing: print('⚠ VERDICTS 里有名单外的人:', missing)
    if unjudged: print('⚠ 名单里有没打标的人（会被漏报）:', unjudged)
    norisk = [n for n, t in v.VERDICTS.items() if not t[4]]
    if norisk: print('⚠ 缺「短板」:', norisk)

    TR = {k: i for i, (k, _, _) in enumerate(v.TIERS)}
    rows = []
    for n, (tier, ai, hot, why, risk) in v.VERDICTS.items():
        t = pool.get(n, {})
        rows.append(dict(name=n, g=v.GENDER.get(n, '?'), tier=tier, ai=ai, hot=hot, why=why, risk=risk,
                         ug=t.get('ug'), ugMajor=t.get('ugMajor'), grad=t.get('grad'),
                         gradMajor=t.get('gradMajor'), gy=t.get('gradYear'), top=t.get('topDegree')))
    rows.sort(key=lambda r: (TR[r['tier']], AR[r['ai']], GR.get(r['g'], 1), r['name']))

    def card(r):
        lbl, cls = AIL[r['ai']]
        hot = '<span class="tag tag-hot">🔥 自驱</span>' if r['hot'] else ''
        risk = f'<p class="risk"><b>短板</b> {e(r["risk"])}</p>' if r['risk'] else ''
        top = r['top'] or '—'
        return (f'<article class="card" data-ai="{r["ai"]}" data-g="{gkey(r["g"])}" data-tier="{r["tier"]}">'
                f'<header><div class="card-top"><h3>{e(r["name"])}</h3>'
                f'<span class="gender">{e(r["g"])}</span></div>'
                f'<div class="tags"><span class="tag tag-{cls}">{lbl}</span>{hot}</div></header>'
                f'<div class="edu"><b>本科</b> {e(r["ug"] or "—")} · {e(r["ugMajor"] or "—")}<br>'
                f'<b>{"最高" if top in ("本科","其他") else "研究生"}</b> {e(r["grad"] or "—")} · '
                f'{e(r["gradMajor"] or "—")} · {e(top)} · {e(str(r["gy"] or "—"))} 毕业</div>'
                f'<p class="evi">{e(r["why"])}</p>{risk}</article>')

    secs, nav = [], []
    for i, (key, title, sub) in enumerate(v.TIERS, 1):
        g = [r for r in rows if r['tier'] == key]
        if not g: continue
        nav.append(f'<a href="#s{i}">{i:02d} {e(title)}</a>')
        secs.append(f'<section id="s{i}"><div class="sec-head"><div class="section-num">{i:02d}</div>'
                    f'<div><h2 class="section-title">{e(title)} · {len(g)} 人</h2>'
                    f'<p class="sec-sub">{e(sub)}</p></div></div>'
                    f'<div class="cards">{"".join(card(r) for r in g)}</div></section>')
    ntbl = len(v.TIERS) + 1
    nav.append(f'<a href="#s{ntbl}">{ntbl:02d} 全量表</a>')
    nav.append(f'<a href="#s{ntbl+1}">{ntbl+1:02d} 口径</a>')

    tbl = ''.join(
        f'<tr data-ai="{r["ai"]}" data-g="{gkey(r["g"])}" data-tier="{r["tier"]}">'
        f'<td><span class="chip">{r["tier"].upper()}</span></td>'
        f'<td class="nm">{e(r["name"])}{" 🔥" if r["hot"] else ""}</td><td>{e(r["g"])}</td>'
        f'<td><span class="tag tag-{AIL[r["ai"]][1]}">{AIL[r["ai"]][0]}</span></td>'
        f'<td>{e(r["ug"] or "—")}<br><span class="sub">{e(r["ugMajor"] or "—")}</span></td>'
        f'<td>{e(r["grad"] or "—")}<br><span class="sub">{e(r["gradMajor"] or "—")} · {e(r["top"] or "—")}</span></td>'
        f'<td>{e(str(r["gy"] or "—"))}</td></tr>' for r in rows)

    M = v.META
    pills = lambda f, opts: ''.join(
        f'<button class="pill{" on" if i == 0 else ""}" data-f="{f}" data-v="{val}">{e(txt)}</button>'
        for i, (val, txt) in enumerate(opts))
    tier_opts = [('all', '全部')] + [(k, f'{t.split("·")[0].strip()} · {len([r for r in rows if r["tier"]==k])}')
                                     for k, t, _ in v.TIERS]

    doc = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(M["title"])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;900&family=Noto+Serif+SC:wght@400;700;900&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="wrap"><header class="hero">
<div class="eyebrow">{e(M["eyebrow"])}</div><h1 class="title">{M["title_html"] if "title_html" in M else e(M["title"])}</h1>
<p class="lede">{M["lede"]}</p>
<div class="tldr"><div class="label">TL;DR</div><div class="body">{M["tldr"]}</div></div>
<div class="stats">{"".join(f'<div class="stat"><b>{e(a)}</b><span>{e(b)}</span></div>' for a, b in M["stats"])}</div>
</header></div><nav class="jump"><div class="inner">{"".join(nav)}</div></nav><div class="wrap">
{"".join(secs)}
<section id="s{ntbl}"><div class="sec-head"><div class="section-num">{ntbl:02d}</div><div>
<h2 class="section-title">全量表 · {len(rows)} 人</h2>
<p class="sec-sub">默认排序：档位 → AI 强度 → 男性优先。点表头换排序，点胶囊组合筛选。<span class="count" id="cnt"></span></p>
</div></div>
<div class="filters"><span class="lb">档位</span>{pills('tier', tier_opts)}</div>
<div class="filters"><span class="lb">AI</span>{pills('ai', [('all','全部'),('core','AI 核心'),('strong','AI 强'),('touch','有接触'),('none','无')])}</div>
<div class="filters"><span class="lb">性别</span>{pills('g', [('all','不限'),('m','男'),('f','女'),('u','未判定')])}</div>
<div class="tbl-wrap"><table id="t"><thead><tr>
<th data-k="0">档</th><th data-k="1">姓名</th><th data-k="2">性别*</th><th data-k="3">AI</th>
<th data-k="4">本科</th><th data-k="5">研究生 / 最高学历</th><th data-k="6">毕业</th>
</tr></thead><tbody>{tbl}</tbody></table></div></section>
<section id="s{ntbl+1}"><div class="sec-head"><div class="section-num">{ntbl+1:02d}</div>
<div><h2 class="section-title">口径与边界</h2></div></div>
<div class="notes">{"".join(f'<div class="note"><h4>{e(h)}</h4>{b}</div>' for h, b in M["notes"])}</div></section>
<footer>{M.get("footer", "数据源 飞书招聘 /atsx/api/evaluation/list_v2/ · 简历全文逐份抓取 · 性别列为姓名推测 · 分档为人工阅读判定")}</footer>
</div><script>{JS}</script></body></html>"""

    pathlib.Path(out).write_text(doc, encoding='utf-8')
    dist = {k: len([r for r in rows if r['tier'] == k]) for k, _, _ in v.TIERS}
    print(f'wrote {out}  {len(rows)} 人  {dist}  {len(doc)} bytes')


if __name__ == '__main__':
    main()
