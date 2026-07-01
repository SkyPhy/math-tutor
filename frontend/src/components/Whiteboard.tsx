import { useEffect, useRef, useState } from 'react';
import { Excalidraw } from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';
import { useStore } from '../store';

// The whiteboard — now Excalidraw only (the native 800×600 canvas engine is
// retired). Excalidraw is an infinite canvas with its own toolbar that fills its
// container, so ⛶ fullscreen genuinely covers the screen. We hand its imperative
// API to the board facade (store) so 提交/AI 助手 can rasterise the scene for OCR.
export function Whiteboard() {
  const { board } = useStore();
  const wrapRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const onFs = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', onFs);
    return () => document.removeEventListener('fullscreenchange', onFs);
  }, []);

  // Release the API reference if this board ever unmounts.
  useEffect(() => () => board.setApi(null), [board]);

  const toggleFullscreen = () => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    if (!document.fullscreenElement) {
      wrap.requestFullscreen?.().catch(() => alert('全屏在当前浏览器 / 环境不可用。'));
    } else {
      document.exitFullscreen?.();
    }
  };

  return (
    <div className="container">
      <div id="canvas-wrapper" ref={wrapRef}>
        <div className="board-mode-row" id="board-mode-row">
          <span className="board-mode-label">白板 · Excalidraw</span>
          <button
            id="fullscreen-btn"
            className="board-fullscreen-btn"
            onClick={toggleFullscreen}
            title="切换全屏白板"
          >
            {isFullscreen ? '🗗 退出全屏' : '⛶ 全屏'}
          </button>
        </div>

        <div id="excalidraw-host" className="excalidraw-host">
          <Excalidraw
            excalidrawAPI={(api) => board.setApi(api)}
            langCode="zh-CN"
            initialData={{ appState: { viewBackgroundColor: '#ffffff' } }}
          />
        </div>
      </div>
    </div>
  );
}
