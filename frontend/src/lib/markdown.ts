// Markdown + LaTeX rendering for the 校对屏 (③ check screen) preview.
//
// marked handles the Markdown; MathJax (loaded from the CDN in index.html) does the
// maths. The catch: marked treats a backslash before punctuation as an escape, so it
// would silently eat the delimiters in `\( … \)` / `\[ … \]` before MathJax ever sees
// them. We therefore PROTECT every maths span with a placeholder, run marked on the
// prose, then restore the spans verbatim — so the LaTeX reaches MathJax intact.
import { marked } from 'marked';

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// Render Markdown with embedded LaTeX to typeset-ready HTML (used by render mode 1).
// Recognises $$…$$, \[…\], \(…\) and single-$ inline maths; the single-$ form is
// rewritten to \( … \) because that is the inline delimiter MathJax is configured for.
export function renderMarkdownMath(src: string): string {
  const spans: string[] = [];
  const stash = (raw: string): string => {
    spans.push(raw);
    return `@@MATH${spans.length - 1}@@`;
  };

  const protectedSrc = src
    .replace(/\$\$[\s\S]+?\$\$/g, (m) => stash(m)) // $$ display $$
    .replace(/\\\[[\s\S]+?\\\]/g, (m) => stash(m)) // \[ display \]
    .replace(/\\\([\s\S]+?\\\)/g, (m) => stash(m)) // \( inline \)
    .replace(/\$[^$\n]+?\$/g, (m) => stash('\\(' + m.slice(1, -1) + '\\)')); // $ inline $ → \( \)

  let html = marked.parse(protectedSrc, { async: false, breaks: true, gfm: true }) as string;
  html = html.replace(/@@MATH(\d+)@@/g, (_, i) => spans[Number(i)] ?? '');
  return html;
}

// Render mode 2 — "source style": show the raw Markdown/LaTeX source as-is, the way a
// code editor's preview pane would. Wrapped in <pre><code> so MathJax (which skips
// code/pre) leaves the delimiters visible instead of typesetting them.
export function renderSource(src: string): string {
  return `<pre class="check-source"><code>${escapeHtml(src)}</code></pre>`;
}
