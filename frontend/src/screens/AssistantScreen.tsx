import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ScreenHeader } from '../components/ScreenHeader';
import { ChatBox } from '../components/ChatBox';
import type { SendMeta } from '../components/ChatBox';
import { ManimView, manimProps } from '../components/ManimView';
import { SCREEN_DEFS } from '../config';
import { useStore } from '../store';
import { assistantAnalyze, assistantAsk } from '../api';
import { renderMarkdownMath } from '../lib/markdown';
import { useMathJax } from '../hooks/useMathJax';
import type { AssistAnalysis, ChatMsg } from '../types';

// ④ AI assistant screen (v0.4.3a). The student's corrected work (from ③ 校对屏) is
// sent to POST /assistant/analyze, which returns an analysis ALIGNED line by line:
// the student's step on the left, the AI note on the right — blank where the step is
// fine (无误行留空). Clicking any row opens a follow-up chat grounded in that line
// (POST /assistant/ask), each line keeping its own little conversation.
export function AssistantScreen({ active }: { active: boolean }) {
  const { problem, studentWork, renderMode, sessionId, navHome, model } = useStore();

  const [data, setData] = useState<AssistAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [focusIdx, setFocusIdx] = useState<number | null>(null);
  const [threads, setThreads] = useState<Record<number, ChatMsg[]>>({});
  const [asking, setAsking] = useState(false);
  const [chatProvider, setChatProvider] = useState<string | undefined>();

  const analyzedRef = useRef<string>(''); // the work string we last analysed

  const problemText = useMemo(
    () => [problem?.statement, problem?.latex].filter(Boolean).join('\n'),
    [problem],
  );

  const runAnalyze = useCallback(async () => {
    if (!studentWork.trim()) return;
    setLoading(true);
    setErr(null);
    setFocusIdx(null);
    setThreads({});
    try {
      const res = await assistantAnalyze({
        session_id: sessionId,
        question_id: problem?.id ?? null,
        problem: problemText,
        student_work_md: studentWork,
        render_mode: renderMode,
        model,
      });
      setData(res);
      analyzedRef.current = studentWork;
    } catch (e) {
      setErr('分析失败：' + (e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [studentWork, sessionId, problem?.id, problemText, renderMode, model]);

  // Analyse when the screen opens with fresh work (a new 提交 from the 校对屏).
  useEffect(() => {
    if (active && studentWork.trim() && analyzedRef.current !== studentWork) {
      void runAnalyze();
    }
  }, [active, studentWork, runAnalyze]);

  // Re-typeset the aligned grid whenever the analysis changes.
  const gridRef = useMathJax<HTMLDivElement>(data);

  const focusLine = data?.lines.find((l) => l.idx === focusIdx) || null;

  const sendFollowUp = async (text: string, meta?: SendMeta) => {
    if (focusIdx == null) return;
    const line = data?.lines.find((l) => l.idx === focusIdx) || null;
    const prior = threads[focusIdx] || [];
    setThreads((t) => ({ ...t, [focusIdx]: [...prior, { role: 'user', content: text }] }));
    setAsking(true);
    try {
      const res = await assistantAsk({
        session_id: sessionId,
        message: text,
        question_id: problem?.id ?? null,
        problem: problemText,
        history: prior, // prior turns only; backend appends `message`
        focus: line ? { idx: line.idx, content: line.content, analysis: line.analysis } : null,
        render_mode: renderMode,
        allow_special: meta?.allowSpecial,
        model,
      });
      setChatProvider(res.provider);
      const reply = res.reply || (res.reason ? `（${res.reason}）` : '（AI 暂时无法回答，请稍后再试。）');
      setThreads((t) => ({ ...t, [focusIdx]: [...(t[focusIdx] || []), { role: 'assistant', content: reply }] }));
    } catch (e) {
      setThreads((t) => ({
        ...t,
        [focusIdx]: [...(t[focusIdx] || []), { role: 'assistant', content: '（请求失败：' + (e as Error).message + '）' }],
      }));
    } finally {
      setAsking(false);
    }
  };

  const isTemplate = data?.provider === 'template';

  return (
    <section className={`screen${active ? ' active' : ''}`} id="screen-assistant">
      <ScreenHeader def={SCREEN_DEFS.assistant} />
      <div className="screen-body">
        {problem ? <p className="assist-problem">题目：{problem.title}</p> : null}

        {!studentWork.trim() ? (
          <div className="screen-stub">
            <p className="screen-stub-tag">④ AI 助手屏 · 逐行分析</p>
            <p>还没有可分析的作答。请先在题目屏点「🤖 AI 助手」，经选区 → 校对提交后回到这里。</p>
            <div className="stub-actionbar">
              <span style={{ color: 'var(--text-dim)' }}>作答将逐行对齐分析，无误的行留空；点任意行可就那一步追问。</span>
              <button className="btn-secondary" onClick={navHome}>← 去题目屏</button>
            </div>
          </div>
        ) : (
          <>
            <div className="assist-summary-bar">
              <div className="assist-summary">
                {loading ? '正在逐行分析你的作答…' : data?.summary || '点「重新分析」让 AI 逐行看看你的解法。'}
              </div>
              <div className="assist-summary-side">
                {data?.provider ? (
                  <span className={`assist-provider ${isTemplate ? 'is-template' : ''}`}>
                    {isTemplate ? '模板（AI 暂不可用）' : data.provider}
                  </span>
                ) : null}
                <button className="btn-secondary assist-reanalyze" onClick={runAnalyze} disabled={loading}>
                  {loading ? '分析中…' : '🔄 重新分析'}
                </button>
              </div>
            </div>

            {err ? <p className="select-err">{err}</p> : null}

            {data && data.lines.length > 0 ? (
              <div className="assist-grid" ref={gridRef}>
                <div className="assist-row assist-grid-head">
                  <div className="assist-cell">学生作答</div>
                  <div className="assist-cell">AI 分析（无误留空，点行可追问）</div>
                </div>
                {data.lines.map((l) => {
                  const answered = (threads[l.idx]?.length || 0) > 0;
                  return (
                    <div
                      key={l.idx}
                      role="button"
                      tabIndex={0}
                      className={
                        'assist-row' +
                        (l.has_issue ? ' has-issue' : ' ok') +
                        (focusIdx === l.idx ? ' is-focus' : '') +
                        (answered ? ' answered' : '')
                      }
                      onClick={() => setFocusIdx(focusIdx === l.idx ? null : l.idx)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setFocusIdx(focusIdx === l.idx ? null : l.idx);
                        }
                      }}
                    >
                      <div className="assist-cell assist-left">
                        <span className="assist-idx">{l.idx}</span>
                        <div
                          className="assist-work"
                          dangerouslySetInnerHTML={{ __html: renderMarkdownMath(l.content) }}
                        />
                      </div>
                      <div className="assist-cell assist-right">
                        {l.has_issue ? (
                          <div
                            className="assist-analysis"
                            dangerouslySetInnerHTML={{ __html: renderMarkdownMath(l.analysis) }}
                          />
                        ) : (
                          <span className="assist-ok-tag">✓ 这步没问题</span>
                        )}
                        {l.manim ? <span className="assist-manim">🎬 {l.manim}</span> : null}
                        <span className="assist-ask-hint">{answered ? '💬 已追问' : '追问 →'}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : loading ? (
              <div className="assist-loading">分析中，请稍候…</div>
            ) : null}

            {focusLine ? (
              <div className="assist-followup">
                {focusLine.manim ? (
                  // The clicked line carries a <manim> block — a prose note OR ready
                  // Manim code; manimProps() routes code as-is, prose as a spec.
                  <div
                    className="assist-manim-wrap"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ManimView
                      {...manimProps(focusLine.manim)}
                      expression={problemText || focusLine.content}
                    />
                  </div>
                ) : null}
                <ChatBox
                  messages={threads[focusLine.idx] || []}
                  onSend={sendFollowUp}
                  busy={asking}
                  provider={chatProvider}
                  manimExpression={problemText || focusLine.content}
                  contextNote={
                    <span className="assist-focus-chip">
                      就 <b>第 {focusLine.idx} 行</b> 追问：
                      <span
                        className="assist-focus-work"
                        dangerouslySetInnerHTML={{ __html: renderMarkdownMath(focusLine.content) }}
                      />
                    </span>
                  }
                  emptyHint={
                    focusLine.has_issue
                      ? '就这一步的问题问 AI，例如「为什么这里要变号？」'
                      : '这步看起来没问题，也可以问 AI「还有更好的写法吗？」'
                  }
                  placeholder="就这一行问点什么…"
                />
              </div>
            ) : null}
          </>
        )}
      </div>
    </section>
  );
}
