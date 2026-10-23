/**
 * Read-only Python source in Monaco, loaded from the bundle, never a CDN (the demo may be offline).
 * Only the core editor and the Python grammar are imported; lazy-load this file.
 */
import Editor, { loader, type OnMount } from '@monaco-editor/react';
import * as monaco from 'monaco-editor/editor/editor.api';
import 'monaco-editor/languages/definitions/python/register';
import EditorWorker from 'monaco-editor/editor/editor.worker?worker';
import { useEffect, useRef, useSyncExternalStore } from 'react';

self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
loader.config({ monaco });
// Monaco measures glyphs once; re-measure when IBM Plex Mono has actually loaded.
void document.fonts.ready.then(() => monaco.editor.remeasureFonts());

const html = document.documentElement;
const subscribe = (onChange: () => void) => {
  const observer = new MutationObserver(onChange);
  observer.observe(html, { attributes: true, attributeFilter: ['class'] });
  return () => observer.disconnect();
};
const isDark = () => html.classList.contains('dark');

/** Monochrome, like the template: keywords bold, comments muted. Hue stays reserved for run state. */
function defineTheme() {
  const token = (name: string) => getComputedStyle(html).getPropertyValue(`--${name}`).trim();
  const [ink, muted, card, tint] = ['foreground', 'muted-foreground', 'card', 'muted'].map(token);
  monaco.editor.defineTheme('axolotl', {
    base: isDark() ? 'vs-dark' : 'vs',
    inherit: false,
    rules: [
      { token: '', foreground: ink.slice(1) },
      { token: 'keyword', fontStyle: 'bold' },
      { token: 'comment', foreground: muted.slice(1) },
    ],
    colors: {
      'editor.background': card,
      'editor.foreground': ink,
      'editorLineNumber.foreground': muted,
      'editorLineNumber.activeForeground': ink,
      'editor.selectionBackground': tint,
      'editor.inactiveSelectionBackground': tint,
      'editorCursor.foreground': ink,
    },
  });
}

/** `start`-`end`: the symbol to scroll to and mark, 1-based and inclusive. */
export default function SourceView({ source, path, start, end }: { source: string; path: string; start?: number; end?: number }) {
  const dark = useSyncExternalStore(subscribe, isDark);
  const editor = useRef<monaco.editor.IStandaloneCodeEditor>(null);
  const marks = useRef<monaco.editor.IEditorDecorationsCollection>(null);

  useEffect(() => {
    defineTheme();
    monaco.editor.setTheme('axolotl');
  }, [dark]);

  const reveal = () => {
    if (!editor.current || !start || !end) return marks.current?.clear();
    editor.current.revealLinesInCenter(start, end);
    marks.current?.set([{ range: new monaco.Range(start, 1, end, 1), options: { isWholeLine: true, className: 'source-symbol' } }]);
  };
  useEffect(reveal, [start, end]);

  const onMount: OnMount = (instance) => {
    editor.current = instance;
    marks.current = instance.createDecorationsCollection();
    reveal();
  };

  return (
    <Editor
      value={source}
      language="python"
      path={path}
      theme="axolotl"
      beforeMount={defineTheme}
      onMount={onMount}
      loading={<span className="p-3 text-sm text-muted-foreground">Loading the editor…</span>}
      options={{
        readOnly: true,
        domReadOnly: true,
        ariaLabel: `Source of ${path}, read-only`,
        fontFamily: '"IBM Plex Mono", monospace',
        fontSize: 14,
        lineHeight: 22,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        renderLineHighlight: 'none',
        folding: false,
        lineNumbersMinChars: 3,
        overviewRulerLanes: 0,
        contextmenu: false,
        automaticLayout: true,
        padding: { top: 4, bottom: 4 },
        scrollbar: { verticalScrollbarSize: 10, horizontalScrollbarSize: 10 },
      }}
    />
  );
}
