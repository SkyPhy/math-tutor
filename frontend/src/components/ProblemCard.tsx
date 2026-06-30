import { MathText } from './MathText';
import { PracticeControls } from './PracticeControls';
import { SOURCES } from '../config';
import type { Problem } from '../types';

// Difficulty chip colour class, matching the legacy `difficulty-{easy|medium|hard}`
// convention (the backend may send a numeric or string difficulty).
function diffClass(difficulty?: number | string): string {
  const s = String(difficulty ?? '').toLowerCase();
  return 'difficulty-' + s;
}

interface Props {
  problem: Problem | null;
  loading: boolean;
  error: string | null;
  source: string;
  showTags: boolean;
  onToggleTags: () => void;
  onSourceChange: (value: string) => void;
  onRefresh: () => void;
  onGenerateFocused: (focusLogic: string | null, difficulty: number | null) => void;
}

export function ProblemCard({
  problem,
  loading,
  error,
  source,
  showTags,
  onToggleTags,
  onSourceChange,
  onRefresh,
  onGenerateFocused,
}: Props) {
  const tags = problem?.tags || [];
  const srcChip = problem?.generated
    ? '✨ AI 新题'
    : problem?.source === 'ai'
      ? 'AI 题库'
      : '';

  const title = loading ? '正在加载题目…' : error ? '题目加载失败' : problem?.title || '正在加载题目…';

  return (
    <div id="problem-card" className="problem-card">
      <div className="problem-card-top">
        <div id="problem-meta" className={`problem-meta ${showTags ? '' : 'tags-hidden'}`}>
          {problem && !loading && !error ? (
            <>
              {problem.topic ? <span className="problem-topic">{problem.topic}</span> : null}
              {problem.difficulty != null && problem.difficulty !== '' ? (
                <span className={`problem-difficulty ${diffClass(problem.difficulty)}`}>{problem.difficulty}</span>
              ) : null}
              {srcChip ? <span className="problem-source">{srcChip}</span> : null}
              {tags.map((t, i) => {
                const isLogic = t.dimension === '逻辑思维类型';
                return (
                  <span key={i} className={`problem-tag ${isLogic ? 'logic' : ''}`}>
                    {isLogic ? '🧠 ' : ''}
                    {t.tag}
                  </span>
                );
              })}
            </>
          ) : null}
        </div>
        <div className="problem-actions">
          <button
            className="btn-secondary problem-refresh"
            onClick={onRefresh}
            disabled={loading}
            title="按当前来源换一道题"
          >
            🎲 换一题
          </button>
        </div>
      </div>

      {/* "Problem" bar — tags toggle (hidden by default) + 出题来源 picker. */}
      <div className="problem-source-row">
        <span className="problem-row-label">Problem</span>
        <button
          id="tags-toggle-btn"
          className="chip-btn"
          onClick={onToggleTags}
          title="显示 / 隐藏本题的知识点与思维类型标签"
        >
          {showTags ? '🏷 隐藏标签' : '🏷 显示标签'}
        </button>
        <span className="problem-row-spacer" />
        <label className="pc-label">
          来源
          <select className="pc-select" value={source} onChange={(e) => onSourceChange(e.target.value)}>
            {SOURCES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <h2 id="problem-title" className="problem-title">
        {title}
      </h2>
      <p id="problem-statement" className="problem-statement">
        {error ? (
          <span style={{ color: '#ef4444' }}>请确认后端已在 8000 端口运行，然后点「🎲 换一题」。</span>
        ) : (
          problem?.statement || ''
        )}
      </p>
      <MathText latex={problem?.latex} className="problem-latex" />
      {problem?.disclaimer ? <p className="problem-hint-line">{problem.disclaimer}</p> : null}
      <p className="problem-hint-line">✍️ 在白板上作答，完成后点下方「提交 / AI 助手」，或「提问 / 不会做」。</p>

      <PracticeControls onGenerate={onGenerateFocused} />
    </div>
  );
}
