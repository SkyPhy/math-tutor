import { useEffect, useRef } from 'react';
import type { ReactNode, RefObject } from 'react';
import {
  surround,
  insertLatex,
  toggleBold,
  lineStartPrefix,
  setHeading,
  insertTable,
} from '../lib/editorOps';
import type { EditOp } from '../lib/editorOps';

// ③ 校对屏 Markdown + LaTeX helper toolbars (issue #3). Two regions, each horizontally
// scrollable with the mouse wheel:
//   • md region    — 加粗(toggle) / 标题(下拉等级) / 表格 / 列举 / 引用
//   • latex region — 插入公式 / 分式 / 上标 / 下标 / 平方根 / n次方根 / 对数 / 自然对数 /
//                    方程组 / 特殊符号(下拉)
// The latex tools auto-wrap in $$…$$ when the caret isn't already inside a formula.

// Extra LaTeX symbols for the 特殊符号 dropdown (inserted as commands, auto-$$-wrapped).
const LATEX_SYMBOLS: Array<{ label: string; v: string }> = [
  { label: '≤  \\leq', v: '\\leq ' },
  { label: '≥  \\geq', v: '\\geq ' },
  { label: '≠  \\neq', v: '\\neq ' },
  { label: '± \\pm', v: '\\pm ' },
  { label: '× \\times', v: '\\times ' },
  { label: '÷ \\div', v: '\\div ' },
  { label: '∞ \\infty', v: '\\infty ' },
  { label: 'π \\pi', v: '\\pi ' },
  { label: '∑ \\sum', v: '\\sum_{i=1}^{n} ' },
  { label: '∏ \\prod', v: '\\prod_{i=1}^{n} ' },
  { label: '∫ \\int', v: '\\int ' },
  { label: '∈ \\in', v: '\\in ' },
  { label: '∉ \\notin', v: '\\notin ' },
  { label: '⊆ \\subseteq', v: '\\subseteq ' },
  { label: '∪ \\cup', v: '\\cup ' },
  { label: '∩ \\cap', v: '\\cap ' },
  { label: '→ \\to', v: '\\to ' },
  { label: '⇒ \\Rightarrow', v: '\\Rightarrow ' },
  { label: '∀ \\forall', v: '\\forall ' },
  { label: '∃ \\exists', v: '\\exists ' },
  { label: 'α \\alpha', v: '\\alpha ' },
  { label: 'β \\beta', v: '\\beta ' },
  { label: 'θ \\theta', v: '\\theta ' },
  { label: 'Δ \\Delta', v: '\\Delta ' },
  { label: '° ^\\circ', v: '^\\circ ' },
];

// A wheel-scrollable strip: vertical wheel translates to horizontal scroll (non-passive
// listener so we can preventDefault only when the strip actually overflows).
function ScrollStrip({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (el.scrollWidth <= el.clientWidth || e.deltaY === 0) return;
      e.preventDefault();
      el.scrollLeft += e.deltaY;
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);
  return (
    <div className="check-tool-scroll" ref={ref}>
      {children}
    </div>
  );
}

export function EditorToolbar({
  textareaRef,
  content,
  setContent,
  disabled = false,
}: {
  textareaRef: RefObject<HTMLTextAreaElement>;
  content: string;
  setContent: (v: string) => void;
  disabled?: boolean;
}) {
  // Run a pure EditOp against the live selection, then restore focus + selection.
  const apply = (fn: (c: string, s: number, e: number) => EditOp) => {
    const el = textareaRef.current;
    if (!el) return;
    const s = el.selectionStart;
    const e = el.selectionEnd;
    const op = fn(content, s, e);
    setContent(op.value);
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(op.selStart, op.selEnd);
    });
  };

  return (
    <div className="check-toolbars">
      <div className="check-tool-region">
        <span className="check-tool-tag">MD</span>
        <ScrollStrip>
          <button type="button" className="tool-btn check-tool" title="加粗（已加粗则取消）" disabled={disabled} onClick={() => apply(toggleBold)}>
            <b>B</b> 加粗
          </button>
          <select
            className="pc-select check-tool-select"
            title="标题等级"
            value=""
            disabled={disabled}
            onChange={(ev) => {
              const lvl = Number(ev.target.value);
              if (lvl) apply((c, s, e) => setHeading(c, s, e, lvl));
              ev.target.value = '';
            }}
          >
            <option value="">标题▾</option>
            {[1, 2, 3, 4, 5, 6].map((l) => (
              <option key={l} value={l}>
                {'#'.repeat(l)} H{l}
              </option>
            ))}
          </select>
          <button type="button" className="tool-btn check-tool" title="新建表格" disabled={disabled} onClick={() => apply(insertTable)}>
            ▦ 新建表格
          </button>
          <button type="button" className="tool-btn check-tool" title="无序列表" disabled={disabled} onClick={() => apply((c, s, e) => lineStartPrefix(c, s, e, '- '))}>
            • 列举
          </button>
          <button type="button" className="tool-btn check-tool" title="引用块" disabled={disabled} onClick={() => apply((c, s, e) => lineStartPrefix(c, s, e, '> '))}>
            ❝ 引用
          </button>
        </ScrollStrip>
      </div>

      <div className="check-tool-region">
        <span className="check-tool-tag">LaTeX</span>
        <ScrollStrip>
          <button type="button" className="tool-btn check-tool" title="插入公式块 $$ … $$（其后按键会自动补 $$）" disabled={disabled} onClick={() => apply((c, s, e) => surround(c, s, e, '$$', '$$'))}>
            ƒ 插入公式
          </button>
          <button type="button" className="tool-btn check-tool" title="分式 \frac{a}{b}" disabled={disabled} onClick={() => apply((c, s, e) => insertLatex(c, s, e, '\\frac{', '}{}'))}>
            分式
          </button>
          <button type="button" className="tool-btn check-tool" title="右上角标 x^{n}" disabled={disabled} onClick={() => apply((c, s, e) => insertLatex(c, s, e, '^{', '}'))}>
            x²
          </button>
          <button type="button" className="tool-btn check-tool" title="右下角标 x_{i}" disabled={disabled} onClick={() => apply((c, s, e) => insertLatex(c, s, e, '_{', '}'))}>
            xᵢ
          </button>
          <button type="button" className="tool-btn check-tool" title="平方根 \sqrt{ }" disabled={disabled} onClick={() => apply((c, s, e) => insertLatex(c, s, e, '\\sqrt{', '}'))}>
            √
          </button>
          <button type="button" className="tool-btn check-tool" title="n 次方根 \sqrt[n]{ }" disabled={disabled} onClick={() => apply((c, s, e) => insertLatex(c, s, e, '\\sqrt[n]{', '}'))}>
            ⁿ√
          </button>
          <button type="button" className="tool-btn check-tool" title="对数 \log_{b}" disabled={disabled} onClick={() => apply((c, s, e) => insertLatex(c, s, e, '\\log_{', '}'))}>
            log
          </button>
          <button type="button" className="tool-btn check-tool" title="自然对数 \ln( )" disabled={disabled} onClick={() => apply((c, s, e) => insertLatex(c, s, e, '\\ln(', ')'))}>
            ln
          </button>
          <button
            type="button"
            className="tool-btn check-tool"
            title="方程组 cases"
            disabled={disabled}
            onClick={() => apply((c, s, e) => insertLatex(c, s, e, '\\begin{cases} ', ' \\\\  \\end{cases}'))}
          >
            方程组
          </button>
          <select
            className="pc-select check-tool-select"
            title="特殊符号"
            value=""
            disabled={disabled}
            onChange={(ev) => {
              const v = ev.target.value;
              if (v) apply((c, s, e) => insertLatex(c, s, e, v, ''));
              ev.target.value = '';
            }}
          >
            <option value="">特殊符号▾</option>
            {LATEX_SYMBOLS.map((sym) => (
              <option key={sym.v} value={sym.v}>
                {sym.label}
              </option>
            ))}
          </select>
        </ScrollStrip>
      </div>
    </div>
  );
}
