// Artifact viewer for the Axolotl boards: one column, frames zoomed to fit it, one view per #hash.
// Everything is rendered by kit.js and board.js. This artifact is the UI reference; the Figma file is out of date.
(() => {
  const $ = s => document.querySelector(s);
  const VIEWS = [['screens', 'Screens'], ['states', 'States'], ['storyboard', 'Storyboard'], ['principles', 'Principles'], ['foundations', 'Foundations'], ['components', 'Components']];
  let view = 'screens', wide = false;

  const clean = html => html.replace(/ tabindex="0"/g, '');
  const shot = (w, h, html) => `<div class="shot" data-w="${w}" style="aspect-ratio:${w}/${h}"><div class="zoomer" style="width:${w}px">${clean(html)}</div></div>`;
  // Any frame showing the Runtime panel says its figures are made up, right where they appear.
  const SAMPLE = 'Runtime figures are sample data until the backend fills RunReport.performance.';
  const noteFor = (note, html) => html.includes('<h3>Runtime</h3>') ? [note, SAMPLE].filter(Boolean).join(' ') : note;
  const fig = (title, note, body) => { note = noteFor(note, body); return `<figure class="fig"><figcaption><h2>${title}</h2>${note ? `<p class="muted">${note}</p>` : ''}</figcaption>${body}</figure>`; };
  const intro = (h, p) => `<header class="intro"><h1>${h}</h1><p class="muted">${p}</p></header>`;
  const comp = (t, d, body) => `<section class="comp"><div><h3>${t}</h3><p class="meta muted">${d}</p></div><div class="pv">${body}</div></section>`;

  const screens = () => {
    const [w, h] = wide ? [1440, 900] : [1280, 720];
    return intro(`Screens at ${w}×${h}`, w === 1280
      ? 'The safe projector size. The data follows demo/legacy_orders and its real held-out cases.'
      : 'The same screens on a 1440×900 laptop. Side panels widen, and the extra height goes to the graph, source and events.')
      + Object.values(SCREENS).map(([t, f]) => fig(t, '', shot(w, h, f({ w, h })))).join('');
  };

  const states = () => intro('States', 'The import form’s error, then empty, loading, error and partial versions of the run dashboard and report. Each state is something the API can actually return.')
    + Object.values(STATES).map(([t, n, f]) => fig(t, n, shot(1280, 720, f()))).join('');

  const storyboard = () => intro('Demo storyboard', 'One frame per beat of the 3-minute live demo. If the live run has no mismatch, say so: show the held-out checks passing, then the T-11 wrong-patch test as a separate, labelled demonstration. A backup recording is always labelled “Recorded earlier run at &lt;time&gt;”.')
    + STORY.map(([t, name, f, act, say, see]) => { const s = shot(1280, 720, f()), n = noteFor('', s);
      return `<figure class="fig"><figcaption><h2>${name}</h2><p class="muted">${t}${n ? `. ${n}` : ''}</p></figcaption>${s}
      <dl class="beat"><div><dt>Do</dt><dd>${act}</dd></div><div><dt>Say</dt><dd>${say}</dd></div><div><dt>Judges see</dt><dd>${see}</dd></div></dl></figure>`; }).join('');

  const principles = () => intro('Principles', 'How every Axolotl screen is judged. Each rule comes with a check you can run in under a minute.')
    + `<ol class="rules">${RULES.map(([t, d, c], i) => `<li><span class="med muted">${String(i + 1).padStart(2, '0')}</span><h2>${t}</h2><p>${d}</p><p class="meta"><span class="med">Check:</span> ${c}</p></li>`).join('')}</ol>
    <div class="pair"><section class="panel"><div class="sec"><h2>Never</h2></div>${BANNED.map(([t, d]) => `<div class="sec"><h3>${t}</h3><p class="muted">${d}</p></div>`).join('')}</section>
    <section class="panel"><div class="sec"><h2>One deliberate exception</h2></div>${EXCEPTIONS.map(([t, d]) => `<div class="sec"><h3>${t}</h3><p class="muted">${d}</p></div>`).join('')}</section></div>`;

  // ---------- foundations: token values read from kit.css itself, so this table can't drift from the mocks
  const TOKENS = [['ground', 'Page and canvas background, dimmed graph nodes'], ['surface', 'Panels, bars, inputs'], ['ink', 'Text, primary button, focus, selection, lit edges'],
    ['muted', 'Secondary text, normal edges'], ['border', 'Dividers and panel edges'], ['border-strong', 'Control outlines, dimmed nodes and edges'], ['grid', 'Canvas grid'], ['code', 'Code blocks'],
    ['working', 'Baselining, migrating, verifying'], ['repairing', 'Repairing'], ['warning', 'Completed with warnings, warning messages'], ['passed', 'Passed, completed'], ['failed', 'Failed, blocked'], ['neutral', 'Not planned, queued, skipped, cancelled']];
  const CHECK = { ink: ['surface', 4.5], muted: ['surface', 4.5], 'border-strong': ['surface', 3] };
  const lum = hex => { const n = parseInt(hex.slice(1), 16); return [n >> 16, n >> 8 & 255, n & 255].map(v => (v /= 255) <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4).reduce((s, v, i) => s + v * [0.2126, 0.7152, 0.0722][i], 0); };
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  const sheetTokens = () => {
    try {
      const rules = [...[...document.styleSheets].find(s => (s.href || '').endsWith('kit.css')).cssRules];
      return [rules.find(r => r.selectorText === ':root').style, rules.find(r => r.selectorText === '[data-theme="dark"]').style];
    } catch { return null; }
  };
  const swatch = hex => `<span class="sw" style="background:${hex}"></span>`;
  const tokenCell = (st, t) => {
    const v = n => st.getPropertyValue('--' + n).trim(), hex = v(t), tint = v(t + '-tint');
    const [against, min] = CHECK[t] || (tint ? [t + '-tint', 4.5] : []), r = against ? ratio(hex, v(against)) : 0;
    return `<td><div class="row g8">${swatch(hex)}${tint ? swatch(tint) : ''}<span class="mono">${hex}${tint ? ` / ${tint}` : ''}</span></div>`
      + (against ? `<span class="meta${r >= min ? ' muted' : ''}">${r.toFixed(1)}:1 on ${tint ? 'its tint' : against}, needs ${min}</span>` : '') + '</td>';
  };
  const TYPE = [['Heading 1', '24 / 30, 600, page and verdict titles', '<h1>Final report</h1>'], ['Heading 2', '20 / 25, 600', '<h2>Units</h2>'], ['Heading 3', '16 / 24, 500', '<h3>Runtime</h3>'],
    ['Body', '16 / 24, 400', '<p>Passing tests are evidence, not proof of equivalence.</p>'],
    ['Meta', '14 / 21, 400', '<p class="meta">Median per recorded case, before and after, in the same sandbox.</p>'],
    ['Label', '14 / 21, 500, muted', '<span class="lbl">Current unit</span>'],
    ['Mono 16', '16, 500, module names in headers', '<span class="m16 med">pricing.py</span>'],
    ['Mono 14', '14, code and values only', '<span class="mono">rev_3a9f0c21b7e4</span>']];
  // One stated choice per axis (anti-ai-slop's five axes), with the reason that makes it ours.
  const DECISIONS = [
    ['Colour', 'No brand hue. Ink and greys carry the interface. Hue appears only for run state, always beside an icon and a word.',
      'On the graph, any brand colour would read as a state.'],
    ['Type', 'IBM Plex Sans for all text, Plex Mono for code and values only. Weights 400, 500 and 600; sizes 14, 16, 20 and 24.',
      'One family keeps a busy screen calm on a projector. Plex tells 0 from O and 1 from l, which matters when someone reads a case ID aloud.'],
    ['Layout', 'Fixed panes around one dominant graph. Panels are split by borders, not cards. Side panels are 360&nbsp;px at 1280 and 400&nbsp;px at 1440.',
      'The run stays in view while events stream in, so nobody scrolls during the demo.'],
    ['Copy', 'One verb per action, from button to result. Numbers come from the fixture, and anything made up is labelled where it appears.',
      'Judges check claims against the screen. An unlabelled number costs more than a missing one.'],
    ['Motion', 'Two moments only: a unit’s state change with its dependant highlight, under 300&nbsp;ms, and a 120&nbsp;ms colour change on hover. Transform, opacity and colour; all of it off under reduced motion.',
      'Movement should mean the run changed. Anything else competes with it.']];
  const foundations = () => {
    const tk = sheetTokens();
    return intro('Foundations', 'The five decisions every screen follows, then the colour tokens with their contrast, type, spacing, radius and icons.')
      + `<section class="col"><h2 style="margin-bottom:8px">Five decisions</h2>${DECISIONS.map(([a, d, y]) => comp(a, '', `<div class="col g8" style="max-width:72ch"><p>${d}</p><p class="meta muted"><span class="med">Why:</span> ${y}</p></div>`)).join('')}</section>
      <section class="col g16"><h2>Colour</h2>${tk ? `<div class="tbl"><table class="tokens"><thead><tr><th>Token</th><th>Used for</th><th>Light</th><th>Dark</th></tr></thead><tbody>
        ${TOKENS.map(([t, use]) => `<tr><td class="mono">--${t}</td><td>${use}</td>${tokenCell(tk[0], t)}${tokenCell(tk[1], t)}</tr>`).join('')}</tbody></table></div>`
        : '<p class="muted">The token table needs kit.css to load. Reload the page to try again.</p>'}</section>
      <section class="col g16"><h2>Type</h2><div class="tbl"><table><tbody>${TYPE.map(([n, spec, s]) => `<tr><td style="width:200px"><span class="med">${n}</span><br><span class="meta muted">${spec}</span></td><td>${s}</td></tr>`).join('')}</tbody></table></div></section>
      <div class="pair"><section class="col g16"><h2>Spacing</h2><p class="meta muted">A 4&nbsp;px grid. Panels are divided by borders, not gaps.</p><div class="scale">${[4, 8, 12, 16, 24, 32].map(n => `<div class="col g4"><span class="space" style="width:${n}px;height:${n}px"></span><span class="meta muted">${n}</span></div>`).join('')}</div></section>
      <section class="col g16"><h2>Radius</h2><p class="meta muted">By hierarchy, nested radii concentric.</p><div class="scale">${[[4, 'Chips, inputs'], [6, 'Buttons, graph nodes'], [10, 'Panels']].map(([r, u]) => `<div class="col g8"><span class="rad" style="border-radius:${r}px"></span><span class="meta"><span class="med">${r}</span> <span class="muted">${u}</span></span></div>`).join('')}</div></section></div>
      <section class="col g16"><h2>Icons</h2><p class="meta muted">Phosphor, regular weight. 16&nbsp;px in text, 20&nbsp;px in bars, always next to a word.</p><div class="icons">${Object.keys(ICONS).map(n => `<div class="ico">${I(n, 'ic24')}<span class="meta muted">${n}</span></div>`).join('')}</div></section>`;
  };

  // ---------- components
  const at0 = html => html.replace(/left:\d+px;top:\d+px/, 'left:0;top:0');
  const NODES = [['orders.py', { state: 'queued' }, 'Queued'], ['customers.py', { state: 'migrating' }, 'Migrating'], ['pricing.py', { state: 'repairing', att: 2 }, 'Repairing, attempt 2'],
    ['storage.py', { state: 'passed' }, 'Passed'], ['refunds.py', { state: 'failed' }, 'Failed'], ['pricing.py', { state: 'passed', sel: 1 }, 'Selected'],
    ['main.py', { state: 'queued', dim: 1 }, 'Dimmed, queued'], ['customers.py', { state: 'passed', dim: 1 }, 'Dimmed, passed']];
  const components = () => intro('Components', 'The parts every screen is built from, rendered by the same code as the screens.')
    + `<div class="col">${[
      comp('Status badge', 'Unit state. Icon, word and colour together, never colour alone.', `<div class="wrap8">${Object.keys(ST).map(badge).join('')}</div>`),
      comp('Run state', 'One per run, in the run header. Completed with warnings has its own yellow and the warning triangle, so it never reads as repairing.', `<div class="wrap8">${['baselining', 'migrating', 'verifying', 'repairing', 'final_verification', 'completed', 'completed_with_warnings', 'failed', 'cancelled'].map(runstate).join('')}</div>`),
      comp('System chip', 'In the app bar. ok stays grey; only problems get colour.', `<div class="wrap8">${[['ok', 'MongoDB'], ['building', 'Search indexes'], ['unavailable', 'Runner']].map(chip).join('')}</div>`),
      comp('Buttons', 'One verb per action. Primary is ink. Hover changes colour only, over 120&nbsp;ms, and nothing moves. Focus is an ink ring, 2&nbsp;px, offset 2. A disabled button always has its reason next to it.',
        `<div class="wrap8" style="gap:16px 24px;align-items:flex-start">${[[btn('Approve plan', 'primary'), 'Primary'], [btn('Approve plan', 'primary', 'hover'), 'Primary, hover'], [btn('Cancel run'), 'Secondary'],
          [btn('Cancel run', 'secondary', 'hover'), 'Secondary, hover'], [btn('Start migration', 'disabled'), 'Disabled'], [btn('Approve plan', 'primary', 'focus'), 'Focus']]
          .map(([b, l]) => `<div class="col g8" style="align-items:flex-start">${b}<span class="meta muted">${l}</span></div>`).join('')}</div>`),
      comp('Search field and toggle', 'The / key focuses search from anywhere.', `<div class="wrap8">${field('Search modules, functions and cases', { ph: true, w: 320 })}<span class="seg"><span class="on">Keyword</span><span>Meaning</span></span></div>`),
      comp('Gate chips', 'One per gate, in the verifier’s order: compile, differential, impacted tests, existing tests, sandbox policy. Skipped gates are dashed.',
        `<div class="col g8">${GATES1}<div class="wrap8"><span class="gate skip">${I('arrow-bend-down-right', 'muted')}Impacted tests <span class="muted">skipped</span></span></div></div>`),
      comp('Graph nodes', 'Dimmed uses no opacity: ground fill, 3:1 outline, muted name, and the state line keeps its colour, icon and word.',
        `<div class="nodes">${NODES.map(([n, o, l]) => `<div class="col g8"><div class="nodebox">${clean(at0(node(n, o)))}</div><span class="meta muted">${l}</span></div>`).join('')}</div>`),
      comp('Graph with a selection', 'Selecting pricing.py lights the two modules that import it. Their edges turn ink and 3&nbsp;px; the rest dim.',
        shot(700, 420, `<div class="app" style="width:700px;height:420px"><div class="body">${graph(700, 420, { states: S_REPAIR, selected: 'pricing.py', att: { 'pricing.py': 2 } })}</div></div>`)),
      comp('Timeline events', 'One line per recorded event. Failures are tinted and pinned first; tool calls and Argon’s turns expand inline.',
        `<div class="tlbox">${ev('14:01:50', 'run_verification', 'unit_pricing, attempt 1', { icon: 'hourglass' })}${ev('14:02:09', 'verification_failed', 'unit_pricing, attempt 1', { fail: 1, open: 1, body: '<span class="meta">8 visible match. 7 held-out differ, 2 in orders and refunds.</span><div class="codebox">hcase_001  old £2.65  new £2.64\n6 more held-out, values redacted</div>' })}${ev('14:02:11', 'agent_turn', '', { open: 1, icon: 'caret-down', body: '<span class="who">Argon</span><p class="meta" style="white-space:normal">round() rounds half to even, so £2.205 became £2.20. I’ll restore quantize with ROUND_HALF_UP at both stages.</p>' })}</div>`),
      comp('Connection banner', 'Polling failed. The last data stays on screen with its time, and nothing is inferred.', `<div class="tlbox" style="max-width:none;min-width:760px">${LOST}</div>`),
      comp('Choice rows', 'Single choice with a full description. Unavailable choices stay visible and say why. An error sits on the choice it’s about, in words with an icon, and says what to do next.',
        `<div class="col g8" style="max-width:560px"><div class="choice on"><span class="radio"></span><div class="col"><span class="med">Demo fixture: <span class="mono">legacy_orders</span></span><span class="muted">Order service with pricing, refunds and storage. Trusted, so it can run in the sandbox.</span></div></div>${zipChoice(false)}
        <span class="meta muted" style="margin-top:8px">With an error</span>${zipChoice(true)}</div>`),
      comp('Verdict', 'A warning message: tinted, no border, the triangle on the left. The title says what happened in three words; the body gives the reason, the risk and what to do in two sentences. Caveats follow as a list, and the numbers close it. Not dismissible, because it’s the run’s outcome.', `<div style="min-width:760px;max-width:880px">${VERDICT}</div>`),
      comp('Runtime chart', 'Before is grey, after is ink, bars scaled per unit. Hidden while RunReport.performance is null. The figures here are sample data.', `<div class="narrow">${perf()}</div>`),
      comp('Diff', 'Added and removed lines borrow the passed and failed tints. The + and − markers carry the meaning, so it holds in greyscale.', `<div class="tlbox" style="max-width:none"><div class="editor" style="padding:4px 0;min-width:760px">${diffRows(false)}</div></div>`),
    ].join('')}</div>`;

  const RENDER = { screens, states, storyboard, principles, foundations, components };
  const fit = () => document.querySelectorAll('.shot').forEach(s => s.style.setProperty('--z', s.clientWidth / s.dataset.w));
  const render = () => {
    $('#view').innerHTML = RENDER[view]();
    document.querySelectorAll('#views a').forEach(a => a.setAttribute('aria-current', a.dataset.v === view ? 'page' : 'false'));
    $('#size').hidden = view !== 'screens';
    document.querySelectorAll('#size button').forEach(b => b.setAttribute('aria-pressed', String((b.dataset.size === '1440') === wide)));
    fit();
  };
  const fromHash = () => { const h = location.hash.slice(1); view = VIEWS.some(([k]) => k === h) ? h : 'screens'; render(); window.scrollTo(0, 0); };

  const isDark = () => { const t = document.documentElement.dataset.theme; return t ? t === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches; };
  const syncTheme = () => document.querySelectorAll('#theme button').forEach(b => b.setAttribute('aria-pressed', String((b.dataset.set === 'dark') === isDark())));

  $('#views').innerHTML = VIEWS.map(([k, t]) => `<a href="#${k}" data-v="${k}">${t}</a>`).join('');
  $('#size').addEventListener('click', e => { const b = e.target.closest('button'); if (b) { wide = b.dataset.size === '1440'; render(); } });
  $('#theme').addEventListener('click', e => { const b = e.target.closest('button'); if (b) { document.documentElement.dataset.theme = b.dataset.set; syncTheme(); } });
  new MutationObserver(syncTheme).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', syncTheme);
  addEventListener('hashchange', fromHash);
  addEventListener('resize', fit);
  if (document.fonts) document.fonts.ready.then(fit);
  syncTheme();
  fromHash();
})();
