import { useRef, useState } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';
import { renderMarkdownMath, renderSource, escapeHtml } from '../lib/markdown';
import { useMathJax } from '../hooks/useMathJax';
import { ManimView } from './ManimView';
import { EditorToolbar } from './EditorToolbar';
import type { ChatMsg, RenderMode } from '../types';

// Shared chat control (公共聊天控件, v0.4.3a; controls completed v0.4.7a) — reused by
// the ④ 助手屏 per-line follow-up and the ⑤ 答疑屏. The §C-公共 spec calls for:
//   • 渲染   — every message is Markdown + LaTeX, typeset by MathJax…
//   • 渲染方式下拉 — …or 源码风 / 纯文本 (选 latex+md 渲染 还是 仅文本).
//   • 换行键下拉 — Enter / Alt+Enter / Ctrl+Enter picks which combo inserts a newline
//     (选 Enter 则换行只能点「发送」提交).
//   • 允许识别多选表单 — 特殊符号 / 正则 / \n\r 换行 / 转义: how the raw input is
//     interpreted before it is sent (+ passed to the backend as `allow_special`).
//   • 工具组件 — the SAME md/latex helper toolbar the 校对屏 editor uses (EditorToolbar).
export const SPECIAL_SYMBOLS: string[] = [
  '×', '÷', '±', '√', 'π', '≤', '≥', '≠', '≈', '∞',
  '½', '²', '³', '∑', '∫', '∈', '∴', '∵', '→', '°',
];

// A tutor reply may embed an animation as <manim>…</manim> (a short storyboard note,
// or ready Manim code). We split those out and render each as a <ManimView> instead
// of dumping the raw tag into the message text (issue #4: "识别到 <manim> 前端渲染动画").
const MANIM_RE = /<manim>([\s\S]*?)<\/manim>/gi;

function looksLikeManimCode(s: string): boolean {
  return /from\s+manim\s+import|class\s+\w+\s*\(\s*Scene\s*\)|self\.play\s*\(/.test(s);
}

type Segment = { type: 'text' | 'manim'; value: string };

function splitManim(content: string): Segment[] {
  const segments: Segment[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  MANIM_RE.lastIndex = 0;
  while ((m = MANIM_RE.exec(content))) {
    if (m.index > last) segments.push({ type: 'text', value: content.slice(last, m.index) });
    const inner = m[1].trim();
    if (inner) segments.push({ type: 'manim', value: inner });
    last = m.index + m[0].length;
  }
  if (last < content.length) segments.push({ type: 'text', value: content.slice(last) });
  if (segments.length === 0) segments.push({ type: 'text', value: content });
  return segments;
}

// Plain-text rendering (渲染方式 3): show the message verbatim, newlines preserved,
// no Markdown/LaTeX. Wrapped in <pre> so MathJax (which skips pre/code) leaves any
// \( … \) as literal text instead of typesetting it.
function renderPlain(s: string): string {
  return `<pre class="chat-plain">${escapeHtml(s)}</pre>`;
}

// Render one message according to the chosen 渲染方式:
//   1 全渲染 — Markdown + LaTeX, with <manim> blocks turned into animations.
//   2 源码风 — the raw source, as a code block.
//   3 纯文本 — literal text, newlines kept.
function MessageBody({
  content,
  manimExpression,
  mode,
}: {
  content: string;
  manimExpression: string;
  mode: RenderMode;
}) {
  if (mode === '3') return <div dangerouslySetInnerHTML={{ __html: renderPlain(content) }} />;
  if (mode === '2') return <div dangerouslySetInnerHTML={{ __html: renderSource(content) }} />;
  const segments = splitManim(content);
  return (
    <>
      {segments.map((seg, i) =>
        seg.type === 'manim' ? (
          <ManimView
            key={i}
            expression={manimExpression}
            {...(looksLikeManimCode(seg.value) ? { code: seg.value } : { spec: seg.value })}
          />
        ) : seg.value.trim() ? (
          <div key={i} dangerouslySetInnerHTML={{ __html: renderMarkdownMath(seg.value) }} />
        ) : null,
      )}
    </>
  );
}

// The 换行键 the student picked = which combo inserts a newline. Everything else that
// is a bare Enter then sends (except when the newline key IS Enter — then only the
// 发送 button submits).
type NewlineKey = 'enter' | 'alt' | 'ctrl';
const NEWLINE_OPTS: Array<{ value: NewlineKey; label: string }> = [
  { value: 'enter', label: 'Enter 换行（发送靠按钮）' },
  { value: 'alt', label: 'Alt+Enter 换行（Enter 发送）' },
  { value: 'ctrl', label: 'Ctrl+Enter 换行（Enter 发送）' },
];

const RENDER_OPTS: Array<{ value: RenderMode; label: string }> = [
  { value: '1', label: '渲染：md+latex' },
  { value: '2', label: '渲染：源码风' },
  { value: '3', label: '渲染：纯文本' },
];

// The 允许识别 multi-select form. Each toggle decides whether the raw input is
// interpreted literally / with escapes before sending, and is passed to the backend
// as an `allow_special` hint so the AI knows those forms are intended.
interface SpecialFlags {
  symbols: boolean;   // 特殊符号 (× ÷ √ …)
  regex: boolean;     // 正则表达式
  newline: boolean;   // 字面 \n \r 转成真正的换行
  escape: boolean;    // 其它转义（\t 等）
}
const SPECIAL_FORM: Array<{ key: keyof SpecialFlags; label: string }> = [
  { key: 'symbols', label: '特殊符号（× ÷ √ …）' },
  { key: 'regex', label: '正则表达式' },
  { key: 'newline', label: '\\n \\r 换行' },
  { key: 'escape', label: '转义（\\t 等）' },
];

// Apply the checked interpretation flags to the outgoing text (frontend behaviour).
// Kept deliberately narrow so LaTeX backslashes (\frac, \times, …) are never mangled:
// only the explicit \n/\r/\t sequences are unescaped, and only when asked for.
function applySpecial(text: string, flags: SpecialFlags): string {
  let t = text;
  if (flags.newline) t = t.replace(/\\r\\n/g, '\n').replace(/\\n/g, '\n').replace(/\\r/g, '\n');
  if (flags.escape) t = t.replace(/\\t/g, '\t');
  return t;
}

// Build the `allow_special` hint array from the checked flags (+ the concrete symbol
// glyphs when 特殊符号 is on, preserving the previous助手屏 behaviour).
function buildAllowSpecial(flags: SpecialFlags): string[] {
  const out: string[] = [];
  if (flags.symbols) out.push(...SPECIAL_SYMBOLS);
  if (flags.regex) out.push('正则表达式');
  if (flags.newline) out.push('\\n / \\r 换行符');
  if (flags.escape) out.push('转义序列（\\t 等）');
  return out;
}

export interface SendMeta {
  allowSpecial: string[];
  renderMode: RenderMode;
}

interface ChatBoxProps {
  messages: ChatMsg[];
  onSend: (text: string, meta?: SendMeta) => void | Promise<void>;
  busy?: boolean;
  disabled?: boolean;
  placeholder?: string;
  contextNote?: ReactNode;   // e.g. a chip naming the focused line
  emptyHint?: string;        // shown when there are no messages yet
  provider?: string;         // 'claude:…' | 'template' | 'unavailable' — for a subtle badge
  manimExpression?: string;  // problem context passed to any <manim> block in a reply
}

export function ChatBox({
  messages,
  onSend,
  busy = false,
  disabled = false,
  placeholder = '问点什么…',
  contextNote,
  emptyHint,
  provider,
  manimExpression = '',
}: ChatBoxProps) {
  const [text, setText] = useState('');
  const [renderMode, setRenderMode] = useState<RenderMode>('1');
  const [newlineKey, setNewlineKey] = useState<NewlineKey>('ctrl');
  const [special, setSpecial] = useState<SpecialFlags>({
    symbols: true, regex: false, newline: false, escape: false,
  });
  const taRef = useRef<HTMLTextAreaElement>(null);
  const listRef = useMathJax<HTMLDivElement>(`${renderMode}:${messages.length}`); // re-typeset on change

  const send = () => {
    const t = applySpecial(text, special).trim();
    if (!t || busy || disabled) return;
    setText('');
    void onSend(t, { allowSpecial: buildAllowSpecial(special), renderMode });
  };

  // Insert a real newline at the caret (Alt/Ctrl+Enter don't do this on their own).
  const insertNewline = () => {
    const el = taRef.current;
    if (!el) return;
    const s = el.selectionStart;
    const e = el.selectionEnd;
    const next = text.slice(0, s) + '\n' + text.slice(e);
    setText(next);
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(s + 1, s + 1);
    });
  };

  // 换行键: the picked combo inserts a newline; a bare Enter otherwise sends (unless
  // the newline key IS Enter, in which case only the 发送 button submits). IME
  // composition Enter always falls through to the input method.
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== 'Enter' || e.nativeEvent.isComposing) return;

    const isNewlineCombo =
      (newlineKey === 'enter' && !e.altKey && !e.ctrlKey && !e.shiftKey) ||
      (newlineKey === 'alt' && e.altKey) ||
      (newlineKey === 'ctrl' && e.ctrlKey);

    if (isNewlineCombo) {
      if (newlineKey === 'enter') return; // let the textarea insert the newline itself
      e.preventDefault();
      insertNewline();
      return;
    }
    // A bare Enter (no modifiers) sends — but only when Enter isn't the newline key.
    if (newlineKey !== 'enter' && !e.altKey && !e.ctrlKey && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const providerBadge =
    provider && provider.startsWith('claude') ? null
    : provider === 'template' || provider === 'unavailable' || provider === 'error'
      ? '（AI 暂不可用，可稍后再问）'
      : null;

  const specialCount = Object.values(special).filter(Boolean).length;

  return (
    <div className="chatbox">
      {contextNote ? <div className="chatbox-context">{contextNote}</div> : null}

      <div className="chatbox-log" ref={listRef}>
        {messages.length === 0 ? (
          <p className="chatbox-empty">{emptyHint || '开始你的提问吧。'}</p>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`chat-msg chat-${m.role}`}>
              <span className="chat-role">{m.role === 'user' ? '我' : 'AI'}</span>
              <div className="chat-bubble">
                <MessageBody content={m.content} manimExpression={manimExpression} mode={renderMode} />
              </div>
            </div>
          ))
        )}
        {busy ? <div className="chat-msg chat-assistant"><span className="chat-role">AI</span><div className="chat-bubble chat-typing">…思考中</div></div> : null}
      </div>

      {providerBadge ? <p className="chatbox-note">{providerBadge}</p> : null}

      {/* Shared md/latex tool component (same as the 校对屏 editor). */}
      <EditorToolbar textareaRef={taRef} content={text} setContent={setText} disabled={disabled} />

      <div className="chatbox-input">
        <textarea
          ref={taRef}
          className="chatbox-textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          rows={2}
          disabled={disabled}
          spellCheck={false}
        />
        <div className="chatbox-actions">
          {/* ① 渲染方式：md+latex 渲染 还是 仅文本（修复消失的下拉菜单） */}
          <select
            className="pc-select chatbox-ctl"
            title="消息渲染方式：md+latex / 源码 / 纯文本"
            value={renderMode}
            disabled={disabled}
            onChange={(e) => setRenderMode(e.target.value as RenderMode)}
          >
            {RENDER_OPTS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          {/* ② 换行键：Enter / Alt+Enter / Ctrl+Enter */}
          <select
            className="pc-select chatbox-ctl"
            title="哪个组合键换行；选 Enter 换行则只能点「发送」提交"
            value={newlineKey}
            disabled={disabled}
            onChange={(e) => setNewlineKey(e.target.value as NewlineKey)}
          >
            {NEWLINE_OPTS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          {/* ③ 允许识别特殊符号与表达式（多选表单） */}
          <details className="chatbox-special">
            <summary className="chatbox-ctl chatbox-special-summary" title="允许识别的特殊符号与表达式（多选）">
              允许识别 · {specialCount}
            </summary>
            <div className="chatbox-special-menu">
              {SPECIAL_FORM.map((f) => (
                <label key={f.key} className="chatbox-special-item">
                  <input
                    type="checkbox"
                    checked={special[f.key]}
                    disabled={disabled}
                    onChange={(e) => setSpecial((s) => ({ ...s, [f.key]: e.target.checked }))}
                  />
                  {f.label}
                </label>
              ))}
            </div>
          </details>

          <button className="btn-primary chatbox-send" onClick={send} disabled={busy || disabled || !text.trim()}>
            {busy ? '发送中…' : '发送'}
          </button>
        </div>
      </div>
    </div>
  );
}
