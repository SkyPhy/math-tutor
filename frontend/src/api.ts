// Typed FastAPI client. Endpoints + payloads mirror the legacy page so the backend
// (the correctness core) needs no changes.
import { API_BASE } from './config';
import type { AssistAnalysis, ChatMsg, ManimRenderResp, Problem, RecognizeModel, WorkDraft } from './types';

async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(API_BASE + path);
  if (!r.ok) throw new Error(`GET ${path} → ${r.status}`);
  return (await r.json()) as T;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(API_BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return (await r.json()) as T;
}

// ── /practice/next ───────────────────────────────────────────────────────────
export interface PracticeParams {
  excludeId?: string | null;
  generate?: boolean;
  source?: string | null;
  focusLogic?: string | null;
  difficulty?: number | null;
  adaptive?: string | null;
  tag?: string | null;
}

export async function fetchProblem(p: PracticeParams = {}): Promise<Problem> {
  const url = new URL(API_BASE + '/practice/next');
  if (p.excludeId) url.searchParams.set('exclude_id', p.excludeId);
  if (p.generate) url.searchParams.set('generate', '1');
  if (p.focusLogic) url.searchParams.set('focus_logic', p.focusLogic);
  if (p.difficulty != null) url.searchParams.set('difficulty', String(p.difficulty));
  if (p.adaptive) url.searchParams.set('adaptive', p.adaptive);
  if (p.tag) url.searchParams.set('tag', p.tag);
  // 出题来源 picker: bank = default (no param); xueke routes to the 学科网 API.
  if (!p.generate && p.source && p.source !== 'bank') url.searchParams.set('source', p.source);
  const r = await fetch(url.toString());
  if (!r.ok) throw new Error(`practice/next → ${r.status}`);
  return (await r.json()) as Problem;
}

// ── /recognize (OCR) ─────────────────────────────────────────────────────────
export interface RecognizeResult {
  text?: string;
  status?: string;
}

export async function recognize(blob: Blob, method = 'nex'): Promise<RecognizeResult> {
  const fd = new FormData();
  fd.append('file', blob, 'board.png');
  const url = new URL(API_BASE + '/recognize');
  if (method) url.searchParams.set('method', method);
  const r = await fetch(url.toString(), { method: 'POST', body: fd });
  return (await r.json()) as RecognizeResult;
}

// GET /recognize/models — added in v0.4.1a; callers tolerate a 404 by falling
// back to the built-in list.
export async function recognizeModels(): Promise<{ models: RecognizeModel[]; default?: string }> {
  return getJSON('/recognize/models');
}

// ── /tags/catalogue ──────────────────────────────────────────────────────────
export interface TagsCatalogue {
  catalogue?: {
    logic?: Record<string, Array<{ name: string }>>;
    knowledge?: Record<string, Array<{ name: string }>>;
  };
}

export async function tagsCatalogue(): Promise<TagsCatalogue> {
  return getJSON('/tags/catalogue');
}

// ── /claude/chat · /analyze · /verify ────────────────────────────────────────
export interface ChatReq {
  message: string;
  expression?: string | null;
  model?: string | null;
  session_id?: string | null;
  history?: Array<{ role: string; content: string }>;
  allow_special?: string[];   // special symbols / regex / escapes the chat may use
}
export interface ChatResp {
  available?: boolean;
  reply?: string;
  provider?: string;
  reason?: string;
}
export async function claudeChat(req: ChatReq): Promise<ChatResp> {
  return postJSON('/claude/chat', req);
}

export async function analyze(expression: string, action = 'analyze', model?: string | null) {
  return postJSON<Record<string, unknown>>('/analyze', { expression, action, model });
}

// Typed view of the /analyze response we actually consume on the 答疑屏 (⑤).
export interface AnalyzeResp {
  session_id?: string;
  original?: string;
  latex?: string;
  socratic?: { messages?: Array<{ role: string; content: string }> };
  steps?: string[];
  ai_provider?: string;
  [k: string]: unknown;
}

// POST /analyze for the 答疑屏「解析此题」button: a Socratic level-0 read of the
// problem (never the final answer). Grounded on the problem text.
export async function analyzeProblem(expression: string, model?: string | null): Promise<AnalyzeResp> {
  return postJSON<AnalyzeResp>('/analyze', { expression, action: 'analyze', model });
}

// Pull the tutor-facing text out of an /analyze response (join the Socratic
// messages, falling back to the legacy `steps` array).
export function analyzeText(res: AnalyzeResp): string {
  const msgs = res.socratic?.messages;
  if (Array.isArray(msgs) && msgs.length) {
    return msgs
      .filter((m) => m.role === 'tutor' || m.role === 'system')
      .map((m) => m.content)
      .join('\n\n')
      .trim();
  }
  if (Array.isArray(res.steps) && res.steps.length) return res.steps.join('\n\n').trim();
  return '';
}

export interface VerifyReq {
  expression: string;
  answer?: string;
  session_id?: string;
  question_id?: string;
  model?: string | null;
}
export interface VerifyResp {
  answer_checked?: boolean;
  answer_correct?: boolean | null;
  judged_by?: string;
  judge_reason?: string;
  ground_truth?: string | number | null;
  agreement?: number;
  votes_label?: string;
  [k: string]: unknown;
}
export async function verify(body: VerifyReq) {
  return postJSON<VerifyResp>('/verify', body);
}

// ── /work/* (校对屏 personal draft library, v0.4.2a) ──────────────────────────
export interface WorkSaveReq {
  session_id?: string;
  question_id?: string | null;
  filename?: string | null;
  content_md: string;
  render_mode?: string | null;
  status: 'tmp' | 'final';
  draft_id?: string | null;
}

// POST /work/save — 存草稿 (status=tmp) or 提交 (status=final). Returns the stored
// draft so the caller can keep its id and 续作 (reopen + continue) it later.
export async function workSave(body: WorkSaveReq): Promise<WorkDraft> {
  return postJSON('/work/save', body);
}

// GET /work?session=&question_id= — the caller's drafts (for the 「我的草稿」list).
export async function workList(session?: string, questionId?: string | null): Promise<{ drafts: WorkDraft[] }> {
  const url = new URL(API_BASE + '/work');
  if (session) url.searchParams.set('session', session);
  if (questionId) url.searchParams.set('question_id', questionId);
  const r = await fetch(url.toString());
  if (!r.ok) throw new Error(`GET /work → ${r.status}`);
  return (await r.json()) as { drafts: WorkDraft[] };
}

// ── /assistant/* (④ 助手屏 line-by-line analysis, v0.4.3a) ────────────────────
export interface AssistAnalyzeReq {
  session_id?: string;
  question_id?: string | null;
  problem?: string;
  student_work_md: string;
  render_mode?: string | null;
  model?: string | null;
}

// POST /assistant/analyze — align the student's corrected work with AI notes line
// by line (blank note = that step is fine). Always resolves (200) with a provider;
// `provider: 'template'` means Claude was unavailable and rows came back un-annotated.
export async function assistantAnalyze(body: AssistAnalyzeReq): Promise<AssistAnalysis> {
  return postJSON('/assistant/analyze', body);
}

export interface AssistAskReq {
  session_id?: string;
  message: string;
  question_id?: string | null;
  problem?: string;
  model?: string | null;
  history?: ChatMsg[];
  focus?: { idx: number; content: string; analysis: string } | null;
  render_mode?: string | null;
  allow_special?: string[];
}
export interface AssistAskResp {
  reply?: string | null;
  provider?: string;
  available?: boolean;
  reason?: string;
}

// POST /assistant/ask — per-line follow-up, grounded in the clicked line (`focus`).
export async function assistantAsk(body: AssistAskReq): Promise<AssistAskResp> {
  return postJSON('/assistant/ask', body);
}

// ── /manim/render (④ 助手屏 <manim> blocks, v0.4.5b) ──────────────────────────
export interface ManimRenderReq {
  expression?: string;
  spec?: string;             // the natural-language <manim> note
  manim_code?: string;
  session_id?: string;
  model?: string | null;
}

// POST /manim/render — real MP4 when the server has Manim CE, else status != 'ok'
// with a browser storyboard to animate in-page. Always resolves (never errors out).
export async function manimRender(body: ManimRenderReq): Promise<ManimRenderResp> {
  return postJSON('/manim/render', body);
}
