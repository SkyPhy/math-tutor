// Shared types for the tutor frontend.

export type ScreenName = 'problem' | 'select' | 'check' | 'assistant' | 'ask';
export type WorkFlow = 'submit' | 'assist' | null;

export interface ProblemTag {
  tag: string;
  dimension?: string;
  primary?: boolean;
}

export interface Problem {
  id: string;
  title: string;
  statement: string;
  latex?: string;
  topic?: string;
  difficulty?: number | string;
  tags?: ProblemTag[];
  source?: string;       // 'ai' | 'bank' | 'xueke' | …
  from_source?: string;
  generated?: boolean;
  disclaimer?: string | null;
}

// ── Whiteboard ──────────────────────────────────────────────────────────────
export interface Point {
  x: number;
  y: number;
}

// `strokes` is an ordered op list so the board can be rebuilt at any time
// (needed by the stroke eraser). Each op is one of:
export type Op =
  | { mode: 'pen'; weight: number; points: Point[] }
  | { mode: 'erasePixels'; radius: number; points: Point[] };

export type Tool = 'pen' | 'erasePixels' | 'eraseStrokes';
export type BoardMode = 'original' | 'excalidraw';

export interface RecognizeModel {
  id: string;
  label: string;
}
