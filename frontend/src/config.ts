// Config-driven UI: screens, sources, and problem actions are data, not markup —
// so the guided flow stays changeable in one place (honouring the project rule:
// "dynamic / config-driven, not hardcoded"). Mirrors the legacy SCREEN_DEFS /
// SOURCES / PROBLEM_ACTIONS tables.
import type { ScreenName, WorkFlow } from './types';

// Backend base URL. CORS is open on the FastAPI side, so a direct call works;
// override with VITE_API_BASE for other hosts.
export const API_BASE: string = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export interface ScreenDef {
  name: ScreenName;
  title: string;
  sub?: string;
}

export const SCREEN_DEFS: Record<ScreenName, ScreenDef> = {
  problem: { name: 'problem', title: 'AI-based math tutor' },
  select: { name: 'select', title: '选择要提交的内容', sub: '框选要发送给 OCR 的笔画' },
  check: { name: 'check', title: 'AI math tutor', sub: '核对识别结果后再提交' },
  assistant: { name: 'assistant', title: 'AI assistant', sub: '逐行看看你的解法' },
  ask: { name: 'ask', title: 'Q&A', sub: '就这道题随便问' },
};

export interface SourceDef {
  value: 'ai' | 'xueke' | 'bank';
  label: string;
  generate: boolean;
}

export const SOURCES: SourceDef[] = [
  { value: 'ai', label: '1 · AI 生成', generate: true },
  { value: 'xueke', label: '2 · 学科网 API', generate: false },
  { value: 'bank', label: '3 · 后台题库', generate: false },
];

// Bottom action row on the problem screen. `go` is the routing intent:
//   'flow' → start a work flow (submit / assist) which enters the select screen
//   'ask'  → jump straight to the Q&A screen (no whiteboard / OCR)
export interface ActionDef {
  label: string;
  cls: string;
  confirm?: string;
  flow?: Exclude<WorkFlow, null>;
  go: 'flow' | 'ask';
}

export const PROBLEM_ACTIONS: ActionDef[] = [
  {
    label: '📤 提交',
    cls: 'btn-primary',
    confirm: '确认已完成作答并提交？（未完成也可提交）',
    flow: 'submit',
    go: 'flow',
  },
  { label: '🙋 提问 / 不会做', cls: 'btn-secondary', go: 'ask' },
  { label: '🤖 AI 助手（求助＝同时提交）', cls: 'btn-secondary', flow: 'assist', go: 'flow' },
];

// Open-ended difficulty ladder (1 = 认识数字 … 10 = 大学通识课, >10 = 竞赛/研究级).
// Ported from the legacy initPracticeControls() DIFF table.
export const DIFFICULTY_LADDER: Array<{ value: number; label: string }> = [
  { value: 1, label: '1 · 认识数字' },
  { value: 2, label: '2 · 低年级·20以内' },
  { value: 3, label: '3 · 低年级·百以内' },
  { value: 4, label: '4 · 中年级·两步' },
  { value: 5, label: '5 · 中年级·多步' },
  { value: 6, label: '6 · 高年级·分数比例' },
  { value: 7, label: '7 · 高年级·多策略' },
  { value: 8, label: '8 · 初中过渡' },
  { value: 9, label: '9 · 高中/竞赛初步' },
  { value: 10, label: '10 · 大学通识课' },
  { value: 12, label: '11+ · 竞赛/研究级' },
];
