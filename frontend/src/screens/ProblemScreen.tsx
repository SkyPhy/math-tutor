import { useCallback, useEffect, useState } from 'react';
import { ProblemCard } from '../components/ProblemCard';
import { Whiteboard } from '../components/Whiteboard';
import { fetchProblem } from '../api';
import { PROBLEM_ACTIONS, SOURCES } from '../config';
import { useStore } from '../store';

// ① Problem screen — the wired core. Source picker → /practice/next, tags toggle,
// MathJax problem card, targeted-practice controls, native whiteboard, 3 actions.
export function ProblemScreen({ active }: { active: boolean }) {
  const { problem, setProblem, board, navTo, startWorkFlow, model } = useStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<string>('bank');
  const [showTags, setShowTags] = useState(false);
  const [excludeId, setExcludeId] = useState<string | null>(null);

  const load = useCallback(
    async (opts: { generate?: boolean; focusLogic?: string | null; difficulty?: number | null; source?: string } = {}) => {
      setLoading(true);
      setError(null);
      try {
        const p = await fetchProblem({
          excludeId,
          generate: opts.generate,
          focusLogic: opts.focusLogic ?? null,
          difficulty: opts.difficulty ?? null,
          source: opts.source ?? source,
          model, // AI 出题所用模型（后端按管理员池夹取）
        });
        setProblem(p);
        setExcludeId(p.id);
        board.clear(); // fresh board for each new problem
      } catch {
        setError('load-failed');
        setProblem(null);
      } finally {
        setLoading(false);
      }
    },
    [board, excludeId, setProblem, source, model],
  );

  // Initial problem (default 来源 = bank). Runs once.
  useEffect(() => {
    load({ source: 'bank' });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSourceChange = (value: string) => {
    setSource(value);
    const def = SOURCES.find((s) => s.value === value);
    load({ generate: !!def?.generate, source: value });
  };

  return (
    <section className={`screen${active ? ' active' : ''}`} id="screen-problem">
      <ProblemCard
        problem={problem}
        loading={loading}
        error={error}
        source={source}
        showTags={showTags}
        onToggleTags={() => setShowTags((v) => !v)}
        onSourceChange={onSourceChange}
        onRefresh={() => load()}
        onGenerateFocused={(focusLogic, difficulty) => load({ generate: true, focusLogic, difficulty })}
      />

      <Whiteboard />

      <div id="problem-action-row" className="problem-action-row">
        {PROBLEM_ACTIONS.map((a) => (
          <button
            key={a.label}
            className={a.cls}
            onClick={() => {
              if (a.confirm && !window.confirm(a.confirm)) return;
              if (a.go === 'ask') navTo('ask');
              else if (a.flow) startWorkFlow(a.flow);
            }}
          >
            {a.label}
          </button>
        ))}
      </div>
    </section>
  );
}
