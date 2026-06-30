import { ScreenHeader } from '../components/ScreenHeader';
import { SCREEN_DEFS } from '../config';
import { useStore } from '../store';

// ② Select screen — STUB (v0.4.1a). Will overlay lasso/rect selection on the
// native strokes[] and export only the selected region as a PNG → POST /recognize.
export function SelectScreen({ active }: { active: boolean }) {
  const { workFlow, navTo } = useStore();
  return (
    <section className={`screen${active ? ' active' : ''}`} id="screen-select">
      <ScreenHeader def={SCREEN_DEFS.select} />
      <div className="screen-body">
        <div className="screen-stub">
          <p className="screen-stub-tag">② 选区屏 · v0.4.1a 落地</p>
          <p>在白板上框选要提交的笔画（四角句柄改大小），仅导出选中区域为 PNG。</p>
          <div className="stub-toolbar">
            <button className="btn-secondary" disabled>
              套索
            </button>
            <button className="btn-secondary" disabled>
              矩形
            </button>
            <label className="pc-label">
              OCR 模型
              <select className="pc-select" disabled>
                <option>1 · nex</option>
              </select>
            </label>
          </div>
          <div className="stub-actionbar">
            <span style={{ color: 'var(--text-dim)' }}>
              flow = <b>{workFlow || '—'}</b> · 将 POST /recognize
            </span>
            <button className="btn-primary" onClick={() => navTo('check')}>
              提交选区 →（桩）
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
