import { exportToCanvas } from '@excalidraw/excalidraw';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';
import type { Op } from '../types';

// Excalidraw-backed board facade — the single drawing engine (the native
// BoardEngine is retired). Excalidraw owns an infinite canvas that fills its
// container (so the board can truly go full-screen), and brings its own toolbar.
//
// The rest of the app only needs three things from a board, so this facade exposes
// the SAME shape the 选区屏 (SelectScreen) already consumed from the old engine —
// `.canvas` / `.width` / `.height` / `.strokes` — by rasterising the scene to a
// plain <canvas>. That keeps the OCR crop/lasso pipeline (board/selection.ts)
// working unchanged: it just crops a region out of this snapshot canvas.
export class ExcalidrawBoard {
  api: ExcalidrawImperativeAPI | null = null;

  // Rasterised snapshot of the scene, refreshed by snapshot() before we enter the
  // 选区屏. SelectScreen reads these exactly as it read the old engine's canvas.
  canvas: HTMLCanvasElement = document.createElement('canvas');
  width = 0;
  height = 0;
  // Always empty — Excalidraw owns the stroke model. Kept so SelectScreen's
  // inkBounds(board.strokes) stays a harmless no-op (→ default = whole snapshot).
  strokes: Op[] = [];

  setApi(api: ExcalidrawImperativeAPI | null) {
    this.api = api;
  }

  isEmpty(): boolean {
    return (this.api?.getSceneElements().length ?? 0) === 0;
  }

  /** Wipe the scene — called when a new problem loads. */
  clear() {
    this.api?.updateScene({ elements: [] });
  }

  /** Rasterise the current scene into `this.canvas`. false when nothing is drawn. */
  async snapshot(): Promise<boolean> {
    const api = this.api;
    if (!api) return false;
    const elements = api.getSceneElements();
    if (!elements.length) return false;
    const canvas = await exportToCanvas({
      elements,
      appState: { ...api.getAppState(), exportBackground: true, viewBackgroundColor: '#ffffff' },
      files: api.getFiles(),
      exportPadding: 16, // a little breathing room so edge strokes aren't clipped
    });
    this.canvas = canvas;
    this.width = canvas.width;
    this.height = canvas.height;
    return true;
  }

  /** Snapshot the scene as a PNG blob (white-backed) for OCR / upload. */
  async captureBlob(): Promise<Blob | null> {
    if (!(await this.snapshot())) return null;
    return new Promise((resolve) => this.canvas.toBlob(resolve, 'image/png'));
  }
}
