// Native whiteboard engine — a faithful port of the legacy <canvas> drawing code.
//
// It owns its own <canvas> element (so it survives screen navigation: the React
// <Whiteboard> just mounts/detaches the element). `strokes` is an ordered op list
// so the board can be rebuilt at any time, which the stroke-eraser and the future
// selection screen both rely on.
import type { Op, Point, Tool } from '../types';

const CANVAS_W = 800;
const CANVAS_H = 600;
const PEN_WEIGHT = 3;

export class BoardEngine {
  readonly canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;

  strokes: Op[] = [];
  private currentOp: Op | null = null;
  private isDrawing = false;

  tool: Tool = 'pen';
  eraserRadius = 20;
  private cursor = { x: 0, y: 0, inside: false };

  private raf = 0;
  private destroyed = false;

  constructor() {
    const c = document.createElement('canvas');
    c.width = CANVAS_W;
    c.height = CANVAS_H;
    c.style.touchAction = 'none';
    c.style.display = 'block';
    c.style.width = '100%';
    c.style.height = 'auto';
    this.canvas = c;
    this.ctx = c.getContext('2d')!;
    this.ctx.fillStyle = 'white';
    this.ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

    c.addEventListener('pointerdown', this.onPointerDown);
    c.addEventListener('pointermove', this.onPointerMove);
    c.addEventListener('pointerleave', this.onPointerLeave);
    window.addEventListener('pointerup', this.onPointerUp);

    this.raf = requestAnimationFrame(this.renderLoop);
  }

  get width() {
    return CANVAS_W;
  }

  get height() {
    return CANVAS_H;
  }

  /** Move the canvas into a host container (the active screen's board area). */
  mount(host: HTMLElement) {
    host.appendChild(this.canvas);
  }

  /** Detach the canvas from its current parent without losing strokes. */
  detach() {
    this.canvas.parentElement?.removeChild(this.canvas);
  }

  destroy() {
    this.destroyed = true;
    cancelAnimationFrame(this.raf);
    this.canvas.removeEventListener('pointerdown', this.onPointerDown);
    this.canvas.removeEventListener('pointermove', this.onPointerMove);
    this.canvas.removeEventListener('pointerleave', this.onPointerLeave);
    window.removeEventListener('pointerup', this.onPointerUp);
  }

  private renderLoop = () => {
    if (this.destroyed) return;
    this.draw();
    this.raf = requestAnimationFrame(this.renderLoop);
  };

  // Map a pointer event to canvas-buffer coordinates (0..800, 0..600).
  private getCanvasPos(e: PointerEvent): Point {
    const rect = this.canvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) * (CANVAS_W / rect.width),
      y: (e.clientY - rect.top) * (CANVAS_H / rect.height),
    };
  }

  private inBounds(p: Point) {
    return p.x >= 0 && p.x <= CANVAS_W && p.y >= 0 && p.y <= CANVAS_H;
  }

  // ── Rendering ──────────────────────────────────────────────────────────────
  private draw() {
    const ctx = this.ctx;
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

    for (const op of this.strokes) {
      if (op.mode === 'pen') {
        ctx.strokeStyle = '#000';
        ctx.lineWidth = op.weight;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        if (op.points.length === 1) {
          ctx.fillStyle = '#000';
          ctx.beginPath();
          ctx.arc(op.points[0].x, op.points[0].y, op.weight / 2, 0, Math.PI * 2);
          ctx.fill();
        } else {
          ctx.beginPath();
          ctx.moveTo(op.points[0].x, op.points[0].y);
          for (let i = 1; i < op.points.length; i++) ctx.lineTo(op.points[i].x, op.points[i].y);
          ctx.stroke();
        }
      } else if (op.mode === 'erasePixels') {
        ctx.globalCompositeOperation = 'destination-out';
        ctx.fillStyle = 'rgba(0,0,0,1)';
        if (op.points.length === 1) {
          ctx.beginPath();
          ctx.arc(op.points[0].x, op.points[0].y, op.radius, 0, Math.PI * 2);
          ctx.fill();
        } else {
          ctx.strokeStyle = 'rgba(0,0,0,1)';
          ctx.lineWidth = op.radius * 2;
          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';
          ctx.beginPath();
          ctx.moveTo(op.points[0].x, op.points[0].y);
          for (let i = 1; i < op.points.length; i++) ctx.lineTo(op.points[i].x, op.points[i].y);
          ctx.stroke();
        }
        ctx.globalCompositeOperation = 'source-over';
      }
    }

    // Live preview of the pen stroke in progress.
    if (this.isDrawing && this.tool === 'pen' && this.currentOp && this.currentOp.points.length > 1) {
      ctx.strokeStyle = '#3264ff';
      ctx.lineWidth = PEN_WEIGHT;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.beginPath();
      ctx.moveTo(this.currentOp.points[0].x, this.currentOp.points[0].y);
      for (let i = 1; i < this.currentOp.points.length; i++)
        ctx.lineTo(this.currentOp.points[i].x, this.currentOp.points[i].y);
      ctx.stroke();
    }

    // Live preview of the area eraser in progress.
    if (
      this.isDrawing &&
      this.tool === 'erasePixels' &&
      this.currentOp &&
      this.currentOp.mode === 'erasePixels' &&
      this.currentOp.points.length > 0
    ) {
      ctx.save();
      ctx.globalCompositeOperation = 'destination-out';
      ctx.fillStyle = 'rgba(0,0,0,1)';
      ctx.strokeStyle = 'rgba(0,0,0,1)';
      ctx.lineWidth = this.currentOp.radius * 2;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      if (this.currentOp.points.length === 1) {
        ctx.beginPath();
        ctx.arc(this.currentOp.points[0].x, this.currentOp.points[0].y, this.currentOp.radius, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.beginPath();
        ctx.moveTo(this.currentOp.points[0].x, this.currentOp.points[0].y);
        for (let i = 1; i < this.currentOp.points.length; i++)
          ctx.lineTo(this.currentOp.points[i].x, this.currentOp.points[i].y);
        ctx.stroke();
      }
      ctx.restore();
    }

    // Eraser cursor ring (shows size + position).
    if (this.cursor.inside && (this.tool === 'erasePixels' || this.tool === 'eraseStrokes')) {
      ctx.strokeStyle = this.tool === 'erasePixels' ? '#f87171' : '#818cf8';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(this.cursor.x, this.cursor.y, this.eraserRadius, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  // Rebuild the whole board from the op list (used after a stroke erase).
  private repaint() {
    const ctx = this.ctx;
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

    for (const op of this.strokes) {
      if (op.mode === 'pen') {
        ctx.strokeStyle = '#000';
        ctx.lineWidth = op.weight;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        if (op.points.length === 1) {
          ctx.fillStyle = '#000';
          ctx.beginPath();
          ctx.arc(op.points[0].x, op.points[0].y, op.weight / 2, 0, Math.PI * 2);
          ctx.fill();
        } else {
          ctx.beginPath();
          ctx.moveTo(op.points[0].x, op.points[0].y);
          for (let i = 1; i < op.points.length; i++) ctx.lineTo(op.points[i].x, op.points[i].y);
          ctx.stroke();
        }
      } else if (op.mode === 'erasePixels') {
        if (op.points.length === 1) {
          ctx.clearRect(op.points[0].x - op.radius, op.points[0].y - op.radius, op.radius * 2, op.radius * 2);
        } else {
          ctx.strokeStyle = 'white';
          ctx.lineWidth = op.radius * 2;
          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';
          ctx.globalCompositeOperation = 'destination-out';
          ctx.beginPath();
          ctx.moveTo(op.points[0].x, op.points[0].y);
          for (let i = 1; i < op.points.length; i++) ctx.lineTo(op.points[i].x, op.points[i].y);
          ctx.stroke();
          ctx.globalCompositeOperation = 'source-over';
        }
      }
    }
  }

  // ── Pointer handlers (arrow props so `this` binds + they stay removable) ─────
  private onPointerDown = (e: PointerEvent) => {
    const p = this.getCanvasPos(e);
    this.cursor = { x: p.x, y: p.y, inside: this.inBounds(p) };
    if (!this.inBounds(p)) return;

    this.isDrawing = true;
    this.canvas.setPointerCapture?.(e.pointerId);
    e.preventDefault();

    if (this.tool === 'pen') {
      this.currentOp = { mode: 'pen', weight: PEN_WEIGHT, points: [p] };
      this.ctx.fillStyle = '#000';
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, PEN_WEIGHT / 2, 0, Math.PI * 2);
      this.ctx.fill();
    } else if (this.tool === 'erasePixels') {
      this.currentOp = { mode: 'erasePixels', radius: this.eraserRadius, points: [p] };
      this.ctx.save();
      this.ctx.globalCompositeOperation = 'destination-out';
      this.ctx.fillStyle = 'rgba(0,0,0,1)';
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, this.eraserRadius, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.restore();
    } else if (this.tool === 'eraseStrokes') {
      this.currentOp = null;
      this.eraseStrokesAt(p);
    }
  };

  private onPointerMove = (e: PointerEvent) => {
    const p = this.getCanvasPos(e);
    this.cursor = { x: p.x, y: p.y, inside: this.inBounds(p) };
    if (!this.isDrawing) return;
    e.preventDefault();

    if (this.tool === 'pen' && this.currentOp) {
      this.currentOp.points.push(p);
      const prev = this.currentOp.points[this.currentOp.points.length - 2];
      if (prev) {
        this.ctx.strokeStyle = '#000';
        this.ctx.lineWidth = PEN_WEIGHT;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
        this.ctx.beginPath();
        this.ctx.moveTo(prev.x, prev.y);
        this.ctx.lineTo(p.x, p.y);
        this.ctx.stroke();
      }
    } else if (this.tool === 'erasePixels' && this.currentOp && this.currentOp.mode === 'erasePixels') {
      const prev = this.currentOp.points[this.currentOp.points.length - 1];
      this.currentOp.points.push(p);
      this.ctx.save();
      this.ctx.globalCompositeOperation = 'destination-out';
      this.ctx.strokeStyle = 'rgba(0,0,0,1)';
      this.ctx.lineWidth = this.currentOp.radius * 2;
      this.ctx.lineCap = 'round';
      this.ctx.lineJoin = 'round';
      this.ctx.beginPath();
      this.ctx.moveTo(prev.x, prev.y);
      this.ctx.lineTo(p.x, p.y);
      this.ctx.stroke();
      this.ctx.restore();
    } else if (this.tool === 'eraseStrokes') {
      this.eraseStrokesAt(p);
    }
  };

  private onPointerUp = () => {
    if (this.isDrawing && this.currentOp && this.currentOp.points.length > 0) {
      this.strokes.push(this.currentOp);
    }
    this.currentOp = null;
    this.isDrawing = false;
    this.repaint();
  };

  private onPointerLeave = () => {
    this.cursor.inside = false;
  };

  // Remove any pen stroke that passes within the eraser radius of p.
  private eraseStrokesAt(p: Point) {
    const before = this.strokes.length;
    this.strokes = this.strokes.filter((op) => {
      if (op.mode !== 'pen') return true;
      const hitR = this.eraserRadius + (op.weight || PEN_WEIGHT) / 2;
      const hit = op.points.some((pt) => Math.hypot(pt.x - p.x, pt.y - p.y) <= hitR);
      return !hit;
    });
    if (this.strokes.length !== before) this.repaint();
  }

  // ── Public toolbar API ───────────────────────────────────────────────────────
  setTool(t: Tool) {
    this.tool = t;
  }

  setEraserRadius(v: number) {
    this.eraserRadius = parseInt(String(v), 10) || 1;
  }

  clear() {
    this.strokes = [];
    this.currentOp = null;
    this.isDrawing = false;
    this.ctx.fillStyle = 'white';
    this.ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
  }

  isEmpty() {
    return this.strokes.length === 0;
  }

  /** Snapshot the board as a PNG blob for OCR. */
  captureBlob(): Promise<Blob | null> {
    return new Promise((resolve) => this.canvas.toBlob(resolve, 'image/png'));
  }
}
