import { useStore } from '../store';
import type { ScreenDef } from '../config';

// Shared header for screens ②–⑤: a back button + gradient title + optional subtitle.
export function ScreenHeader({ def }: { def: ScreenDef }) {
  const { navBack } = useStore();
  return (
    <>
      <div className="screen-nav">
        <button className="btn-secondary screen-back-btn" onClick={navBack}>
          ← 返回
        </button>
        <h2 className="screen-title">{def.title}</h2>
      </div>
      {def.sub ? <p className="screen-sub">{def.sub}</p> : null}
    </>
  );
}
