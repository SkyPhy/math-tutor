import { useState } from 'react';
import { useStore } from '../store';
import { AdminModels } from './AdminModels';

// Header control for the AI model the STUDENT wants to use for generation, grading,
// and help. The options are exactly the admin-opened pool (GET /models, held in the
// store). When the admin has FORCED a model, the picker is locked to it (students
// cannot override an admin's assignment — that switch is admin-only).
//
// A discreet ⚙ button opens the admin-only panel (AdminModels). It is visible to
// everyone but useless without an admin login — the backend gates every write with
// require_admin — so a student clicking it just sees a sign-in they can't pass.
export function ModelControls() {
  const { models, model, setModel, forcedModel } = useStore();
  const [adminOpen, setAdminOpen] = useState(false);

  const locked = !!forcedModel;
  // Show the forced model even if it isn't in the student pool list, so the label
  // is never blank when locked.
  const options = models.length
    ? models
    : model
      ? [{ id: model, label: model, provider: '', provider_label: '' }]
      : [];

  return (
    <div className="model-controls">
      <label className="model-label" htmlFor="ai-model-select">AI 模型</label>
      <select
        id="ai-model-select"
        className="pc-select model-select"
        value={model}
        disabled={locked || options.length === 0}
        title={locked ? '管理员已强制指定模型，学生不可更改' : '选择用于出题 / 判分 / 答疑的 AI 模型'}
        onChange={(e) => setModel(e.target.value)}
      >
        {options.map((m) => (
          <option key={m.id} value={m.id}>
            {m.label}{m.provider_label ? ` · ${m.provider_label}` : ''}
          </option>
        ))}
      </select>
      {locked ? <span className="model-locked" title="管理员强制分配">🔒</span> : null}
      <button
        className="model-admin-btn"
        onClick={() => setAdminOpen(true)}
        title="模型管理（仅管理员）"
        aria-label="模型管理（仅管理员）"
      >
        ⚙
      </button>
      {adminOpen ? <AdminModels onClose={() => setAdminOpen(false)} /> : null}
    </div>
  );
}
