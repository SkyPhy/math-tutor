import { ScreenHeader } from '../components/ScreenHeader';
import { SCREEN_DEFS } from '../config';

// ④ AI assistant screen — STUB (v0.4.3a). Will POST /assistant/analyze and align
// "student work | AI analysis" line by line (empty right cell = no issue), with
// per-line follow-up via POST /assistant/ask.
export function AssistantScreen({ active }: { active: boolean }) {
  return (
    <section className={`screen${active ? ' active' : ''}`} id="screen-assistant">
      <ScreenHeader def={SCREEN_DEFS.assistant} />
      <div className="screen-body">
        <div className="screen-stub">
          <p className="screen-stub-tag">④ AI 助手屏 · v0.4.3a 落地（POST /assistant/analyze）</p>
          <p>逐行对齐「学生作答 | AI 分析」，无误的行留空；可对某行追问。</p>
          <div className="assist-cols">
            <div className="col-head">学生作答</div>
            <div className="col-head col-right">AI 分析</div>
            <div className="col-cell">2x + 4 = 10</div>
            <div className="col-cell col-right empty">（留空 — 这步没问题）</div>
            <div className="col-cell">2x = 10 + 4</div>
            <div className="col-cell col-right">⚠ 移项要变号，应为 10 − 4</div>
          </div>
        </div>
      </div>
    </section>
  );
}
