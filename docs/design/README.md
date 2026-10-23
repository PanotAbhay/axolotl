# Axolotl UI template

This folder is the UI/UX reference for `frontend/`. The Figma file is out of date, so
don't build from it. Use the tokens in `kit.css` as they are.

Open `index.html` in a browser; it needs no build step. Six views: Screens, States,
Storyboard, Principles, Foundations and Components. Each one renders in light and dark,
at 1280 and 1440.

| File | What it holds |
|---|---|
| `kit.css` | Colour, type, spacing and radius tokens, plus component styles |
| `kit.js` | The nine screens (01 New migration to 09 Search) and their states |
| `board.js`, `viewer.js` | The storyboard, principles, foundations and component views |
| `icons.js` | The Phosphor icons used |

Runtime figures on 08 Final report are sample data. `RunReport.performance` fills them in
the real app.
