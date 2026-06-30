import { ScreenHeader } from '../components/ScreenHeader';
import { SCREEN_DEFS } from '../config';
import { useStore } from '../store';

// ③ Check screen — STUB (v0.4.2a). Will echo the OCR text for character-level
// correction (3 render modes), save a named draft (POST /work/save), then route:
// submit → POST /verify (consensus grading); assist → AI assistant screen.
export function CheckScreen({ active }: { active: boolean }) {
  const { workFlow, navTo, navHome } = useStore();
  return (
    <section className={`screen${active ? ' active' : ''}`} id="screen-check">
      <ScreenHeader def={SCREEN_DEFS.check} />
      <div className="screen-body">
        <div className="screen-stub">
          <p className="screen-stub-tag">③ 校对屏 · v0.4.2a 落地</p>
          <p>回显 OCR 识别文本供逐字纠错（3 种渲染方式），可命名存草稿或提交。</p>
          <div className="stub-board">
            2x + 4 = 10{'\n'}x = 3 ← （示例：将来是可编辑的识别结果）
          </div>
          <div className="stub-actionbar">
            <span style={{ color: 'var(--text-dim)' }}>存草稿 → POST /work/save</span>
            {workFlow === 'submit' ? (
              <button
                className="btn-primary"
                onClick={() => {
                  alert('v0.4.2a：提交 → POST /verify 共识判分');
                  navHome();
                }}
              >
                提交（判分桩）
              </button>
            ) : (
              <button className="btn-primary" onClick={() => navTo('assistant')}>
                提交 → AI 助手 →（桩）
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
