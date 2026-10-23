// Board layouts for local review screenshots (shoot.mjs). ?board=screens|states|story|principles|frame &size= &theme= &id= &skip=
const q = new URLSearchParams(location.search);
const size = q.get('size') === '1440' ? [1440, 900] : [1280, 720];
const [W, H] = size;
if (q.get('theme')) document.documentElement.dataset.theme = q.get('theme');

const STORY = [
  ['0:00–0:25', 'Import a real repository', () => s01({ w: 1280, h: 720, focus: 1 }), 'Choose legacy_orders and press Import repository.',
    'Legacy services break when you touch them, because nobody knows what depends on what. Axolotl migrates them one verified unit at a time.', 'A real import, not a slide. Every system chip reports ok.'],
  ['0:25–0:55', 'The dependency graph', () => s03({ w: 1280, h: 720 }), 'Click pricing.py.',
    'This graph comes from parsing the code. Selecting pricing.py lights up the two modules that import it.', 'orders.py and refunds.py stay lit, their edges thicken, everything else dims.'],
  ['0:55–1:20', 'Plan, then approve', () => s05({ w: 1280, h: 720, focus: 1 }), 'Point at the disabled targets, read the order, press Approve plan, then Start migration.',
    'Argon plans dependencies first. Nothing runs until I approve it.', 'Disabled targets give their reason. Approve plan becomes Plan approved.'],
  ['1:20–2:05', 'Live tool calls and tests', () => s06({ w: 1280, h: 720, mode: 'migrating' }), 'Expand the propose_patch row.',
    'Every row is a recorded event: the tool Argon called and what came back.', 'storage.py and customers.py passed with their gates. pricing.py migrating, attempt 1.'],
  ['2:05–2:35', 'A penny out, then repaired', () => s06({ w: 1280, h: 720 }), 'Open the pinned failure. Wait for pricing.py to turn green.',
    'Every visible test passed, but seven held-out cases came out a penny off. Argon sees one of them; the other six stay hidden. It finds the rounding rule and patches it.', '£2.65 against £2.64, pricing.py amber, then green; orders.py is next.'],
  ['2:35–3:00', 'Outcome and limits', () => s08({ w: 1280, h: 720 }), 'Open Report. Point at the runtime chart, then open the pricing.py diff from the units table.',
    'It finished with warnings, and it says why. Passing tests are evidence, not proof. The same cases, timed before and after, show what the rewrite cost or saved.', 'Verdict with caveats in body text. Runtime before and after for each timed unit. Downloads.'],
];

const RULES = [
  ['Show the system’s real state', 'Every visual state traces to a persisted event or API response. A failed poll says “Connection lost — last known status at HH:MM:SS” and never infers a finish.', 'Point at any state and name the event behind it.'],
  ['One hero per screen', 'The graph is the centrepiece. Everything else is quiet, aligned and neutral.', 'Squint. Only one thing should stand out.'],
  ['Colour means state, never decoration, never alone', 'Hue is reserved for run state, and always comes with an icon and a word. Text 4.5:1, control and node outlines 3:1.', 'Desaturate the frame. Every state still reads.'],
  ['Design every state', 'Ideal, empty, loading, partial and error. Skeletons match the final layout, show after 200&nbsp;ms and stay 400&nbsp;ms. Empty screens give the next action.', 'Each screen has all five frames.'],
  ['Keyboard first, URL as state', 'Nodes are focusable, / focuses search, Esc closes the inspector, focus rings are always visible, targets are at least 24&nbsp;px. Run and selected node live in the URL.', 'Refresh mid-demo and land in the same place.'],
  ['Dense, not cramped', 'Panels divided by borders, not card grids. 4&nbsp;px grid, tabular figures for numbers that change, prose under 80 characters.', 'No nested cards, no orphan padding.'],
  ['One motion moment', 'The node state change and the dependant highlight: under 300&nbsp;ms, transform and opacity only, off under reduced motion. Nothing else moves unless a person did it.', 'Turn on reduced motion. Nothing is lost.'],
  ['Agent traces put failures first', 'Attempt count sits at the top. Failures are pinned above the list. Tool calls collapse to one line and expand inline. Argon’s words are labelled as Argon’s.', 'Find the last failure in one glance.'],
  ['Copy is interface', 'Active voice, one verb per action from button to result: Approve plan, then Plan approved. Errors say what happened and what to do, without apology. Caveats sit in body text.', 'Read every button aloud with its result.'],
  ['The demo has to survive the room','Fonts and Monaco load locally, never from a CDN. Test on a real projector in both themes before the dry run.', 'Unplug the Wi-Fi and reload.'],
];
const BANNED = [
  ['Colour and surface', 'Purple or indigo gradients, gradient text, glassmorphism, glows. Coloured left-border strips.'],
  ['Type', 'Inter or Geist by default. Tracked-out all-caps labels above headings. Monospace for anything that isn’t code or a value.'],
  ['Layout', 'Identical rounded cards with the same grey shadow. One radius on everything. Nested cards. Card grids for data.'],
  ['Icons and copy', 'Emoji as icons. Coloured rounded-square icon tiles. “→” on every button. Dot-separated meta strings as decoration. Hype verbs like supercharge, unlock and seamless. Acme, John Doe and made-up numbers without a label.'],
  ['Forms', 'An input with no error state. A disabled button that doesn’t say why.'],
  ['Motion and feedback', 'Fade-and-slide on every panel. Bounce easing. transition: all. Spinners with no timeout. Progress bars driven by timers. Toasts for everything. Tooltips where inline text would do.'],
];
const EXCEPTIONS = [
  ['Diff lines', 'Added and removed lines borrow the passed and failed tints. The + and − markers carry the meaning, so it holds in greyscale.'],
];

const cap = (title, note, html) => `<figure class="cap"><figcaption class="col g4"><span class="capt"><h2>${title}</h2></span>${note ? `<span class="muted" style="max-width:80ch">${note}</span>` : ''}</figcaption>${html}</figure>`;
const board = (title, intro, inner) => `<div class="board"><header><h1>${title}</h1><p class="muted" style="max-width:80ch">${intro}</p></header>${inner}</div>`;
const themeName = document.documentElement.dataset.theme === 'dark' ? ', dark' : '';

function render() {
  const b = q.get('board') || 'screens', id = q.get('id');
  if (b === 'frame') {
    if (SCREENS[id]) return SCREENS[id][1]({ w: W, h: H });
    if (STATES[id]) return STATES[id][2]();
    if (id?.startsWith('story-')) return STORY[+id.slice(6)][2]();
  }
  if (b === 'screens') {
    const skip = (q.get('skip') || '').split(',');
    const cells = Object.entries(SCREENS).filter(([k]) => !skip.includes(k)).map(([k, [t, f]]) => cap(`${t} / ${W}`, '', f({ w: W, h: H }))).join('');
    return board(`Screens at ${W}×${H}${themeName}`, W === 1280
      ? 'The safe projector size. Every value comes from the Foundations tokens; the fixture story matches demo/legacy_orders. Runtime figures on the report are illustrative.'
      : 'The same screens on a 1440×900 laptop. Side panels widen, and the extra height goes to the graph, source and events.',
      `<div class="grid" style="grid-template-columns:repeat(3,${W}px)">${cells}</div>`);
  }
  if (b === 'states') return board(`Run dashboard and report states${themeName}`,
    'Empty, loading, error and partial versions of the two screens the demo depends on. Each state is something the API can actually return.',
    `<div class="grid" style="grid-template-columns:repeat(4,1280px)">${Object.values(STATES).map(([t, n, f]) => cap(t, n, f())).join('')}</div>`);
  if (b === 'story') return board('Demo storyboard', 'One frame per beat of the 3-minute live demo. If the live run has no mismatch, say so: show the held-out checks passing, then the T-11 wrong-patch test as a separate, labelled demonstration. A backup recording is always labelled “Recorded earlier run at &lt;time&gt;”.',
    `<div class="grid" style="grid-template-columns:repeat(2,1280px)">${STORY.map(([t, name, f, act, say, see]) => `<figure class="cap">${f()}
      <figcaption class="row g24" style="align-items:flex-start"><div class="col" style="width:200px;flex:none"><span class="med">${t}</span><span class="semi">${name}</span></div>
      <div class="col g4 fill"><span class="lbl">Do</span><span>${act}</span></div><div class="col g4 fill"><span class="lbl">Say</span><span>${say}</span></div><div class="col g4 fill"><span class="lbl">Judges see</span><span>${see}</span></div></figcaption></figure>`).join('')}</div>`);
  if (b === 'principles') return board('Principles', 'How every Axolotl screen is judged. Each rule comes with a check you can run in under a minute.',
    `<div class="row g48" style="align-items:flex-start;gap:64px">
      <ol class="grid" style="grid-template-columns:repeat(2,440px);gap:32px 48px;list-style:none">${RULES.map(([t, d, c], i) => `<li class="col g8"><span class="med muted">${String(i + 1).padStart(2, '0')}</span><h2>${t}</h2><p>${d}</p><p class="meta"><span class="med">Check:</span> ${c}</p></li>`).join('')}</ol>
      <div class="col g32" style="width:480px"><section class="panel"><div class="sec"><h2>Never</h2></div>${BANNED.map(([t, d]) => `<div class="sec"><h3>${t}</h3><p class="muted">${d}</p></div>`).join('')}</section>
      <section class="panel"><div class="sec"><h2>One deliberate exception</h2></div>${EXCEPTIONS.map(([t, d]) => `<div class="sec"><h3>${t}</h3><p class="muted">${d}</p></div>`).join('')}</section></div></div>`);
  return 'unknown board';
}
const root = document.getElementById('root');
if (root) root.innerHTML = render();
