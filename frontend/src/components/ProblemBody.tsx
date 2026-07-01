import { useMathJax } from '../hooks/useMathJax';

// The backend writes a problem's maths straight into the Chinese `statement`
// (e.g. "求 (a+\frac{1}{a})^2 的最小值") but WITHOUT math delimiters, so MathJax
// never typesets it and the raw \frac shows through. This component renders the
// statement as ONE flowing block with the formulas typeset *in place* — the maths
// stays inside the sentence instead of being pulled out into a separate panel.

// CJK + fullwidth punctuation = prose; the ASCII stretches between them are the
// candidate maths runs we may wrap in \( … \).
const PROSE_CLASS = '\\u3000-\\u303f\\u3400-\\u4dbf\\u4e00-\\u9fff\\uf900-\\ufaff\\uff00-\\uffef';
const RUN_RE = new RegExp(`[^${PROSE_CLASS}]+`, 'g');

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Does an ASCII run actually contain maths (vs. a plain word or a bare list of
// numbers)? We require a real signal — a LaTeX command / sub- or super-script /
// brace, or an operator wedged between two operands — so ordinary text like
// "a, b" or "5, 8, 6" is left as prose rather than italicised into math mode.
function looksMath(run: string): boolean {
  if (/[\\^_{}]/.test(run)) return true; // \frac, x^2, a_n, {…}
  const compact = run.replace(/\s+/g, '');
  return /[A-Za-z0-9)\].][+\-*/=<>][A-Za-z0-9(\\.[]/.test(compact); // a+b=1, (…)*2
}

// Wrap each math-looking ASCII run in \( … \); leave prose (and the surrounding
// whitespace) untouched. Whitespace is kept OUTSIDE the delimiters so word
// spacing reads naturally. Everything is HTML-escaped — the entities decode back
// to literal characters in the DOM text node, which is what MathJax reads.
function autoDelimit(src: string): string {
  let out = '';
  let last = 0;
  let m: RegExpExecArray | null;
  RUN_RE.lastIndex = 0;
  while ((m = RUN_RE.exec(src))) {
    out += escapeHtml(src.slice(last, m.index));
    const run = m[0];
    const lead = run.match(/^\s*/)![0];
    const trail = run.match(/\s*$/)![0];
    const core = run.slice(lead.length, run.length - trail.length);
    out += core && looksMath(core) ? `${lead}\\(${escapeHtml(core)}\\)${trail}` : escapeHtml(run);
    last = m.index + run.length;
  }
  out += escapeHtml(src.slice(last));
  return out;
}

// Render a statement to typeset-ready HTML. If the author already delimited the
// maths ($…$ / \(…\) / \[…\]) we trust it as-is; otherwise we auto-delimit.
function renderStatement(src: string): string {
  const delimited = /\$|\\\(|\\\[/.test(src);
  const html = delimited ? escapeHtml(src) : autoDelimit(src);
  return html.replace(/\r?\n/g, '<br/>');
}

export function ProblemBody({
  statement,
  latex,
  className,
}: {
  statement?: string;
  latex?: string;
  className?: string;
}) {
  const text = (statement || '').trim();
  const tex = (latex || '').trim();
  const body = text ? renderStatement(text) : '';
  // Did the statement already carry maths? If so, the separate `latex` field is a
  // pulled-out duplicate — don't append it (that's exactly the split the user
  // doesn't want). Only fall back to it when the statement has no maths of its own.
  const statementHasMath = /\\\(|\\\[|\$/.test(body);
  const showTex = tex && !statementHasMath && !text.includes(tex);
  const html =
    body + (showTex ? `<span class="problem-latex-inline">\\[ ${escapeHtml(tex)} \\]</span>` : '');
  const ref = useMathJax<HTMLDivElement>(html);
  return <div ref={ref} className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}
