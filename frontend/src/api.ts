// Typed FastAPI client. Endpoints + payloads mirror the legacy page so the backend
// (the correctness core) needs no changes.
import { API_BASE } from './config';
import type { Problem, RecognizeModel } from './types';

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

export interface VerifyReq {
  expression: string;
  answer?: string;
  session_id?: string;
  question_id?: string;
  model?: string | null;
}
export async function verify(body: VerifyReq) {
  return postJSON<Record<string, unknown>>('/verify', body);
}
