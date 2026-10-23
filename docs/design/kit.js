// Axolotl mock screens. Static design mocks only, never shipped. Fixture story matches demo/legacy_orders:
// pricing attempt 1 swaps quantize(ROUND_HALF_UP) for round() -> half-even, differential 5 of 7 held-out + impacted 2 held-out differ (7 counterexamples, hcase_001 exposed); attempt 2 passes.
// Case IDs and counts come from demo/challenge_cases/held_out.json and verification/__init__.py gate order.
// Runtime figures on the report are illustrative until RunReport carries them.
const I = (n, c = '') => `<svg class="ic ${c}" viewBox="0 0 256 256" aria-hidden="true">${ICONS[n].map(d => `<path d="${d}"/>`).join('')}</svg>`;

const ST = {
  not_planned: ['circle-dashed', 'Not planned', 'neutral'], queued: ['circle', 'Queued', 'neutral'],
  baselining: ['circle-half', 'Baselining', 'working'], migrating: ['pencil-simple', 'Migrating', 'working'],
  verifying: ['hourglass', 'Verifying', 'working'], repairing: ['arrow-clockwise', 'Repairing', 'repairing'],
  passed: ['check-circle', 'Passed', 'passed'], blocked: ['prohibit', 'Blocked', 'failed'],
  failed: ['x-circle', 'Failed', 'failed'], skipped: ['arrow-bend-down-right', 'Skipped', 'neutral'],
};
const RUN = { ...ST, final_verification: ['list-checks', 'Final verification', 'working'],
  completed: ['check-circle', 'Completed', 'passed'], completed_with_warnings: ['warning', 'Completed with warnings', 'warning'],
  cancelled: ['minus-circle', 'Cancelled', 'neutral'] };
const badge = s => `<span class="badge s-${ST[s][2]}">${I(ST[s][0])}${ST[s][1]}</span>`;
const runstate = s => `<span class="runstate s-${RUN[s][2]}">${I(RUN[s][0], 'ic20')}${RUN[s][1]}</span>`;
const btn = (l, v = 'secondary', x = '') => `<span class="btn ${v} ${x}">${l}</span>`;
const kv = (k, v, vc = '') => `<div class="col"><span class="lbl">${k}</span><span class="${vc}">${v}</span></div>`;

// ---------- shell
const SYS_OK = [['ok', 'MongoDB'], ['ok', 'Search indexes'], ['ok', 'Runner'], ['ok', 'Gemini']];
const chip = ([s, n]) => `<span class="chip ${s}">${I({ ok: 'check-circle', building: 'hourglass', unavailable: 'x-circle' }[s])}<span>${n}</span><span class="st">${s}</span></span>`;
const appbar = ({ repo = true, progress, sys = SYS_OK }) => `<header class="appbar">
  <div class="row g12"><span class="med">Axolotl</span>${repo ? `<span class="div"></span><span class="mono med">legacy_orders</span>` : ''}</div>
  <div class="row g24">${progress ? `<span class="row g8 med">${I('list-checks', 'ic20')}${progress}</span>` : ''}<div class="row g8">${sys.map(chip).join('')}</div></div></header>`;
const TABS = ['Overview', 'Graph', 'Plan', 'Run', 'Report', 'Search'];
const nav = (tab, right = '') => `<nav class="nav"><div class="tabs">${TABS.map(t => `<span class="tab${t === tab ? ' on' : ''}">${t}</span>`).join('')}</div><span class="sp"></span><div class="row g12">${right}</div></nav>`;
const frame = ({ w, h, tab, right, banner = '', body, ...bar }) =>
  `<div class="app" style="width:${w}px;height:${h}px">${appbar(bar)}${tab ? nav(tab, right) : ''}${banner}<div class="body">${body}</div></div>`;
const field = (v, { w = 280, ph = false, icon = true, key = true, x = '' } = {}) =>
  `<span class="field ${x}" style="width:${w}px">${icon ? I('magnifying-glass', 'muted') : ''}<span class="${ph ? 'ph' : 'fill'}">${v}</span>${key ? '<span class="kbd">/</span>' : ''}</span>`;

// ---------- graph
const POS = { 'main.py': [224, 0], 'orders.py': [112, 150], 'refunds.py': [336, 150], 'customers.py': [0, 300], 'pricing.py': [224, 300], 'storage.py': [448, 300] };
const GW = 638, GH = 358;
const EDGES = [['main.py', 'orders.py'], ['main.py', 'refunds.py'], ['orders.py', 'customers.py'], ['orders.py', 'pricing.py'], ['orders.py', 'storage.py'],
  ['refunds.py', 'pricing.py'], ['refunds.py', 'storage.py']];
const DEPENDANTS = n => EDGES.filter(e => e[1] === n).map(e => e[0]);
const box = n => { const [x, y] = POS[n]; return { x, y, w: 190, h: 58 } };
function edgeSvg(lit, dimmed) {
  const spread = (list, i) => (i - (list.length - 1) / 2) * 32;
  return EDGES.map(([s, t]) => {
    const a = box(s), b = box(t);
    const outs = EDGES.filter(e => e[0] === s).sort((p, q) => POS[p[1]][0] - POS[q[1]][0]);
    const ins = EDGES.filter(e => e[1] === t).sort((p, q) => POS[p[0]][0] - POS[q[0]][0]);
    const sx = a.x + a.w / 2 + spread(outs, outs.findIndex(e => e[1] === t)), sy = a.y + a.h;
    const ex = b.x + b.w / 2 + spread(ins, ins.findIndex(e => e[0] === s)), ey = b.y - 2;
    const on = lit.includes(`${s}>${t}`), L = Math.hypot(ex - sx, ey - sy), ux = (ex - sx) / L, uy = (ey - sy) / L;
    const ah = on ? 12 : 9, aw = on ? 6 : 4.5, bx = ex - ux * ah, by = ey - uy * ah;
    const col = on ? 'var(--ink)' : dimmed ? 'var(--border-strong)' : 'var(--muted)';
    return `<g><line x1="${sx}" y1="${sy}" x2="${bx}" y2="${by}" style="stroke:${col};stroke-width:${on ? 3 : 1.5}"/>` +
      `<polygon points="${ex},${ey} ${bx - uy * aw},${by + ux * aw} ${bx + uy * aw},${by - ux * aw}" style="fill:${col}"/></g>`;
  }).join('');
}
function node(n, { state = 'not_planned', sel, dim, att, sk }) {
  const b = box(n), at = `left:${b.x}px;top:${b.y}px`;
  if (sk) return `<div class="sk" style="position:absolute;${at};width:${b.w}px;height:${b.h}px;border-radius:6px"></div>`;
  const [ic, label, col] = ST[state];
  return `<div class="node st-${state} s-${col}${sel ? ' sel' : ''}${dim ? ' dim' : ''}" style="${at};--sc:var(--${col})" tabindex="0">` +
    `<span class="nm">${n}</span><span class="st">${I(ic)}${label}${att ? `<span class="att">Attempt ${att}</span>` : ''}</span></div>`;
}
const legendLine = (dash, col, wgt) => `<svg width="32" height="16"><line x1="0" y1="8" x2="24" y2="8" style="stroke:${col};stroke-width:${wgt};${dash ? `stroke-dasharray:${dash}` : ''}"/><polygon points="32,8 23,${8 - wgt * 2 - 1.5} 23,${8 + wgt * 2 + 1.5}" style="fill:${col}"/></svg>`;
const LEGEND = `<div class="legend"><span class="semi">A → B: A imports B</span>
  <span class="row g8">${legendLine('', 'var(--muted)', 1.5)}Confirmed</span><span class="row g8">${legendLine('6 4', 'var(--muted)', 1.5)}Heuristic</span>
  <span class="row g8">${legendLine('2 3', 'var(--border-strong)', 1.5)}Unresolved</span><span class="row g8">${legendLine('', 'var(--ink)', 3)}Linked to selection</span></div>`;
const ZOOM = `<div class="zoom"><span class="iconbtn" aria-label="Zoom in">${I('plus', 'ic20')}</span><span class="iconbtn" aria-label="Zoom out">${I('minus', 'ic20')}</span><span class="iconbtn" aria-label="Fit graph to view">${I('corners-out', 'ic20')}</span></div>`;
function graph(w, h, { states = {}, selected, att = {}, sk = false, legend = true } = {}) {
  const deps = selected ? DEPENDANTS(selected) : [], lit = deps.map(d => `${d}>${selected}`);
  const dim = n => selected && n !== selected && !deps.includes(n);
  const room = legend ? 68 : 24, s = Math.min(1, (w - 48) / GW, (h - room - 24) / GH);
  const x = (w - GW * s) / 2, y = 24 + (h - room - 24 - GH * s) / 2;
  return `<div class="canvas" style="width:${w}px;flex:none"><div class="graph" style="left:${x}px;top:${y}px;width:${GW}px;height:${GH}px;transform:scale(${s})">
    ${sk ? '' : `<svg width="${GW}" height="${GH}">${edgeSvg(lit, !!selected)}</svg>`}
    ${Object.keys(POS).map(n => node(n, { state: states[n], sel: n === selected, dim: dim(n), att: att[n], sk })).join('')}
  </div>${legend && !sk ? LEGEND + (w < 830 ? ZOOM.replace('class="zoom"', 'class="zoom" style="top:16px;bottom:auto"') : ZOOM) : ''}</div>`;
}

// ---------- shared panels
const RISK = `<div class="sec"><span class="lbl">Risk</span><span class="med">High</span>
  <ul class="meta muted" style="padding-left:18px"><li>Rounds money with Decimal, half up, twice</li><li>Imported by orders.py and refunds.py</li></ul></div>`;
const FUNCS = (selSym) => `<div class="sec"><span class="lbl">Functions and classes</span>
  ${[['discount_rate', 'lines 25–35'], ['line_gross', 'lines 38–45'], ['finalise_amount', 'lines 48–106']].map(([f, l]) =>
    `<div class="kv" style="${f === selSym ? 'background:var(--neutral-tint);margin:0 -8px;padding:2px 8px;border-radius:4px' : ''}"><span class="mono${f === selSym ? ' med' : ''}">${f}</span><span class="meta muted">${l}</span></div>`).join('')}</div>`;
const IMPORTS = `<div class="sec"><span class="lbl">Imports</span><div class="kv"><span class="mono">decimal</span><span class="meta muted">Standard library</span></div></div>`;
const DEPS = st => `<div class="sec"><span class="lbl">Dependants, highlighted on the graph</span>
  ${['orders.py', 'refunds.py'].map(d => `<div class="kv"><span class="mono">${d}</span>${badge(st)}</div>`).join('')}</div>`;
const inspHead = (st, note, expanded) => `<div class="sec" style="gap:4px"><div class="kv" style="align-items:center"><span class="m16 med">pricing.py</span>
  <span class="row">${expanded ? '' : `<span class="iconbtn" aria-label="Expand inspector">${I('corners-out', 'ic20')}</span>`}<span class="iconbtn" aria-label="Close inspector">${I('x', 'ic20')}</span></span></div>
  <span class="mono muted">legacy_orders/pricing.py</span><div class="row g8" style="margin-top:4px">${badge(st)}<span class="meta muted">${note}</span></div></div>`;
const inspector = ({ st = 'not_planned', note = 'No run yet' } = {}) => `<aside class="side" style="width:360px">${inspHead(st, note)}${RISK}
  <div class="sec"><div class="row g32">${kv('Visible cases', '8')}${kv('Analysis warnings', 'None', 'muted')}</div></div>
  ${FUNCS()}${IMPORTS}${DEPS(st === 'not_planned' ? 'not_planned' : 'queued')}</aside>`;

const SRC = [[88, '            }'], [89, '        )'], [90, '        subtotal += line_total'], [91, ''],
  [92, '    <span class="tok-c"># stage 4: tax goes on the sum of the *rounded* lines</span>'], [93, '    tax = subtotal * TAX_RATE'], [94, '    taxed = subtotal + tax'], [95, ''],
  [96, '    <span class="tok-c"># stage 5: round the taxed total to the penny</span>'], [97, '    total = taxed.quantize(PENNY, rounding=ROUND_HALF_UP)'], [98, ''],
  [99, '    <span class="tok-k">return</span> {'], [100, '        <span>"lines"</span>: rounded_lines,'], [101, '        <span>"subtotal"</span>: subtotal,'],
  [102, '        <span>"tax"</span>: tax.quantize(PENNY, rounding=ROUND_HALF_UP),']];
const code = (lines, hl = []) => lines.map(([n, t]) => `<div class="ln${hl.includes(n) ? ' hl' : ''}"><span class="no">${n}</span><span>${t}</span></div>`).join('');

// ---------- 01 New migration
const zipChoice = err => `<div class="choice${err ? ' on bad' : ''}"><span class="radio"></span><div class="col"><span class="med">Upload a ZIP</span>${err
  ? `<span class="fielderr">${I('x-circle')}orders_service.zip is 14.2 MB, over the 10 MB limit.</span><span class="muted">Remove build output and vendored packages, then upload it again.</span>`
  : '<span class="muted">Up to 10 MB and 500 files. Static analysis only, so it can’t be migrated.</span>'}</div></div>`;
function s01({ w, h, focus, mode }) {
  const err = mode === 'error';
  const body = `<main class="col g24" style="width:640px;margin:${h > 800 ? 64 : 32}px auto 0">
    <div class="col g8"><h1>New migration</h1><p class="muted">Import a Python project. Axolotl maps its modules and imports, then migrates and verifies one unit at a time.</p></div>
    <div class="notice">${I('info', 'ic20 muted')}<span>Uploads are analysed statically and never run. Only trusted demo fixtures can be migrated.</span></div>
    <fieldset class="col g8" style="border:0"><legend class="lbl" style="margin-bottom:8px">Source</legend>
      <div class="choice${err ? '' : ' on'}"><span class="radio"></span><div class="col"><span class="med">Demo fixture: <span class="mono">legacy_orders</span></span><span class="muted">Order service with pricing, refunds and storage. Trusted, so it can run in the sandbox.</span></div></div>
      ${zipChoice(err)}
    </fieldset>
    <label class="col g8"><span class="lbl">Project name</span><span class="field" style="width:320px"><span class="mono fill">${err ? 'orders_service' : 'legacy_orders'}</span></span></label>
    <div class="row g12">${btn('Import repository', 'primary', focus ? 'focus' : '')}</div></main>`;
  return frame({ w, h, repo: false, body });
}

// ---------- 02 Repository overview
const MODS = [['main.py', 3, 0, 2, 0, 0], ['orders.py', 2, 0, 3, 1, 3], ['refunds.py', 1, 0, 2, 1, 3], ['pricing.py', 3, 0, 0, 2, 8],
  ['customers.py', 3, 0, 0, 1, 2], ['storage.py', 8, 0, 0, 2, 0]];
function s02({ w, h }) {
  const side = w > 1300 ? 400 : 360;
  const body = `<main class="col g24 fill" style="padding:24px">
    <div class="row g24" style="align-items:flex-end"><div class="col g8 fill"><h1 class="mono" style="font-size:24px;font-weight:500">legacy_orders</h1>
      <div class="row g32">${kv('Origin', 'Demo fixture, trusted')}${kv('Snapshot', 'snap_9c41e7d2a8b0', 'mono')}${kv('Analysis', `<span class="row g4" style="color:var(--passed)">${I('check-circle')}Complete</span>`)}${kv('Imported', '13:58:40')}</div></div>
      <div class="row g12">${btn('Open graph')}${btn('Choose target', 'primary')}</div></div>
    <div class="row g24" style="align-items:flex-start;min-height:0">
      <section class="panel fill"><div class="row" style="padding:12px 16px;border-bottom:1px solid var(--border)"><h2>Modules</h2><span class="sp"></span><span class="meta muted">6 local, standard library only</span></div>
        <table><thead><tr><th>Module</th><th class="num">Functions</th><th class="num">Classes</th><th class="num">Local imports</th><th class="num">Imported by</th><th class="num">Visible cases</th></tr></thead><tbody>
        ${MODS.map(m => `<tr><td class="mono">${m[0]}</td>${m.slice(1).map((v, i) => `<td class="num${i === 4 && !v ? ' muted' : ''}">${i === 4 && !v ? 'None' : v}</td>`).join('')}</tr>`).join('')}
        </tbody></table></section>
      <div class="col g16" style="width:${side}px;flex:none">
        <section class="panel"><div class="sec"><h3>Found in this snapshot</h3>${[['Files', 9], ['Modules', 6], ['Functions', 20], ['Test files', 1], ['Visible behaviour cases', 16]].map(([k, v]) => `<div class="kv"><span class="muted">${k}</span><span>${v}</span></div>`).join('')}</div></section>
        <section class="panel"><div class="sec"><h3>Warnings</h3><div class="row g8" style="align-items:flex-start">${I('warning', 'muted')}<span class="meta"><span class="mono">customers.py</span> has a docstring with instruction-like text. Treated as data; Argon won’t follow it.</span></div></div></section>
        <div class="notice">${I('hourglass', 'ic20')}<span class="meta" style="color:var(--ink)">Search indexes are building. Keyword is ready; vector search is available when it finishes.</span></div>
      </div></div></main>`;
  return frame({ w, h, tab: 'Overview', sys: [['ok', 'MongoDB'], ['building', 'Search indexes'], ['ok', 'Runner'], ['ok', 'Gemini']], body });
}

// ---------- 03 Architecture graph / 04 Module inspector
const ch = h => h - 96;
function s03({ w, h }) {
  const body = graph(w - 360, ch(h), { selected: 'pricing.py' }) + inspector();
  return frame({ w, h, tab: 'Graph', right: field('Filter modules', { ph: true }), body });
}
function s04({ w, h }) {
  const iw = w > 1300 ? 640 : 560, states = Object.fromEntries(Object.keys(POS).map(n => [n, 'queued']));
  const big = h > 800, lines = big ? SRC.slice(2) : SRC.slice(5, 10);
  const ins = `<aside class="side" style="width:${iw}px">${inspHead('queued', 'Unit 3 of 6 in the approved plan', true)}
    <div class="sec"><div class="row g32">${kv('Risk', 'High', 'med')}${kv('Visible cases', '8')}${kv('Analysis warnings', 'None', 'muted')}</div>
      <span class="meta muted">Rounds money with Decimal, half up, twice. Imported by orders.py and refunds.py.</span></div>
    ${FUNCS('finalise_amount')}
    <div class="sec" style="flex:1;min-height:0"><div class="kv"><span class="lbl">Source, read-only</span><span class="meta muted">finalise_amount, lines 48–106</span></div>
      <div class="editor" style="border:1px solid var(--border);border-radius:4px;padding:4px 0;flex:1;line-height:20px">${code(lines, [96, 97])}</div></div>
    <div class="row" style="align-items:stretch;flex:none"><div class="fill" style="border-right:1px solid var(--border)">${IMPORTS}</div><div class="fill">${DEPS('queued')}</div></div></aside>`;
  return frame({ w, h, tab: 'Graph', progress: '0 of 6 units verified', right: field('Filter modules', { ph: true }),
    body: graph(w - iw, ch(h), { states, selected: 'pricing.py' }) + ins });
}

// ---------- 05 Target & plan
const UNITS = [['storage.py', 'None', 'Low', 0], ['customers.py', 'None', 'Low', 2], ['pricing.py', 'None', 'High', 8],
  ['orders.py', 'customers.py, pricing.py, storage.py', 'Medium', 3], ['refunds.py', 'pricing.py, storage.py', 'Medium', 3], ['main.py', 'orders.py, refunds.py', 'Low', 0]];
function s05({ w, h, focus, approved }) {
  const lw = w > 1300 ? 400 : 360;
  const tgt = (on, off, t, d) => `<div class="choice${on ? ' on' : ''}${off ? ' off' : ''}"><span class="radio"></span><div class="col"><span class="med t">${t}</span><span class="meta muted">${d}</span></div></div>`;
  const body = `<main class="row g24 fill" style="padding:24px;align-items:flex-start;min-height:0">
    <section class="col g12" style="width:${lw}px;flex:none"><h2>Target</h2>
      ${tgt(1, 0, 'Modern Python 3', 'Typed and refactored, with the same public behaviour.')}
      ${tgt(0, 1, 'Python backend to FastAPI', 'Not available yet. Needs the app interface characterised first.')}
      ${tgt(0, 1, 'Python to TypeScript', 'Not available in this version. Behaviour checks only cover Python to Python.')}
      ${tgt(0, 1, 'Python 2 to Python 3', 'Not available in this version. Old runtimes aren’t supported in the sandbox.')}
      <span class="meta muted">Plan created by Argon at 13:59:12.</span></section>
    <section class="panel fill col" style="min-height:0;align-self:stretch;overflow:hidden">
      <div class="row g12" style="padding:12px 16px;border-bottom:1px solid var(--border)"><h2>Migration plan</h2>
        <span class="badge s-${approved ? 'passed' : 'neutral'}">${I(approved ? 'check-circle' : 'circle-dashed')}${approved ? 'Approved' : 'Draft'}</span><span class="sp"></span>
        ${approved ? btn('Start migration', 'primary', focus ? 'focus' : '') : btn('Approve plan', 'primary', focus ? 'focus' : '') + btn('Start migration', 'disabled')}</div>
      <p class="meta muted" style="padding:8px 16px 0">${approved ? 'Plan approved at 14:00:01.' : 'Approve the plan to enable Start migration.'} Dependencies migrate before the modules that import them.</p>
      <table><thead><tr><th class="num">Order</th><th>Unit</th><th>Depends on</th><th>Risk</th><th class="num">Visible cases</th></tr></thead><tbody>
        ${UNITS.map((u, i) => `<tr><td class="num">${i + 1}</td><td class="mono">${u[0]}</td><td class="${u[1] === 'None' ? 'muted' : 'mono'}">${u[1]}</td><td>${u[2]}</td><td class="num${u[3] ? '' : ' muted'}">${u[3] || 'None'}</td></tr>`).join('')}</tbody></table>
      <div class="row" style="align-items:stretch;border-top:1px solid var(--border);flex:1;min-height:0">
        <div class="sec fill" style="border-bottom:0;border-right:1px solid var(--border)"><span class="lbl">Rationale, written by Argon</span>
          <p style="max-width:60ch">storage.py, customers.py and pricing.py import no local modules, so they go first. orders.py and refunds.py depend on them and follow. main.py only wires the others together and goes last.</p></div>
        <div class="sec fill" style="border-bottom:0"><span class="lbl">Risks and coverage gaps</span>
          <ul style="padding-left:18px" class="col g4"><li>pricing.finalise_amount rounds each line, then the taxed total. Changing either step moves some totals by £0.01.</li><li>storage.py and main.py have no visible cases. Only the existing tests cover them.</li><li class="muted">No import cycles found.</li></ul></div></div>
    </section></main>`;
  return frame({ w, h, tab: 'Plan', body });
}

// ---------- 06 Run dashboard (+ states)
const runHead = ({ state = 'repairing', unit = 'pricing.py', attempt = '2 of 3', tests = '12 passed, 0 failed', last = '14:02:24, event 49', sk } = {}) => sk
  ? `<div class="row g32" style="height:56px;flex:none;padding:0 16px;background:var(--surface);border-bottom:1px solid var(--border)"><span class="sk" style="width:132px;height:32px;border-radius:6px"></span>${[96, 72, 140, 120].map(x => `<div class="col g4"><span class="sk" style="width:${x * .6}px;height:12px"></span><span class="sk" style="width:${x}px;height:16px"></span></div>`).join('')}</div>`
  : `<div class="row g32" style="height:56px;flex:none;padding:0 16px;background:var(--surface);border-bottom:1px solid var(--border)">${runstate(state)}
    ${kv('Current unit', unit, unit === 'None yet' ? 'muted' : 'mono med')}${kv('Attempt', attempt)}${kv('Tests', tests)}${kv('Last event', last)}<span class="sp"></span>${btn('Cancel run')}</div>`;
const ev = (t, n, x, { fail, open, icon = 'caret-right', body = '' } = {}) =>
  `<div class="ev${fail ? ' fail' : ''}${open ? ' open' : ''}">${open ? `<div class="row g8">` : ''}${I(fail ? 'x-circle' : icon, 'muted')}<span class="t">${t}</span><span class="n">${n}</span><span class="x">${x}</span>${open ? `</div>${body}` : ''}</div>`;
const GATES1 = `<div class="row g8" style="flex-wrap:wrap">
  <span class="gate s-passed">${I('check-circle', 'v')}Compile <span class="v">passed</span></span>
  <span class="gate s-failed">${I('x-circle', 'v')}Differential <span class="v">5 held-out differ</span></span>
  <span class="gate s-failed">${I('x-circle', 'v')}Impacted tests <span class="v">2 held-out differ</span></span>
  <span class="gate s-passed">${I('check-circle', 'v')}Existing tests <span class="v">12 passed</span></span>
  <span class="gate s-passed">${I('check-circle', 'v')}Sandbox policy <span class="v">passed</span></span></div>`;
function runSide(w, mode, big, tight) {
  if (mode === 'sk') return `<aside class="side" style="width:${w}px"><div class="sec"><span class="sk" style="width:140px;height:14px"></span><div class="row g8">${[120, 150, 170].map(x => `<span class="sk" style="width:${x}px;height:28px"></span>`).join('')}</div></div>
    <div class="sec" style="border-bottom:0"><span class="sk" style="width:80px;height:14px"></span></div>${Array.from({ length: 9 }, (_, i) => `<div class="ev"><span class="sk" style="width:16px;height:16px"></span><span class="sk" style="width:64px;height:14px"></span><span class="sk" style="width:${[120, 150, 104, 136][i % 4]}px;height:14px"></span></div>`).join('')}</aside>`;
  if (mode === 'early') return `<aside class="side" style="width:${w}px"><div class="sec"><span class="lbl">Gates</span><span class="muted">No gate results yet. Gates report as each unit is verified.</span></div>
    <div class="sec" style="border-bottom:1px solid var(--border)"><div class="kv"><span class="lbl">Events</span><span class="meta muted">Newest at the bottom</span></div></div>
    ${ev('14:00:02', 'run_created', 'plan_2e81, modern_python3', { icon: 'circle' })}${ev('14:00:03', 'run_state_changed', 'queued to baselining', { icon: 'circle' })}
    ${ev('14:00:05', 'baseline_started', 'Recording old outputs for 16 visible and 10 held-out cases', { icon: 'circle-half' })}
    <div class="sec" style="border-bottom:0"><span class="meta muted">Checking for new events every 1.5 s.</span></div></aside>`;
  const mig = mode === 'migrating';
  return `<aside class="side" style="width:${w}px">
    <div class="sec">${mig ? `<span class="lbl">Gates, customers.py attempt 1</span><div class="row g8" style="flex-wrap:wrap"><span class="gate s-passed">${I('check-circle', 'v')}Compile <span class="v">passed</span></span><span class="gate s-passed">${I('check-circle', 'v')}Differential <span class="v">all match</span></span><span class="gate s-passed">${I('check-circle', 'v')}Impacted tests <span class="v">all match</span></span><span class="gate s-passed">${I('check-circle', 'v')}Existing tests <span class="v">12 passed</span></span></div>`
      : `<span class="lbl">Gates, pricing.py attempt 1</span>${GATES1}`}</div>
    <div class="sec" style="padding-bottom:8px;border-bottom:1px solid var(--border)"><div class="kv"><span class="lbl">Events${mig ? '' : ', failures first'}</span><span class="meta muted">Newest at the bottom</span></div></div>
    ${mig ? '' : ev('14:02:09', 'verification_failed', 'unit_pricing, attempt 1', { fail: 1, open: 1, body: `<span class="meta">8 visible match. 7 held-out differ, 2 in orders and refunds.</span><div class="codebox">hcase_001  old £2.65  new £2.64\n6 more held-out, values redacted</div>` })}
    ${ev('', `Show ${mig ? (big ? 23 : 24) : (big ? 44 : 46)} earlier events`, '', { icon: 'caret-down' }).replace('class="n"', 'class="n" style="font-family:IBM Plex Sans"')}
    ${mig ? ev('14:01:20', 'snapshot_accepted', 'customers.py, rev_6d1a4b9e0c37', { icon: 'check-circle' }) + ev('14:01:22', 'unit_state_changed', 'pricing.py queued to migrating', { icon: 'circle' }) +
      ev('14:01:31', 'get_module_source', 'pricing.py, 106 lines') + (big ? ev('14:01:39', 'get_behaviour_cases', 'unit_pricing, 8 visible') : '') +
      ev('14:01:48', 'propose_patch', 'pricing.py, attempt 1', { open: 1, icon: 'caret-down', body: `<span class="lbl">Arguments</span><div class="codebox">{"files": ["pricing.py"],\n "summary": "Add type hints; use round()\n  for the penny rounding"}</div><span class="lbl">Result</span><div class="codebox">accepted, rev_51c8d07e9a22</div>` }) +
      ev('14:01:50', 'run_verification', 'unit_pricing, attempt 1', { icon: 'hourglass' })
      : (big ? ev('14:02:09', 'counterexample_recorded', 'hcase_008, held-out, redacted') + ev('14:02:09', 'counterexample_recorded', 'hcase_009, held-out, redacted') : '') +
      ev('14:02:10', 'repair_started', 'attempt 2 of 3', { icon: 'arrow-clockwise' }) +
      (tight ? ev('14:02:11', 'agent_turn', 'Argon: round() rounds half to even; restoring quantize with ROUND_HALF_UP') : ev('14:02:11', 'agent_turn', '', { open: 1, icon: 'caret-down', body: `<span class="who">Argon</span><p class="meta" style="white-space:normal">round() rounds half to even, so £2.205 became £2.20. I’ll restore quantize with ROUND_HALF_UP at both stages.</p>` })) +
      ev('14:02:24', 'propose_patch', 'pricing.py, attempt 2')}
  </aside>`;
}
const S_REPAIR = { 'storage.py': 'passed', 'customers.py': 'passed', 'pricing.py': 'repairing', 'orders.py': 'queued', 'refunds.py': 'queued', 'main.py': 'queued' };
function s06({ w, h, mode = 'repair', banner }) {
  const sw = w > 1300 ? 480 : 440, gh = ch(h) - 56 - (banner ? 48 : 0);
  if (mode === 'empty') return frame({ w, h, tab: 'Run', body: `<div class="empty">${I('list-checks', 'ic24')}<h2>No migration running</h2><p class="muted">Approve a plan to start one. Unit states and tool calls appear here as the run records them.</p><div style="margin-top:8px">${btn('Go to plan', 'primary')}</div></div>` });
  const cfg = {
    repair: [S_REPAIR, 'pricing.py', { 'pricing.py': 2 }, {}, '2 of 6 units verified'],
    migrating: [{ ...S_REPAIR, 'pricing.py': 'migrating' }, null, {}, { state: 'migrating', attempt: '1 of 3', tests: '12 passed, 0 failed', last: '14:01:50, event 29' }, '2 of 6 units verified'],
    early: [Object.fromEntries(Object.keys(POS).map(n => [n, 'baselining'])), null, {}, { state: 'baselining', unit: 'None yet', attempt: '–', tests: 'Not run yet', last: '14:00:05, event 3' }, '0 of 6 units verified'],
    sk: [{}, null, {}, { sk: 1 }, null],
  }[mode];
  const [states, selected, att, head, progress] = cfg;
  const content = `<div class="col fill" style="min-width:0">${runHead(head)}<div class="row" style="flex:1;min-height:0;align-items:stretch">
    ${graph(w - sw, gh, { states, selected, att, sk: mode === 'sk' })}${runSide(sw, mode === 'sk' ? 'sk' : mode === 'early' ? 'early' : mode === 'migrating' ? 'migrating' : 'repair', h > 800, !!banner)}</div></div>`;
  return frame({ w, h, tab: 'Run', progress, banner, body: content, right: mode === 'sk' ? '' : '<span class="meta muted">Run ID <span class="mono" style="color:var(--ink)">run_7f3a2c</span></span>' });
}
const LOST = `<div class="banner" role="status">${I('wifi-slash', 'ic20')}<span class="med">Connection lost — last known status at 14:02:31</span><span class="muted meta">Retrying every 1.5 s. Everything below is from that time.</span><span class="sp"></span>${btn('Retry now')}</div>`;

// ---------- 07 Verification / diff
const K = s => `<span class="tok-k">${s}</span>`, STD = 'CATEGORY_DISCOUNTS[<span>"standard"</span>]';
const DIFF = [[25, null, 'del', `${K('def')} discount_rate(category):`], [null, 25, 'add', `${K('def')} discount_rate(category: str | ${K('None')}) -&gt; Decimal:`], ['sep', '5 unchanged lines'],
  [31, null, 'del', `    ${K('if')} category ${K('is None')}:`], [32, null, 'del', `        ${K('return')} ${STD}`], [33, null, 'del', `    ${K('if')} category ${K('not in')} CATEGORY_DISCOUNTS:`],
  [34, null, 'del', `        ${K('return')} ${STD}`], [35, null, 'del', `    ${K('return')} CATEGORY_DISCOUNTS[category]`], [null, 31, 'add', `    ${K('return')} CATEGORY_DISCOUNTS.get(category, ${STD})`], ['sep', '2 unchanged lines'],
  [38, null, 'del', `${K('def')} line_gross(unit_price, quantity):`], [null, 34, 'add', `${K('def')} line_gross(unit_price: Decimal | str, quantity: int) -&gt; Decimal:`], ['sep', '5 unchanged lines'],
  [44, null, 'del', `        ${K('raise')} ValueError(<span>"quantity must not be negative: %s"</span> % quantity)`], [null, 40, 'add', `        ${K('raise')} ValueError(f<span>"quantity must not be negative: {quantity}"</span>)`],
  [45, 41, '', `    ${K('return')} Decimal(str(unit_price)) * Decimal(qty)`], ['sep', '2 unchanged lines'],
  [48, null, 'del', `${K('def')} finalise_amount(lines, category):`], [null, 44, 'add', `${K('def')} finalise_amount(lines: list[dict], category: str | ${K('None')}) -&gt; dict:`], ['sep', '30 unchanged lines'],
  [79, 75, '', '        line_total = discounted.quantize(PENNY, rounding=ROUND_HALF_UP)']];
const diffRows = big => DIFF.map(r => r[0] === 'sep'
  ? `<div class="ln" style="background:var(--ground);color:var(--muted);font-family:'IBM Plex Sans';padding:${big ? 8 : 4}px 0 ${big ? 8 : 4}px 104px">${I('caret-down')} ${r[1]}</div>`
  : `<div class="ln ${r[2]}"><span class="no">${r[0] ?? ''}</span><span class="no">${r[1] ?? ''}</span><span class="mk">${r[2] === 'add' ? '+' : r[2] === 'del' ? '−' : ''}</span><span>${r[3]}</span></div>`).join('');
function s07({ w, h }) {
  const sw = w > 1300 ? 520 : 440, big = h > 800;
  const gates = [['Compile', 'passed', ''], ['Differential', 'passed', 'All match'], ['Impacted tests', 'passed', '9 of 9'], ['Existing tests', 'passed', '12 of 12'], ['Sandbox policy', 'passed', 'No violations']];
  const cx = (id, vis, inp, o, n) => `<div class="col g4" style="padding:8px 0;border-top:1px solid var(--border)"><div class="row g8"><span class="${id.startsWith('hcase') ? 'mono ' : ''}med">${id}</span><span class="meta muted">${vis}</span><span class="sp"></span><span class="row g4 meta" style="color:var(--passed)">${I('check-circle')}Resolved</span></div>
    ${inp ? `<span>${inp}</span><span class="meta">Old <span class="mono">${o}</span>, attempt 1 <span class="mono">${n}</span>, now <span class="mono">${o}</span></span>` : '<span class="meta muted">hcase_002, 004, 005, 007, 008 and 009. Argon never saw them, so they still count as held-out checks.</span>'}</div>`;
  const body = `<div class="col fill" style="min-width:0">
    <div class="row g24" style="height:56px;flex:none;padding:0 16px;background:var(--surface);border-bottom:1px solid var(--border)">
      ${btn('Back to run')}<span class="div" style="width:1px;height:24px;background:var(--border)"></span>
      <span class="m16 med">pricing.py</span>${badge('passed')}${kv('Attempt', '2 of 2, accepted')}${kv('Revision', 'rev_baseline to rev_3a9f0c21b7e4', 'mono')}</div>
    <div class="row" style="flex:1;min-height:0;align-items:stretch">
      <section class="col fill" style="min-width:0;background:var(--surface)"><div class="row g12" style="height:40px;padding:0 16px;border-bottom:1px solid var(--border)">${I('git-diff')}<span class="mono med">pricing.py</span><span class="meta muted">5 lines added, 9 removed</span><span class="sp"></span><span class="meta muted">Inline diff, read-only</span></div>
        <div class="editor" style="flex:1;padding:4px 0">${diffRows(big)}</div></section>
      <aside class="side" style="width:${sw}px">
        <div class="sec"><span class="lbl">Gates on rev_3a9f0c21b7e4</span><table style="margin:-4px 0">${gates.map(([g, s, c]) => `<tr><td style="padding:5px 0;border:0">${g}</td><td style="padding:5px 0;border:0"><span class="row g4" style="color:var(--passed)">${I('check-circle')}${s}</span></td><td class="num muted" style="padding:5px 0;border:0">${c}</td></tr>`).join('')}</table></div>
        <div class="sec" style="gap:0"><span class="lbl" style="margin-bottom:4px">Counterexamples from attempt 1</span>
          ${cx('hcase_001', `<span class="row g4" style="color:var(--repairing)">${I('eye')}Held-out, exposed during repair</span>`, 'member, 1 × <span class="mono">SKU-A</span> at <span class="mono">£2.45</span>', '£2.65', '£2.64')}
          ${cx('6 more', 'Held-out, redacted')}</div>
        <div class="sec"><span class="lbl">Attempt history</span>
          <div class="kv"><span>Attempt 1 <span class="mono muted">rev_51c8d07e9a22</span></span><span class="row g4 meta" style="color:var(--failed)">${I('x-circle')}Failed: 7 held-out differ</span></div>
          <div class="kv"><span>Attempt 2 <span class="mono muted">rev_3a9f0c21b7e4</span></span><span class="row g4 meta" style="color:var(--passed)">${I('check-circle')}Passed, accepted</span></div></div>
      </aside></div></div>`;
  return frame({ w, h, tab: 'Run', progress: '3 of 6 units verified', body });
}

// ---------- 08 Final report (+ states)
// Warning message: title says what happened; body says why, the risk and what to do (Atlassian's warning-message guidance).
const VERDICT = `<section class="verdict s-warning">${I('warning', 'ic24')}<div class="col g12 fill">
  <div class="col g4"><h2 class="title">Completed with warnings</h2><p>Every recorded case matches, but recorded cases can’t prove the code behaves the same everywhere. Check these three caveats before you apply the patch.</p></div>
  <ul class="col g4"><li>Only 26 cases were compared: 16 visible and 10 held-out.</li>
  <li><span class="mono">hcase_001</span> was shown to Argon during repair, so it no longer counts as a held-out check.</li><li>storage.py and main.py have no visible cases. Only the existing tests cover them.</li></ul><hr>
  <div class="row g32">${kv('Units', '6 of 6 verified', 'med')}${kv('Tests', '12 passed, 0 failed', 'med')}${kv('Counterexamples', '7 found, 7 resolved', 'med')}${kv('Final revision', 'rev_7d2e91c04a6f', 'mono med')}</div></div></section>`;
const OUT = [['storage.py', 1, 'rev_2b77e0f4c913', 'None'], ['customers.py', 1, 'rev_6d1a4b9e0c37', 'None'], ['pricing.py', 2, 'rev_3a9f0c21b7e4', '7 found, 7 resolved'],
  ['orders.py', 1, 'rev_5e0a6c18d2f7', 'None'], ['refunds.py', 1, 'rev_8c3f19b6a0e5', 'None'], ['main.py', 1, 'rev_7d2e91c04a6f', 'None']];
const UNITS_T = `<section class="panel"><div class="row" style="padding:8px 16px;border-bottom:1px solid var(--border)"><h2>Units</h2><span class="sp"></span><span class="meta muted">6 changed files</span></div>
  <table class="tight"><thead><tr><th>Unit</th><th>Status</th><th class="num">Attempts</th><th>Accepted revision</th><th>Counterexamples</th></tr></thead><tbody>
  ${OUT.map(u => `<tr><td class="mono">${u[0]}</td><td>${badge('passed')}</td><td class="num">${u[1]}</td><td class="mono">${u[2]}</td><td class="${u[3] === 'None' ? 'muted' : ''}">${u[3]}</td></tr>`).join('')}</tbody></table></section>`;
const ART = [['legacy_orders.patch', 'Patch', '9f2c41d0'], ['report.json', 'Report', '4be07a93'], ['legacy_orders_migrated.zip', 'Archive', 'c81d5e26']];
const downloads = (n, note = '<span class="meta muted">SHA-256 checksums for each file are in report.json.</span>') => `<section class="panel"><div class="sec"><h3>Downloads</h3>
  <div class="row g8">${ART.slice(0, n).map(([f, k, s]) => btn(`${I('download-simple')}${k}`).replace('class="btn', `title="${f}, sha256 ${s}…" class="btn`)).join('')}</div>${note}</div></section>`;
// [unit, before µs, after µs, within noise]. Illustrative: RunReport has no timing field yet.
const PERF = [['customers.py', 1.9, 1.8, 1], ['pricing.py', 18.6, 15.2], ['orders.py', 41.3, 37.0], ['refunds.py', 52.7, 49.9, 1]];
const perfRow = ([u, b, a, noise]) => { const m = Math.max(a, b), d = Math.round((1 - a / b) * 100);
  return `<div class="col g4"><div class="row g8"><span class="mono">${u}</span><span class="sp"></span><span class="meta muted">${b.toFixed(1)} → ${a.toFixed(1)} µs</span>
    <span class="meta${noise ? ' muted' : ' med'}" style="width:92px;text-align:right">${noise ? 'Within noise' : `${Math.abs(d)}% ${d >= 0 ? 'faster' : 'slower'}`}</span></div>
    <div class="perf" role="img" aria-label="${u}: ${b.toFixed(1)} µs before, ${a.toFixed(1)} µs after"><i class="b" style="width:${b / m * 100}%"></i><i class="a" style="width:${a / m * 100}%"></i></div></div>`; };
const perf = () => `<section class="panel"><div class="sec" style="gap:12px"><div class="col g4"><div class="row g12"><h3>Runtime</h3><span class="sp"></span>
    <span class="row g8 meta"><span class="swatch b"></span>Before<span class="swatch a" style="margin-left:4px"></span>After</span></div>
    <span class="meta muted">Median per recorded case, before and after, in the same sandbox. Bars are scaled per unit.</span></div>
  ${PERF.map(perfRow).join('')}<span class="meta muted">Not timed: storage.py and main.py have no cases.</span></div></section>`;
const NARR = `<section class="panel"><div class="sec"><h3>Argon’s summary</h3><span class="meta muted">Written by Argon from the recorded events. Check it against the evidence.</span>
  <p class="meta">pricing.py needed a second attempt. Its first patch used round(), which rounds half to even, so seven held-out cases came out £0.01 off. The accepted patch keeps quantize with ROUND_HALF_UP. Every recorded case now matches.</p></div></section>`;
const NARR_ROW = `<section class="panel"><div class="row g8" style="padding:12px 16px">${I('caret-right', 'muted')}<h3>Argon’s summary</h3><span class="sp"></span><span class="meta muted">Written by Argon</span></div></section>`;
const NARR_MISSING = `<section class="panel"><div class="sec"><div class="row g8" style="align-items:flex-start">${I('info', 'muted')}<p class="meta"><span class="med">Argon’s summary</span> isn’t available: Gemini hit its rate limit (429). Everything else here comes from recorded results.</p></div></div></section>`;
function s08({ w, h, mode = 'ideal' }) {
  const sw = w > 1300 ? 400 : 360, pad = 'padding:24px';
  const wrap = (main, side) => `<main class="row g24 fill" style="${pad};align-items:flex-start;min-height:0;overflow:hidden"><div class="col g16 fill" style="max-width:880px">${main}</div><div class="col g16" style="width:${sw}px;flex:none">${side}</div></main>`;
  if (mode === 'empty') return frame({ w, h, tab: 'Report', progress: '2 of 6 units verified', body: `<div class="empty">${I('list-checks', 'ic24')}<h2>Report not ready yet</h2><p class="muted">Axolotl writes the report after final verification. The run is on unit 3 of 6.</p><div style="margin-top:8px">${btn('Go to run', 'primary')}</div></div>` });
  if (mode === 'error') return frame({ w, h, tab: 'Report', progress: '6 of 6 units verified', body: `<div class="empty">${I('x-circle', 'ic24')}<h2>Couldn’t load the report</h2><p class="muted">The server returned an error (500) at 14:09:12. The run’s results are still recorded, so nothing is lost.</p><div class="row g12" style="margin-top:8px">${btn('Try again', 'primary')}${btn('Go to run')}</div></div>`.replace('ic24', 'ic24" style="color:var(--failed)') });
  if (mode === 'sk') return frame({ w, h, tab: 'Report', body: wrap(
    `<div class="panel" style="height:300px;padding:16px 20px;display:flex;flex-direction:column;gap:16px"><span class="sk" style="width:380px;height:40px"></span><span class="sk" style="width:440px;height:16px"></span><div class="row g32">${[140, 140, 160].map(x => `<span class="sk" style="width:${x}px;height:36px"></span>`).join('')}</div><span class="sk" style="width:100%;height:1px"></span>${[560, 520, 480].map(x => `<span class="sk" style="width:${x}px;height:14px"></span>`).join('')}</div>
     <div class="panel">${Array.from({ length: 6 }, () => `<div class="row g24" style="height:44px;padding:0 16px;border-bottom:1px solid var(--border)"><span class="sk" style="width:96px;height:14px"></span><span class="sk" style="width:80px;height:20px"></span><span class="sk" style="width:140px;height:14px"></span></div>`).join('')}</div>`,
    `<div class="panel col g12" style="height:300px;padding:16px"><span class="sk" style="width:180px;height:16px"></span>${[1, .8, .9, .95].map(f => `<div class="col g4" style="margin-top:12px"><span class="sk" style="width:100%;height:8px"></span><span class="sk" style="width:${f * 100}%;height:8px"></span></div>`).join('')}</div>
     <div class="panel" style="height:180px;padding:16px"><span class="sk" style="display:block;width:120px;height:16px"></span></div>`) });
  const big = h > 800, noArchive = `<span class="meta muted">No archive was returned for this run. The patch and report are complete.</span>`;
  return frame({ w, h, tab: 'Report', progress: '6 of 6 units verified', body: wrap(VERDICT + UNITS_T,
    perf() + (mode === 'partial' ? downloads(2, noArchive) + NARR_MISSING : downloads(3) + (big ? NARR : NARR_ROW))) });
}

// ---------- 09 Search
const HITS = [['pricing.py', '48–106', 'pricing.finalise_amount', 1, 1, '# stage 5: round the taxed total to the penny\ntotal = taxed.quantize(PENNY, rounding=ROUND_HALF_UP)'],
  ['orders.py', '16–58', 'orders.place_order', null, 2, 'priced = pricing.finalise_amount(items, category)'],
  ['pricing.py', '25–35', 'pricing.discount_rate', null, 3, 'def discount_rate(category):\n    """Return the per-line discount rate …'],
  ['refunds.py', '18–98', 'refunds.partial_refund', null, 4, 'priced = pricing.finalise_amount(to_price, order["category"])']];
function s09({ w, h }) {
  const lw = w > 1300 ? 600 : 520, n = h > 800 ? 4 : 3;
  const hit = ([p, l, sym, kr, vr, snip], i) => `<div class="col g8" style="padding:12px 16px;border-bottom:1px solid var(--border);${i === 0 ? 'outline:2px solid var(--ink);outline-offset:-2px;border-radius:6px' : ''}">
    <div class="row g8"><span class="mono med">${p}</span><span class="meta muted">lines ${l}</span><span class="sp"></span><span class="meta muted">Hybrid, keyword ${kr ? '#' + kr : 'no match'}, vector #${vr}</span></div>
    <span class="mono muted">${sym}</span><div class="codebox">${snip.replace(/\bround\b/, '<span class="hl-mark">round</span>')}</div></div>`;
  const body = `<section class="col" style="width:${lw}px;flex:none;background:var(--surface);border-right:1px solid var(--border);min-height:0">
      <div class="col g12" style="padding:16px;border-bottom:1px solid var(--border)"><div class="row g8">${field('where is the bill rounded?', { w: lw - 32 - 236 - 8, key: false, x: 'focus' })}<span class="seg"><span>Keyword</span><span>Vector</span><span class="on">Hybrid</span></span></div>
        <div class="row g8"><span class="meta">4 results</span><span class="sp"></span><span class="badge s-neutral">${I('info')}Native Atlas hybrid</span></div></div>
      <div class="col" style="overflow:hidden">${HITS.slice(0, n).map(hit).join('')}</div></section>
    ${graph(w - lw, ch(h), { selected: 'pricing.py' })}`;
  return frame({ w, h, tab: 'Search', body });
}

const SCREENS = { s01: ['01 New migration', s01], s02: ['02 Repository overview', s02], s03: ['03 Architecture graph', s03], s04: ['04 Module inspector', s04],
  s05: ['05 Target and plan', s05], s06: ['06 Run dashboard', s06], s07: ['07 Verification and diff', s07], s08: ['08 Final report', s08], s09: ['09 Search', s09] };
const STATES = {
  'import-error': ['01 New migration / error', 'The API answers 422 VALIDATION_ERROR when an archive is over 10 MB. The error sits on the choice it’s about and says what to do; Import stays enabled.', () => s01({ w: 1280, h: 720, mode: 'error' })],
  'run-empty': ['06 Run dashboard / empty', 'No run yet. The one next step is the plan.', () => s06({ w: 1280, h: 720, mode: 'empty' })],
  'run-loading': ['06 Run dashboard / loading', 'Skeleton matches the final layout. Appears after 200 ms, stays at least 400 ms. No shimmer.', () => s06({ w: 1280, h: 720, mode: 'sk' })],
  'run-error': ['06 Run dashboard / error', 'Polling failed. Last data stays on screen with its time; nothing is inferred.', () => s06({ w: 1280, h: 720, banner: LOST })],
  'run-partial': ['06 Run dashboard / partial', 'Sparse data: the run has only baselined. Each empty section says what fills it.', () => s06({ w: 1280, h: 720, mode: 'early' })],
  'report-empty': ['08 Final report / empty', 'GET /report is 404 until final verification. Points back to the run.', () => s08({ w: 1280, h: 720, mode: 'empty' })],
  'report-loading': ['08 Final report / loading', 'Verdict block, units table and side panels as placeholders.', () => s08({ w: 1280, h: 720, mode: 'sk' })],
  'report-error': ['08 Final report / error', 'Says what failed and that results are safe. Two ways forward.', () => s08({ w: 1280, h: 720, mode: 'error' })],
  'report-partial': ['08 Final report / partial', 'narrative is null and only two artefacts came back. Only what exists gets a download.', () => s08({ w: 1280, h: 720, mode: 'partial' })],
};
