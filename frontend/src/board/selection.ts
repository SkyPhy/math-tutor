// Selection geometry + region export for the 选区屏 (select screen).
//
// The student frames part of the whiteboard; we send ONLY that region to OCR.
// Rather than re-deriving the picture from the op list (which would lose the
// erase ops), we copy pixels straight from the already-rendered board canvas —
// faithful to the exact ink, and correct around erased areas. A rectangle is a
// plain crop; a lasso clips to its polygon. Pure functions so they're easy to
// reason about and reuse from the screen component.
import type { Op, Point } from '../types';

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Flip a rect drawn right-to-left / bottom-to-top into positive w/h. */
export function normRect(r: Rect): Rect {
  return {
    x: Math.min(r.x, r.x + r.w),
    y: Math.min(r.y, r.y + r.h),
    w: Math.abs(r.w),
    h: Math.abs(r.h),
  };
}

/** Clamp a (normalised) rect to the canvas, keeping at least 1px of area. */
export function clampRect(r: Rect, maxW: number, maxH: number): Rect {
  const n = normRect(r);
  const x = Math.max(0, Math.min(n.x, maxW - 1));
  const y = Math.max(0, Math.min(n.y, maxH - 1));
  const w = Math.max(1, Math.min(n.w, maxW - x));
  const h = Math.max(1, Math.min(n.h, maxH - y));
  return { x, y, w, h };
}

/** Bounding box of all pen ink (erase ops ignored). null when nothing drawn. */
export function inkBounds(ops: Op[]): Rect | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let found = false;
  for (const op of ops) {
    if (op.mode !== 'pen') continue;
    for (const p of op.points) {
      found = true;
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.x > maxX) maxX = p.x;
      if (p.y > maxY) maxY = p.y;
    }
  }
  if (!found) return null;
  return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
}

/** Axis-aligned bounds of a polygon, or null if it has no extent. */
export function polyBounds(points: Point[]): Rect | null {
  if (points.length < 2) return null;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const p of points) {
    if (p.x < minX) minX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.x > maxX) maxX = p.x;
    if (p.y > maxY) maxY = p.y;
  }
  return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
}

function toBlob(off: HTMLCanvasElement): Promise<Blob | null> {
  return new Promise((resolve) => off.toBlob(resolve, 'image/png'));
}

/** Crop `src` to `rect` onto a white-backed PNG (the framed region only). */
export function exportRect(src: HTMLCanvasElement, rect: Rect): Promise<Blob | null> {
  const r = clampRect(rect, src.width, src.height);
  const w = Math.max(1, Math.round(r.w));
  const h = Math.max(1, Math.round(r.h));
  const off = document.createElement('canvas');
  off.width = w;
  off.height = h;
  const ctx = off.getContext('2d')!;
  ctx.fillStyle = 'white';
  ctx.fillRect(0, 0, w, h);
  ctx.drawImage(src, Math.round(r.x), Math.round(r.y), w, h, 0, 0, w, h);
  return toBlob(off);
}

/** Export only the lasso polygon's interior (cropped to its bbox) as PNG. */
export function exportLasso(src: HTMLCanvasElement, points: Point[]): Promise<Blob | null> {
  const bb = polyBounds(points);
  if (!bb || points.length < 3) return Promise.resolve(null);
  const r = clampRect(bb, src.width, src.height);
  const w = Math.max(1, Math.round(r.w));
  const h = Math.max(1, Math.round(r.h));
  const off = document.createElement('canvas');
  off.width = w;
  off.height = h;
  const ctx = off.getContext('2d')!;
  ctx.fillStyle = 'white';
  ctx.fillRect(0, 0, w, h);
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(points[0].x - r.x, points[0].y - r.y);
  for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x - r.x, points[i].y - r.y);
  ctx.closePath();
  ctx.clip();
  ctx.drawImage(src, Math.round(r.x), Math.round(r.y), w, h, 0, 0, w, h);
  ctx.restore();
  return toBlob(off);
}
