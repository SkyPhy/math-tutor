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

// ── AI models (multi-provider: Claude / DeepSeek / GPT) ───────────────────────
// A model a STUDENT may pick, from GET /models. The pool itself is decided by the
// admin (usable ∧ enabled) — the student can only choose within it.
export interface LLMModel {
  id: string;
  label: string;
  provider: string;        // 'claude' | 'deepseek' | 'openai'
  provider_label: string;  // 'Claude' | 'DeepSeek' | 'GPT'
}

export interface ModelsResp {
  available: boolean;
  default_model: string;
  forced_model: string | null;   // when set, the admin forced this model → lock the picker
  models: LLMModel[];
  status?: unknown;
}

// Admin-only view (GET /admin/models): the FULL catalogue with usable/enabled state.
export interface AdminModel extends LLMModel {
  usable: boolean;
  enabled: boolean;
}
export interface AdminModelsResp {
  models: AdminModel[];
  forced_model: string | null;
}

export interface AuthUser {
  id: number;
  username: string;
  email?: string | null;
  role: string;            // 'admin' | 'student'
  created_at?: string;
}

// ── Workspace (校对屏 personal draft library) ─────────────────────────────────
// Render mode for the recognised text: 1 full md+latex render / 2 source-style /
// 3 plain text (default).
export type RenderMode = '1' | '2' | '3';

export interface WorkDraft {
  id: string;
  owner: string;
  question_id: string | null;
  filename: string | null;
  content_md: string;
  render_mode: string | null;
  status: 'tmp' | 'final';
  created_at: string;
  updated_at: string;
}

// ── AI assistant (④ 助手屏, v0.4.3a) ──────────────────────────────────────────
// One row of the two-column aligned analysis: the student's line on the left,
// the AI note on the right. `analysis` is empty (and `has_issue` false) when the
// step is fine — the right column stays blank on correct rows.
export interface AssistLine {
  idx: number;
  content: string;
  analysis: string;
  has_issue: boolean;
  manim?: string | null;
}

export interface AssistAnalysis {
  lines: AssistLine[];
  summary: string;
  provider: string;
  reason?: string;
}

// A single chat turn for the shared chat control (ChatBox).
export interface ChatMsg {
  role: 'user' | 'assistant';
  content: string;
}

// ── Manim render (v0.4.5b) ────────────────────────────────────────────────────
// One frame of the browser storyboard fallback (in-page animation when there is no
// real MP4). Mirrors the backend ManimAnimator storyboard shape.
export interface ManimFrame {
  index: number;
  title?: string;
  latex?: string;
  caption?: string;
}

export interface ManimRenderResp {
  status: 'ok' | 'unavailable' | 'error';
  video_url?: string;      // present when status === 'ok' (path under API_BASE)
  manim_code?: string;
  provider?: string;       // 'claude' | 'template' | 'provided'
  scene?: string;
  reason?: string;
  storyboard?: ManimFrame[];
  expression?: string;
}
