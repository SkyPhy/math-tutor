// App-wide store: the screen router (with back-stack), the persistent whiteboard
// engine, and the current problem. Kept deliberately small — a React context over
// useState/useRef rather than a heavyweight state library.
import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { ExcalidrawBoard } from './board/ExcalidrawBoard';
import { SCREEN_DEFS } from './config';
import { fetchModels } from './api';
import type { LLMModel, Problem, RenderMode, ScreenName, WorkFlow } from './types';

interface StoreValue {
  // ── routing ──
  screen: ScreenName;
  workFlow: WorkFlow;
  navTo: (name: ScreenName) => void;
  navBack: () => void;
  navHome: () => void;
  startWorkFlow: (flow: Exclude<WorkFlow, null>) => void;

  // ── whiteboard (Excalidraw) ──
  board: ExcalidrawBoard;
  captureBlob: () => Promise<Blob | null>;

  // ── problem ──
  problem: Problem | null;
  setProblem: (p: Problem | null) => void;

  // ── OCR handoff (select → check) ──
  ocrText: string;
  setOcrText: (t: string) => void;

  // ── corrected work handoff (check → assistant / verify) ──
  studentWork: string;
  setStudentWork: (t: string) => void;
  // render mode the work was saved with (check → assistant reading hint)
  renderMode: RenderMode;
  setRenderMode: (m: RenderMode) => void;

  // ── AI model selection (student picks within the admin-controlled pool) ──
  // `models` is the student-selectable pool from GET /models. `model` is the
  // student's current choice. `forcedModel` is set when the admin forced a model
  // (the picker is then locked to it — students can't override an admin's force).
  models: LLMModel[];
  model: string;
  setModel: (id: string) => void;
  forcedModel: string | null;
  refreshModels: () => void;

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
  const [problem, setProblem] = useState<Problem | null>(null);
  const [ocrText, setOcrText] = useState('');
  const [studentWork, setStudentWork] = useState('');
  const [renderMode, setRenderMode] = useState<RenderMode>('3');

  // AI model pool + current choice. Loaded from GET /models; a forced model (set
  // by an admin) overrides the choice and locks the picker.
  const [models, setModels] = useState<LLMModel[]>([]);
  const [model, setModelState] = useState<string>('');
  const [forcedModel, setForcedModel] = useState<string | null>(null);

  // Pull the student pool (usable ∧ admin-enabled) + default + any forced model.
  // A forced model wins over the current choice; otherwise keep a valid choice,
  // falling back to the backend default when the current one left the pool.
  const refreshModels = () => {
    fetchModels()
      .then((res) => {
        const pool = res.models || [];
        setModels(pool);
        setForcedModel(res.forced_model ?? null);
        setModelState((cur) => {
          if (res.forced_model) return res.forced_model;
          if (cur && pool.some((m) => m.id === cur)) return cur;
          return res.default_model || (pool[0]?.id ?? '');
        });
      })
      .catch(() => {
        /* leave defaults; AI calls still work with the backend's own default */
      });
  };
  useEffect(() => {
    refreshModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // A forced model always wins; otherwise honour the student's own choice.
  const setModel = (id: string) => {
    if (forcedModel) return; // locked by admin
    setModelState(id);
  };

  const navStack = useRef<ScreenName[]>([]);
  const [board] = useState(() => new ExcalidrawBoard());
  const sessionId = useMemo(makeSessionId, []);

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

  // 提交 / AI 助手 both go through 选区 → 校对. Rasterise the Excalidraw scene first
  // (the 选区屏 crops a region out of that snapshot for OCR); refuse on a blank board.
  const startWorkFlow = async (flow: Exclude<WorkFlow, null>) => {
    const drawn = await board.snapshot();
    if (!drawn) {
      window.alert('请先在白板上作答，再提交。');
      return;
    }
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
    captureBlob,
    problem,
    setProblem,
    ocrText,
    setOcrText,
    studentWork,
    setStudentWork,
    renderMode,
    setRenderMode,
    models,
    model,
    setModel,
    forcedModel,
    refreshModels,
    sessionId,
  };

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): StoreValue {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useStore must be used inside <StoreProvider>');
  return ctx;
}
