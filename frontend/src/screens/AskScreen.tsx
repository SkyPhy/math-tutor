import { useEffect, useMemo, useState } from 'react';
import { ScreenHeader } from '../components/ScreenHeader';
import { ChatBox } from '../components/ChatBox';
import type { SendMeta } from '../components/ChatBox';
import { ProblemBody } from '../components/ProblemBody';
import { SCREEN_DEFS } from '../config';
import { useStore } from '../store';
import { analyzeProblem, analyzeText, claudeChat } from '../api';
import type { ChatMsg } from '../types';

// ⑤ Ask screen (v0.4.4a). Entered from 题目屏「🙋 提问 / 不会做」 — NO whiteboard.
// Two affordances over the shared ChatBox:
//   • 🔍 解析此题 → POST /analyze (a Socratic level-0 read of the problem — never the
//     final answer), shown as the opening assistant turn.
//   • free Q&A → POST /claude/chat, grounded on the problem, Socratic (won't dump answers).
export function AskScreen({ active }: { active: boolean }) {
  const { problem, sessionId, model } = useStore();

  const [thread, setThread] = useState<ChatMsg[]>([]);
  const [busy, setBusy] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [provider, setProvider] = useState<string | undefined>();
  const [err, setErr] = useState<string | null>(null);

  const expr = useMemo(
    () => [problem?.statement, problem?.latex].filter(Boolean).join('\n'),
    [problem],
  );

  // A new problem starts a fresh conversation.
  useEffect(() => {
    setThread([]);
    setProvider(undefined);
    setErr(null);
  }, [problem?.id]);

  const doAnalyze = async () => {
    if (!expr.trim() || analyzing) return;
    setAnalyzing(true);
    setErr(null);
    try {
      const res = await analyzeProblem(expr, model);
      const text = analyzeText(res) || '（暂无解析——可直接在下面提问。）';
      setProvider(res.ai_provider);
      setThread((t) => [...t, { role: 'assistant', content: '🔍 **解析此题**\n\n' + text }]);
    } catch (e) {
      setErr('解析失败：' + (e as Error).message);
    } finally {
      setAnalyzing(false);
    }
  };

  const send = async (text: string, meta?: SendMeta) => {
    const prior = thread; // turns before this message (backend appends `message`)
    setThread((t) => [...t, { role: 'user', content: text }]);
    setBusy(true);
    try {
      const res = await claudeChat({
        message: text,
        expression: expr,
        session_id: sessionId,
        history: prior,
        allow_special: meta?.allowSpecial,
        model,
      });
      setProvider(res.provider);
      const reply = res.reply || (res.reason ? `（${res.reason}）` : '（AI 暂时无法回答，请稍后再试。）');
      setThread((t) => [...t, { role: 'assistant', content: reply }]);
    } catch (e) {
      setThread((t) => [...t, { role: 'assistant', content: '（请求失败：' + (e as Error).message + '）' }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={`screen${active ? ' active' : ''}`} id="screen-ask">
      <ScreenHeader def={SCREEN_DEFS.ask} />
      <div className="screen-body">
        {problem ? (
          <div className="ask-problem-card">
            <div className="ask-problem-title">{problem.title}</div>
            <ProblemBody statement={problem.statement} latex={problem.latex} className="ask-problem-body" />
            {problem.disclaimer ? <p className="ask-disclaimer">{problem.disclaimer}</p> : null}
          </div>
        ) : (
          <p className="assist-problem">还没有选题，请先回题目屏选一道题再来提问。</p>
        )}

        <div className="ask-actions">
          <button className="btn-secondary" onClick={doAnalyze} disabled={analyzing || !expr.trim()}>
            {analyzing ? '解析中…' : '🔍 解析此题'}
          </button>
          <span className="ask-hint">苏格拉底式：引导你一步步想通，不直接给最终答案。</span>
        </div>

        {err ? <p className="select-err">{err}</p> : null}

        <ChatBox
          messages={thread}
          onSend={send}
          busy={busy}
          provider={provider}
          manimExpression={expr}
          emptyHint="就这道题问点什么，或先点「🔍 解析此题」看看思路。"
          placeholder="就这道题提问…"
        />
      </div>
    </section>
  );
}
