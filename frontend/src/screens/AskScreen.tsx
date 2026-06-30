import { ScreenHeader } from '../components/ScreenHeader';
import { SCREEN_DEFS } from '../config';
import { useStore } from '../store';

// ⑤ Ask screen — STUB (v0.4.4a). Entered from "提问 / 不会做" (no whiteboard).
// Will offer 解析此题 (POST /analyze) + Q&A (POST /claude/chat), Socratic, never
// dumping the final answer.
export function AskScreen({ active }: { active: boolean }) {
  const { problem, navBack } = useStore();
  return (
    <section className={`screen${active ? ' active' : ''}`} id="screen-ask">
      <ScreenHeader def={SCREEN_DEFS.ask} />
      <div className="screen-body">
        <div className="screen-stub">
          <p className="screen-stub-tag">⑤ 答疑屏 · v0.4.4a 落地</p>
          {problem ? <p style={{ color: 'var(--text-dim)' }}>题目：{problem.title}</p> : null}
          <p>不经白板，就当前题目直接问答（苏格拉底式、不直接给答案）。</p>
          <div className="stub-actionbar">
            <span style={{ color: 'var(--text-dim)' }}>解析此题 → POST /analyze · 问答 → POST /claude/chat</span>
            <button className="btn-secondary" onClick={navBack}>
              ← 返回题目
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
