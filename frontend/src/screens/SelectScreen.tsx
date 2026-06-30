import { useCallback, useEffect, useRef, useState } from 'react';
import { ScreenHeader } from '../components/ScreenHeader';
import { SCREEN_DEFS } from '../config';
import { useStore } from '../store';
import { recognize, recognizeModels } from '../api';
import type { Point, RecognizeModel } from '../types';
import { clampRect, exportLasso, exportRect, inkBounds, normRect, polyBounds } from '../board/selection';
import type { Rect } from '../board/selection';

// ② Select screen (v0.4.1a) — overlay rect/lasso selection on the native board
// strokes, drag handles to resize, then export ONLY the framed region as a PNG
// → POST /recognize?method=<chosen>. The OCR text lands in the store for ③ 校对屏.

type SelTool = 'rect' | 'lasso';
type Selection = { kind: 'rect'; rect: Rect } | { kind: 'lasso'; points: Point[] } | null;
type Handle = 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w';
type DragTarget = Handle | 'move' | 'draw' | 'lasso';

const HANDLES: Handle[] = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];
const HANDLE_HALF = 6; // half the on-canvas handle square (drawn 12px)
const HIT_TOL = 18; // canvas-px radius for grabbing a handle

// Built-in fallback list if GET /recognize/models is unavailable (older backend).
const FALLBACK_MODELS: RecognizeModel[] = [
  { id: 'nex', label: 'nex-n2-pro 专用 OCR' },
  { id: 'claude', label: 'Claude 视觉' },
  { id: 'auto', label: '自动（nex 失败回退 Claude）' },
];

function handlePoints(r: Rect): Record<Handle, Point> {
  const { x, y, w, h } = r;
  const cx = x + w / 2;
  const cy = y + h / 2;
  return {
    nw: { x, y },
    n: { x: cx, y },
    ne: { x: x + w, y },
    e: { x: x + w, y: cy },
    se: { x: x + w, y: y + h },
    s: { x: cx, y: y + h },
    sw: { x, y: y + h },
    w: { x, y: cy },
  };
}

function rectArea(s: Selection): number {
  if (!s) return 0;
  if (s.kind === 'rect') return s.rect.w * s.rect.h;
  const b = polyBounds(s.points);
  return b ? b.w * b.h : 0;
}

export function SelectScreen({ active }: { active: boolean }) {
  const { board, workFlow, navTo, setOcrText } = useStore();

  const baseRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const selRef = useRef<Selection>(null);
  const dragRef = useRef<{ target: DragTarget; start: Point; startRect: Rect } | null>(null);
  const toolRef = useRef<SelTool>('rect');

  const [tool, setTool] = useState<SelTool>('rect');
  const [models, setModels] = useState<RecognizeModel[]>(FALLBACK_MODELS);
  const [model, setModel] = useState<string>('nex');
  const [hasSel, setHasSel] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // ── overlay rendering ──────────────────────────────────────────────────────
  const drawOverlay = useCallback(() => {
    const cv = overlayRef.current;
    if (!cv) return;
    const ctx = cv.getContext('2d')!;
    ctx.clearRect(0, 0, cv.width, cv.height);

    // Dim everything, then punch out the selection so it reads as a spotlight.
    ctx.fillStyle = 'rgba(15,23,42,0.32)';
    ctx.fillRect(0, 0, cv.width, cv.height);

    const sel = selRef.current;
    if (!sel) return;

    if (sel.kind === 'rect') {
      const r = normRect(sel.rect);
      ctx.clearRect(r.x, r.y, r.w, r.h);
      ctx.strokeStyle = '#3264ff';
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 5]);
      ctx.strokeRect(r.x, r.y, r.w, r.h);
      ctx.setLineDash([]);
      // resize handles
      const hp = handlePoints(r);
      for (const name of HANDLES) {
        const p = hp[name];
        ctx.fillStyle = '#fff';
        ctx.strokeStyle = '#3264ff';
        ctx.lineWidth = 1.5;
        ctx.fillRect(p.x - HANDLE_HALF, p.y - HANDLE_HALF, HANDLE_HALF * 2, HANDLE_HALF * 2);
        ctx.strokeRect(p.x - HANDLE_HALF, p.y - HANDLE_HALF, HANDLE_HALF * 2, HANDLE_HALF * 2);
      }
    } else {
      const pts = sel.points;
      if (pts.length >= 2) {
        // punch out the polygon interior
        ctx.save();
        ctx.globalCompositeOperation = 'destination-out';
        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
        // outline
        ctx.strokeStyle = '#3264ff';
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 5]);
        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
        ctx.closePath();
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }
  }, []);

  const setSelection = useCallback(
    (s: Selection) => {
      selRef.current = s;
      setHasSel(rectArea(s) >= 25);
      drawOverlay();
    },
    [drawOverlay],
  );

  // Snapshot the board + reset the default selection whenever we enter the screen.
  useEffect(() => {
    if (!active) return;
    const base = baseRef.current;
    if (base) {
      const ctx = base.getContext('2d')!;
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, base.width, base.height);
      ctx.drawImage(board.canvas, 0, 0);
    }
    // default selection = padded bounding box of the ink (or the whole board).
    const ink = inkBounds(board.strokes);
    let def: Rect;
    if (ink) {
      const pad = 24;
      def = clampRect(
        { x: ink.x - pad, y: ink.y - pad, w: ink.w + pad * 2, h: ink.h + pad * 2 },
        board.width,
        board.height,
      );
    } else {
      def = { x: 0, y: 0, w: board.width, h: board.height };
    }
    toolRef.current = 'rect';
    setTool('rect');
    setSelection({ kind: 'rect', rect: def });
  }, [active, board, setSelection]);

  // Load the OCR model list once.
  useEffect(() => {
    let alive = true;
    recognizeModels()
      .then((res) => {
        if (!alive || !res.models?.length) return;
        setModels(res.models);
        setModel(res.default || res.models[0].id);
      })
      .catch(() => {
        /* keep FALLBACK_MODELS */
      });
    return () => {
      alive = false;
    };
  }, []);

  // ── pointer interaction ─────────────────────────────────────────────────────
  const toCanvas = (e: React.PointerEvent): Point => {
    const cv = overlayRef.current!;
    const r = cv.getBoundingClientRect();
    return {
      x: (e.clientX - r.left) * (cv.width / r.width),
      y: (e.clientY - r.top) * (cv.height / r.height),
    };
  };

  const hitHandle = (r: Rect, p: Point): Handle | null => {
    const hp = handlePoints(normRect(r));
    for (const name of HANDLES) {
      if (Math.hypot(hp[name].x - p.x, hp[name].y - p.y) <= HIT_TOL) return name;
    }
    return null;
  };

  const onPointerDown = (e: React.PointerEvent) => {
    e.preventDefault();
    overlayRef.current?.setPointerCapture(e.pointerId);
    const p = toCanvas(e);

    if (toolRef.current === 'lasso') {
      dragRef.current = { target: 'lasso', start: p, startRect: { x: 0, y: 0, w: 0, h: 0 } };
      setSelection({ kind: 'lasso', points: [p] });
      return;
    }

    const sel = selRef.current;
    if (sel && sel.kind === 'rect') {
      const r = normRect(sel.rect);
      const h = hitHandle(r, p);
      if (h) {
        dragRef.current = { target: h, start: p, startRect: r };
        return;
      }
      if (p.x >= r.x && p.x <= r.x + r.w && p.y >= r.y && p.y <= r.y + r.h) {
        dragRef.current = { target: 'move', start: p, startRect: r };
        return;
      }
    }
    // start a fresh rectangle from the press point
    dragRef.current = { target: 'draw', start: p, startRect: { x: p.x, y: p.y, w: 0, h: 0 } };
    setSelection({ kind: 'rect', rect: { x: p.x, y: p.y, w: 0, h: 0 } });
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const drag = dragRef.current;
    if (!drag) return;
    e.preventDefault();
    const p = toCanvas(e);

    if (drag.target === 'lasso') {
      const sel = selRef.current;
      if (sel && sel.kind === 'lasso') {
        const last = sel.points[sel.points.length - 1];
        if (!last || Math.hypot(p.x - last.x, p.y - last.y) > 2.5) {
          selRef.current = { kind: 'lasso', points: [...sel.points, p] };
          drawOverlay();
        }
      }
      return;
    }

    const dx = p.x - drag.start.x;
    const dy = p.y - drag.start.y;
    const s = drag.startRect;
    let rect: Rect;

    if (drag.target === 'draw') {
      rect = { x: drag.start.x, y: drag.start.y, w: p.x - drag.start.x, h: p.y - drag.start.y };
    } else if (drag.target === 'move') {
      const moved = clampRect({ x: s.x + dx, y: s.y + dy, w: s.w, h: s.h }, board.width, board.height);
      rect = { x: moved.x, y: moved.y, w: s.w, h: s.h };
    } else {
      // a corner/edge handle: move only the edges its name names
      let L = s.x;
      let T = s.y;
      let R = s.x + s.w;
      let B = s.y + s.h;
      if (drag.target.includes('w')) L = s.x + dx;
      if (drag.target.includes('e')) R = s.x + s.w + dx;
      if (drag.target.includes('n')) T = s.y + dy;
      if (drag.target.includes('s')) B = s.y + s.h + dy;
      rect = { x: L, y: T, w: R - L, h: B - T };
    }
    selRef.current = { kind: 'rect', rect };
    drawOverlay();
  };

  const onPointerUp = (e: React.PointerEvent) => {
    const drag = dragRef.current;
    dragRef.current = null;
    overlayRef.current?.releasePointerCapture?.(e.pointerId);
    if (!drag) return;

    const sel = selRef.current;
    if (!sel) return;
    if (sel.kind === 'rect') {
      const r = clampRect(sel.rect, board.width, board.height);
      setSelection({ kind: 'rect', rect: r });
    } else {
      // discard a degenerate lasso (a tap)
      if (sel.points.length < 3) setSelection(null);
      else setSelection(sel);
    }
  };

  const pickTool = (t: SelTool) => {
    toolRef.current = t;
    setTool(t);
    if (t === 'lasso') {
      setSelection(null);
    } else {
      const ink = inkBounds(board.strokes);
      const def: Rect = ink
        ? clampRect({ x: ink.x - 24, y: ink.y - 24, w: ink.w + 48, h: ink.h + 48 }, board.width, board.height)
        : { x: 0, y: 0, w: board.width, h: board.height };
      setSelection({ kind: 'rect', rect: def });
    }
  };

  // ── submit selected region to OCR ───────────────────────────────────────────
  const submit = async () => {
    const sel = selRef.current;
    if (!sel || busy) return;
    setBusy(true);
    setErr(null);
    try {
      const blob =
        sel.kind === 'rect'
          ? await exportRect(board.canvas, sel.rect)
          : await exportLasso(board.canvas, sel.points);
      if (!blob) {
        setErr('选区为空，请重新框选。');
        setBusy(false);
        return;
      }
      const res = await recognize(blob, model);
      const text = (res.text || '').trim();
      setOcrText(text);
      setBusy(false);
      if (res.status && res.status !== 'ok' && res.status !== 'unconfigured' && !text) {
        // surface the failure reason but still let the student proceed to correct it
        setErr(`识别未成功（${res.status}），可在下一屏手动输入。`);
      }
      navTo('check');
    } catch (e) {
      setBusy(false);
      setErr('识别请求失败：' + (e as Error).message);
    }
  };

  return (
    <section className={`screen${active ? ' active' : ''}`} id="screen-select">
      <ScreenHeader def={SCREEN_DEFS.select} />
      <div className="screen-body">
        <div className="select-toolbar">
          <div className="select-tools">
            <button
              className={`tool-btn ${tool === 'rect' ? 'active' : ''}`}
              onClick={() => pickTool('rect')}
              title="矩形框选，四角/四边句柄可拖动改大小"
            >
              ▭ 矩形
            </button>
            <button
              className={`tool-btn ${tool === 'lasso' ? 'active' : ''}`}
              onClick={() => pickTool('lasso')}
              title="按住拖动，自由勾勒要发送的区域"
            >
              ✎ 套索
            </button>
          </div>
          <span className="select-hint">仅<b>选中区域</b>会作为 PNG 发送给 OCR</span>
        </div>

        <div className="select-stage">
          <canvas ref={baseRef} className="select-base" width={board.width} height={board.height} />
          <canvas
            ref={overlayRef}
            className="select-overlay"
            width={board.width}
            height={board.height}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerLeave={onPointerUp}
          />
        </div>

        {err && <p className="select-err">{err}</p>}

        <div className="select-actionbar">
          <label className="pc-label">
            OCR 模型
            <select className="pc-select" value={model} onChange={(e) => setModel(e.target.value)}>
              {models.map((m, i) => (
                <option key={m.id} value={m.id}>
                  {i + 1} · {m.label}
                </option>
              ))}
            </select>
          </label>
          <span className="select-flow">
            流程 = <b>{workFlow || '—'}</b> · POST /recognize?method={model}
          </span>
          <button className="btn-primary" onClick={submit} disabled={!hasSel || busy}>
            {busy ? '识别中…' : '提交选区 →'}
          </button>
        </div>
      </div>
    </section>
  );
}
