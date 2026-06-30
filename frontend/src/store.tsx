// App-wide store: the screen router (with back-stack), the persistent whiteboard
// engine, and the current problem. Kept deliberately small — a React context over
// useState/useRef rather than a heavyweight state library.
import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { BoardEngine } from './board/BoardEngine';
import { SCREEN_DEFS } from './config';
import type { BoardMode, Problem, ScreenName, WorkFlow } from './types';

interface StoreValue {
  // ── routing ──
  screen: ScreenName;
  workFlow: WorkFlow;
  navTo: (name: ScreenName) => void;
  navBack: () => void;
  navHome: () => void;
  startWorkFlow: (flow: Exclude<WorkFlow, null>) => void;

  // ── whiteboard ──
  board: BoardEngine;
  boardMode: BoardMode;
  setBoardMode: (m: BoardMode) => void;
  captureBlob: () => Promise<Blob | null>;

  // ── problem ──
  problem: Problem | null;
  setProblem: (p: Problem | null) => void;

  // ── OCR handoff (select → check) ──
  ocrText: string;
  setOcrText: (t: string) => void;

  sessionId: string;
}

const StoreContext = createContext<StoreValue | null>(null);

function makeSessionId(): string {
  try {
    if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  } catch {
    /* fall through */
  }
  return 'sess-' + Math.abs(Date.now() ^ (Math.random() * 1e9)).toString(36);
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [screen, setScreen] = useState<ScreenName>('problem');
  const [workFlow, setWorkFlow] = useState<WorkFlow>(null);
  const [boardMode, setBoardMode] = useState<BoardMode>('original');
  const [problem, setProblem] = useState<Problem | null>(null);
  const [ocrText, setOcrText] = useState('');

  const navStack = useRef<ScreenName[]>([]);
  const [board] = useState(() => new BoardEngine());
  const sessionId = useMemo(makeSessionId, []);

  // The engine lives for the app's lifetime; tear it down only on full unmount.
  useEffect(() => () => board.destroy(), [board]);

  const showScreen = (name: ScreenName) => {
    if (!SCREEN_DEFS[name]) return;
    setScreen(name);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const navTo = (name: ScreenName) => {
    setScreen((cur) => {
      if (name !== cur) navStack.current.push(cur);
      return name;
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const navBack = () => {
    const prev = navStack.current.pop() || 'problem';
    showScreen(prev);
  };

  const navHome = () => {
    navStack.current.length = 0;
    setWorkFlow(null);
    showScreen('problem');
  };

  const startWorkFlow = (flow: Exclude<WorkFlow, null>) => {
    setWorkFlow(flow);
    navTo('select');
  };

  const captureBlob = () => board.captureBlob();

  const value: StoreValue = {
    screen,
    workFlow,
    navTo,
    navBack,
    navHome,
    startWorkFlow,
    board,
    boardMode,
    setBoardMode,
    captureBlob,
    problem,
    setProblem,
    ocrText,
    setOcrText,
    sessionId,
  };

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): StoreValue {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useStore must be used inside <StoreProvider>');
  return ctx;
}
