// Math delimiter policy — the single source of truth for how LaTeX is delimited
// before MathJax typesets it.
//
// PROJECT RULE (user, 2026-07): maths must always render **inline / fused** with the
// surrounding text — never pulled onto its own centered line. Example the user gave:
//   「由 $$x^2=1$$ 得 $$x=\pm1$$」  should read as one flowing line, not three.
//
// MathJax renders `$$…$$` and `\[…\]` as *display* math (its own block line) and
// `\(…\)` / `$…$` as *inline* math. So to fuse everything we normalise EVERY form to
// the inline delimiter `\(…\)`. Every render path (markdown preview, MathText,
// ProblemBody, the Manim storyboard) imports from here instead of hand-writing
// delimiters, so the policy lives in exactly one place.

export const INLINE_OPEN = '\\(';
export const INLINE_CLOSE = '\\)';

// Wrap a bare LaTeX body (no delimiters) as inline maths.
export function asInlineMath(latex: string): string {
  return `${INLINE_OPEN}${(latex ?? '').trim()}${INLINE_CLOSE}`;
}

// Rewrite every delimited maths span in a string to the inline form, so `$$…$$`,
// `\[…\]` and `$…$` all fuse in-line exactly like `\(…\)`. `$$` is handled before the
// single-`$` rule; existing `\(…\)` spans are already inline and pass through unchanged.
export function inlineMathDelimiters(src: string): string {
  return (src ?? '')
    .replace(/\$\$([\s\S]+?)\$\$/g, (_, x) => asInlineMath(x)) // $$ display $$ → inline
    .replace(/\\\[([\s\S]+?)\\\]/g, (_, x) => asInlineMath(x)) // \[ display \] → inline
    .replace(/\$([^$\n]+?)\$/g, (_, x) => asInlineMath(x));    // $ inline $     → inline
}
