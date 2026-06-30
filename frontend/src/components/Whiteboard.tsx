import { useEffect, useRef, useState } from 'react';
import { useStore } from '../store';
import type { Tool } from '../types';

// The native whiteboard. The <canvas> element is owned by the long-lived
// BoardEngine (so strokes survive screen changes); this component just mounts it
// into the DOM and renders the toolbar + engine selector + fullscreen control.
export function Whiteboard() {
  const { board, boardMode, setBoardMode } = useStore();
  const hostRef = useRef<HTMLDivElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [tool, setToolState] = useState<Tool>(board.tool);
  const [eraser, setEraser] = useState(board.eraserRadius);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const host = hostRef.current;
    if (host) board.mount(host);
    return () => board.detach();
  }, [board]);

  useEffect(() => {
    const onFs = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', onFs);
    return () => document.removeEventListener('fullscreenchange', onFs);
  }, []);

  const pick = (t: Tool) => {
    board.setTool(t);
    setToolState(t);
  };

  const toggleFullscreen = () => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    if (!document.fullscreenElement) {
      wrap.requestFullscreen?.().catch(() => alert('Fullscreen is not available in this browser/context.'));
    } else {
      document.exitFullscreen?.();
    }
  };

  return (
    <div className="container">
      <div id="canvas-wrapper" ref={wrapRef}>
        <div className="board-mode-row" id="board-mode-row">
          <label className="board-mode-label" htmlFor="boardModeSelect">
            Whiteboard engine
          </label>
          <select
            id="boardModeSelect"
            className="board-mode-select"
            value={boardMode}
            onChange={(e) => setBoardMode(e.target.value === 'excalidraw' ? 'excalidraw' : 'original')}
          >
            <option value="original">✏️ Original Whiteboard</option>
            <option value="excalidraw" disabled>
              🎨 Excalidraw（即将回归）
            </option>
          </select>
          <button
            id="fullscreen-btn"
            className="board-fullscreen-btn"
            onClick={toggleFullscreen}
            title="Toggle fullscreen whiteboard"
          >
            {isFullscreen ? '🗗 Exit Fullscreen' : '⛶ Fullscreen'}
          </button>
        </div>

        <div id="canvas-container" ref={hostRef} />

        <div className="board-tools">
          <span id="native-tools" style={{ display: 'contents' }}>
            <button className={`tool-btn ${tool === 'pen' ? 'active' : ''}`} onClick={() => pick('pen')}>
              ✏️ Pen
            </button>
            <button
              className={`tool-btn ${tool === 'erasePixels' ? 'active' : ''}`}
              onClick={() => pick('erasePixels')}
              title="Erase a circular area around the cursor"
            >
              🧽 Erase Area
            </button>
            <button
              className={`tool-btn ${tool === 'eraseStrokes' ? 'active' : ''}`}
              onClick={() => pick('eraseStrokes')}
              title="Erase whole strokes the cursor touches"
            >
              ✂️ Erase Stroke
            </button>
            <label className="eraser-size">
              Size
              <input
                type="range"
                min={5}
                max={60}
                value={eraser}
                onInput={(e) => {
                  const v = parseInt((e.target as HTMLInputElement).value, 10);
                  board.setEraserRadius(v);
                  setEraser(v);
                }}
                onChange={(e) => {
                  const v = parseInt(e.target.value, 10);
                  board.setEraserRadius(v);
                  setEraser(v);
                }}
              />
              <span>{eraser}</span>
            </label>
            <button className="btn-secondary" onClick={() => board.clear()}>
              Clear Board
            </button>
          </span>
        </div>
      </div>
    </div>
  );
}
