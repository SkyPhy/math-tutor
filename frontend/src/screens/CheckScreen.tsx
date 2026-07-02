import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ScreenHeader } from '../components/ScreenHeader';
import { EditorToolbar } from '../components/EditorToolbar';
import { SCREEN_DEFS } from '../config';
import { useStore } from '../store';
import { workList, workSave, verify } from '../api';
import type { VerifyResp } from '../api';
import { renderMarkdownMath, renderSource } from '../lib/markdown';
import { useMathJax } from '../hooks/useMathJax';
import type { RenderMode, WorkDraft } from '../types';

// ③ Check screen (v0.4.2a) — review the OCR text, correct it character-by-character,
// pick a render mode (1 full md+latex / 2 source / 3 plain), name + 存草稿 it to the
// personal draft library (POST /work/save), then 提交: submit-flow → /verify consensus
// grading, assist-flow → the AI assistant screen.

const RENDER_MODES: Array<{ value: RenderMode; label: string }> = [
  { value: '1', label: '1 · 全渲染（md+latex）' },
  { value: '2', label: '2 · 源码风' },
  { value: '3', label: '3 · 纯文本（默认）' },
];

export function CheckScreen({ active }: { active: boolean }) {
  const { workFlow, navTo, navHome, ocrText, problem, sessionId, setStudentWork, setRenderMode, model } = useStore();

  const [content, setContent] = useState('');
  const [mode, setMode] = useState<RenderMode>('3');
  const [filename, setFilename] = useState('');
  const [draftId, setDraftId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<WorkDraft[]>([]);
  const [note, setNote] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<'' | 'tmp' | 'final'>('');
  const [grade, setGrade] = useState<VerifyResp | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // A new OCR result = a fresh arrival from the select screen: seed the editor and
  // reset the per-attempt state (draft id, grade). Edits survive while ocrText is
  // unchanged (navigating back and forth without re-recognising).
  useEffect(() => {
    setContent(ocrText);
    setDraftId(null);
    setGrade(null);
    setNote(null);
    setErr(null);
    setFilename(problem ? `${problem.id}-作答` : '我的作答');
  }, [ocrText, problem]);

  // Load this question's existing drafts so a saved one can be reopened (续作).
  const refreshDrafts = useCallback(async () => {
    try {
      const res = await workList(sessionId, problem?.id ?? null);
      setDrafts(res.drafts || []);
    } catch {
      /* offline / older backend — the list just stays empty */
    }
  }, [sessionId, problem?.id]);

  useEffect(() => {
    if (active) refreshDrafts();
  }, [active, refreshDrafts]);

  // ── render-mode preview (modes 1/2 only; plain text needs no preview) ──
  const previewHtml = useMemo(() => {
    if (mode === '1') return renderMarkdownMath(content);
    if (mode === '2') return renderSource(content);
    return '';
  }, [content, mode]);
  const previewRef = useMathJax<HTMLDivElement>(previewHtml);

  // ── persist (存草稿 / 提交 both go through here) ──
  const save = async (status: 'tmp' | 'final'): Promise<WorkDraft | null> => {
    setBusy(status);
    setErr(null);
    try {
      const draft = await workSave({
        session_id: sessionId,
        question_id: problem?.id ?? null,
        filename: filename.trim() || null,
        content_md: content,
        render_mode: mode,
        status,
        draft_id: draftId,
      });
      setDraftId(draft.id);
      await refreshDrafts();
      return draft;
    } catch (e) {
      setErr('保存失败：' + (e as Error).message);
      return null;
    } finally {
      setBusy('');
    }
  };

  const saveDraft = async () => {
    const d = await save('tmp');
    if (d) setNote(`已存草稿「${d.filename || '未命名'}」（${new Date(d.updated_at).toLocaleTimeString()}）`);
  };

  const submit = async () => {
    const d = await save('final');
    if (!d) return;
    setStudentWork(content);
    setRenderMode(mode);
    if (workFlow === 'assist') {
      navTo('assistant');
      return;
    }
    // submit flow → consensus grading
    setBusy('final');
    setNote('提交成功，正在判分…');
    try {
      const expression = (problem?.statement || problem?.latex || '').trim();
      const res = await verify({
        expression,
        answer: content,
        session_id: sessionId,
        question_id: problem?.id,
        model,
      });
      setGrade(res);
      setNote(null);
    } catch (e) {
      setErr('判分失败：' + (e as Error).message);
      setNote(null);
    } finally {
      setBusy('');
    }
  };

  const loadDraft = (d: WorkDraft) => {
    setContent(d.content_md || '');
    setDraftId(d.id);
    setFilename(d.filename || '');
    if (d.render_mode === '1' || d.render_mode === '2' || d.render_mode === '3') setMode(d.render_mode);
    setGrade(null);
    setNote(`已载入草稿「${d.filename || '未命名'}」，可继续修改。`);
  };

  // The md/latex tool component is always available (writing aid regardless of mode);
  // the live preview only makes sense for the rendering modes (1 full / 2 source).
  const showPreview = mode === '1' || mode === '2';

  return (
    <section className={`screen${active ? ' active' : ''}`} id="screen-check">
      <ScreenHeader def={SCREEN_DEFS.check} />
      <div className="screen-body">
        <div className="check-card">
          <div className="check-head">
            <span className="check-head-label">你的书写过程（可逐字纠错）</span>
            <label className="pc-label">
              渲染方式
              <select className="pc-select" value={mode} onChange={(e) => setMode(e.target.value as RenderMode)}>
                {RENDER_MODES.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <EditorToolbar textareaRef={textareaRef} content={content} setContent={setContent} />

          <textarea
            ref={textareaRef}
            className="check-editor"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="（尚无识别结果——可在这里直接输入，或从②选区屏「提交选区」让 OCR 识别）"
            spellCheck={false}
          />

          {showPreview && (
            <div className="check-preview-wrap">
              <span className="check-preview-label">预览</span>
              <div
                ref={previewRef}
                className="check-preview"
                dangerouslySetInnerHTML={{ __html: previewHtml }}
              />
            </div>
          )}

          {err && <p className="select-err">{err}</p>}
          {note && <p className="check-note">{note}</p>}

          {grade && <GradePanel grade={grade} onNext={navHome} />}

          {!grade && (
            <div className="check-actionbar">
              <label className="pc-label check-filename">
                文件名
                <input
                  type="text"
                  className="check-filename-input"
                  value={filename}
                  onChange={(e) => setFilename(e.target.value)}
                  placeholder="给这份作答起个名字"
                />
              </label>
              <button className="btn-secondary" onClick={saveDraft} disabled={!!busy}>
                {busy === 'tmp' ? '保存中…' : '💾 存草稿'}
              </button>
              <button className="btn-primary check-submit" onClick={submit} disabled={!!busy || !content.trim()}>
                {busy === 'final'
                  ? '提交中…'
                  : workFlow === 'assist'
                    ? '提交 → AI 助手 →'
                    : '提交 → 判分'}
              </button>
            </div>
          )}

          {drafts.length > 0 && (
            <div className="check-drafts">
              <span className="check-drafts-label">我的草稿（本题）</span>
              <ul className="check-drafts-list">
                {drafts.map((d) => (
                  <li key={d.id} className={d.id === draftId ? 'is-current' : ''}>
                    <button className="check-draft-open" onClick={() => loadDraft(d)} title="载入这份草稿继续作答">
                      📄 {d.filename || '未命名'}
                    </button>
                    <span className={`check-draft-status status-${d.status}`}>
                      {d.status === 'final' ? '已提交' : '草稿'}
                    </span>
                    <span className="check-draft-time">{new Date(d.updated_at).toLocaleString()}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

// Consensus-grading verdict for the submit flow. Honest about an undetermined
// verdict (gateway down / paths disagreed) rather than guessing.
function GradePanel({ grade, onNext }: { grade: VerifyResp; onNext: () => void }) {
  const correct = grade.answer_correct;
  const state = correct === true ? 'correct' : correct === false ? 'wrong' : 'unknown';
  const headline =
    state === 'correct' ? '✅ 答对了！' : state === 'wrong' ? '❌ 再想想' : '🤔 暂未判定';
  return (
    <div className={`check-grade grade-${state}`}>
      <div className="check-grade-head">{headline}</div>
      <div className="check-grade-meta">
        {grade.judged_by ? <span>判定方式：{grade.judged_by}</span> : null}
        {grade.votes_label ? <span>{grade.votes_label}</span> : null}
        {grade.ground_truth != null ? <span>参考答案：{String(grade.ground_truth)}</span> : null}
      </div>
      {grade.judge_reason ? <p className="check-grade-reason">{grade.judge_reason}</p> : null}
      {state === 'unknown' ? (
        <p className="check-grade-reason">网关不可用或多路推理未达成共识，可稍后重试或换一题。</p>
      ) : null}
      <button className="btn-primary check-next" onClick={onNext}>
        ← 返回题目 / 下一题
      </button>
    </div>
  );
}
