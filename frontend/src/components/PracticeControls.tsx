import { useEffect, useState } from 'react';
import { tagsCatalogue } from '../api';
import { DIFFICULTY_LADDER } from '../config';

// Targeted practice: pick a logic-thinking type (from the live tag store) + an
// open-ended difficulty, then ask the AI to generate one. Mirrors the legacy
// initPracticeControls() / generateFocused().
export function PracticeControls({
  onGenerate,
}: {
  onGenerate: (focusLogic: string | null, difficulty: number | null) => void;
}) {
  const [logicGroups, setLogicGroups] = useState<Record<string, Array<{ name: string }>>>({});
  const [focusLogic, setFocusLogic] = useState('');
  const [difficulty, setDifficulty] = useState('');

  useEffect(() => {
    let alive = true;
    tagsCatalogue()
      .then((data) => {
        if (alive) setLogicGroups((data.catalogue && data.catalogue.logic) || {});
      })
      .catch(() => {
        /* backend offline — selector just stays "不限" */
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="practice-controls" id="practice-controls">
      <label className="pc-label">
        思维类型
        <select className="pc-select" value={focusLogic} onChange={(e) => setFocusLogic(e.target.value)}>
          <option value="">不限</option>
          {Object.keys(logicGroups).map((family) => (
            <optgroup key={family} label={family}>
              {(logicGroups[family] || []).map((t) => (
                <option key={t.name} value={t.name}>
                  {t.name}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
      <label className="pc-label">
        难度
        <select className="pc-select" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
          <option value="">不限</option>
          {DIFFICULTY_LADDER.map((d) => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
      </label>
      <button
        className="btn-secondary"
        title="按所选思维类型 / 难度让 AI 出题"
        onClick={() => onGenerate(focusLogic || null, difficulty ? parseInt(difficulty, 10) : null)}
      >
        🎯 按要求出题
      </button>
    </div>
  );
}
