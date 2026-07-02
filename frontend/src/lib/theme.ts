// Theme system: a dark/light colour scheme + a user-selectable accent pair, both
// persisted to localStorage and applied to <html> (`data-theme` + inline `--accent-*`
// vars that styles.css reads). An inline script in index.html applies the saved choice
// before first paint to avoid a flash; this module is the source of truth the UI uses.
export type ThemeMode = 'dark' | 'light';

export interface Accent {
  name: string;
  c1: string; // primary gradient stop (→ --accent-blue)
  c2: string; // secondary gradient stop (→ --accent-purple)
}

// Preset accent pairs (the title/button gradients). The first is the default (海蓝,
// matching the original hard-coded look).
export const ACCENTS: Accent[] = [
  { name: '海蓝', c1: '#38bdf8', c2: '#818cf8' },
  { name: '紫罗兰', c1: '#a78bfa', c2: '#c084fc' },
  { name: '翡翠', c1: '#34d399', c2: '#22d3ee' },
  { name: '玫瑰', c1: '#fb7185', c2: '#f472b6' },
  { name: '琥珀', c1: '#f59e0b', c2: '#fb923c' },
];

const LS_MODE = 'mt-theme-mode';
const LS_C1 = 'mt-accent-c1';
const LS_C2 = 'mt-accent-c2';

export const DEFAULT_MODE: ThemeMode = 'dark';

export function loadMode(): ThemeMode {
  const v = localStorage.getItem(LS_MODE);
  return v === 'light' || v === 'dark' ? v : DEFAULT_MODE;
}

export function loadAccent(): Accent {
  const c1 = localStorage.getItem(LS_C1);
  const c2 = localStorage.getItem(LS_C2);
  if (c1 && c2) {
    const preset = ACCENTS.find((a) => a.c1 === c1 && a.c2 === c2);
    return preset || { name: 'custom', c1, c2 };
  }
  return ACCENTS[0];
}

export function applyMode(mode: ThemeMode): void {
  document.documentElement.setAttribute('data-theme', mode);
}

export function applyAccent(a: Accent): void {
  const root = document.documentElement;
  root.style.setProperty('--accent-blue', a.c1);
  root.style.setProperty('--accent-purple', a.c2);
}

export function saveMode(mode: ThemeMode): void {
  localStorage.setItem(LS_MODE, mode);
  applyMode(mode);
}

export function saveAccent(a: Accent): void {
  localStorage.setItem(LS_C1, a.c1);
  localStorage.setItem(LS_C2, a.c2);
  applyAccent(a);
}

// Lighten a #rrggbb toward white by `amt` (0..1) — used to derive a second gradient
// stop from the single colour a user picks in the custom colour input.
export function lighten(hex: string, amt = 0.28): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  const chan = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  const hexOf = (c: number) => Math.round(c + (255 - c) * amt).toString(16).padStart(2, '0');
  return `#${chan.map(hexOf).join('')}`;
}
