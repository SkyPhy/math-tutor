// Pure text-editing operations for the 校对屏 (③) Markdown + LaTeX helper toolbars.
// Each takes the current content and the selection [s, e) and returns the new value
// plus where the selection should land — the component applies it and restores the
// caret. Pure + framework-free so the tricky bits (bold toggle, auto-$$ wrapping)
// are unit-testable in isolation.

export interface EditOp {
  value: string;
  selStart: number;
  selEnd: number;
}

// Wrap the selection with `before`/`after`, keeping the inner text selected (or the
// caret between the two when the selection was empty).
export function surround(content: string, s: number, e: number, before: string, after: string): EditOp {
  const sel = content.slice(s, e);
  const value = content.slice(0, s) + before + sel + after + content.slice(e);
  return { value, selStart: s + before.length, selEnd: s + before.length + sel.length };
}

// Is position `pos` inside a `$$ … $$` maths span? True when an odd number of `$$`
// delimiters precede it. Drives the "auto-insert $$ when not already in maths" rule.
export function isInsideMath(content: string, pos: number): boolean {
  const before = content.slice(0, pos);
  const count = (before.match(/\$\$/g) || []).length;
  return count % 2 === 1;
}

// Insert a LaTeX snippet around the selection; if the caret is NOT already inside a
// `$$ … $$` span, wrap the whole thing in `$$ … $$` so the formula renders (issue #3:
// "检测到后续插入的文本不在 $$$$ 中时，自动在两侧插入 $$").
export function insertLatex(content: string, s: number, e: number, before: string, after: string): EditOp {
  const inside = isInsideMath(content, s);
  const b = inside ? before : '$$' + before;
  const a = inside ? after : after + '$$';
  const sel = content.slice(s, e);
  const value = content.slice(0, s) + b + sel + a + content.slice(e);
  return { value, selStart: s + b.length, selEnd: s + b.length + sel.length };
}

// Toggle Markdown bold: strip `**` when the selection already is bold (either the
// selection includes the markers or they sit just outside it), else wrap it.
export function toggleBold(content: string, s: number, e: number): EditOp {
  const sel = content.slice(s, e);
  if (sel.length >= 4 && sel.startsWith('**') && sel.endsWith('**')) {
    const inner = sel.slice(2, -2);
    const value = content.slice(0, s) + inner + content.slice(e);
    return { value, selStart: s, selEnd: s + inner.length };
  }
  if (content.slice(s - 2, s) === '**' && content.slice(e, e + 2) === '**') {
    const value = content.slice(0, s - 2) + sel + content.slice(e + 2);
    return { value, selStart: s - 2, selEnd: s - 2 + sel.length };
  }
  return surround(content, s, e, '**', '**');
}

// Add a line-prefix (list `- `, quote `> `) at the start of the line the caret is on.
export function lineStartPrefix(content: string, s: number, e: number, prefix: string): EditOp {
  const lineStart = content.lastIndexOf('\n', s - 1) + 1;
  const value = content.slice(0, lineStart) + prefix + content.slice(lineStart);
  return { value, selStart: s + prefix.length, selEnd: e + prefix.length };
}

// Set the current line's Markdown heading level (replacing any existing `#` markers).
export function setHeading(content: string, s: number, e: number, level: number): EditOp {
  const lineStart = content.lastIndexOf('\n', s - 1) + 1;
  const rest = content.slice(lineStart);
  const stripped = rest.replace(/^#{1,6}[ \t]+/, '');
  const removed = rest.length - stripped.length;
  const prefix = '#'.repeat(level) + ' ';
  const value = content.slice(0, lineStart) + prefix + stripped;
  const delta = prefix.length - removed;
  return {
    value,
    selStart: Math.max(lineStart, s + delta),
    selEnd: Math.max(lineStart, e + delta),
  };
}

// Replace the selection with literal text (caret lands after it).
export function insertText(content: string, s: number, e: number, text: string): EditOp {
  const value = content.slice(0, s) + text + content.slice(e);
  return { value, selStart: s + text.length, selEnd: s + text.length };
}

// Drop a Markdown table skeleton at the caret.
export function insertTable(content: string, s: number, e: number): EditOp {
  const tpl = '\n| 列1 | 列2 |\n| --- | --- |\n| 　 | 　 |\n';
  const value = content.slice(0, s) + tpl + content.slice(e);
  const caret = s + tpl.length;
  return { value, selStart: caret, selEnd: caret };
}
