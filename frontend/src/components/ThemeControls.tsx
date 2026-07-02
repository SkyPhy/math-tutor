import { useState } from 'react';
import { ACCENTS, lighten, loadAccent, loadMode, saveAccent, saveMode } from '../lib/theme';
import type { Accent, ThemeMode } from '../lib/theme';

// Global theme picker (shown in the app header on every screen): a dark/light toggle
// plus accent-colour swatches and a free colour input. Selections persist to
// localStorage and apply to <html> immediately (see lib/theme).
export function ThemeControls() {
  const [mode, setMode] = useState<ThemeMode>(loadMode);
  const [accent, setAccent] = useState<Accent>(loadAccent);

  const toggleMode = () => {
    const next: ThemeMode = mode === 'dark' ? 'light' : 'dark';
    setMode(next);
    saveMode(next);
  };
  const pick = (a: Accent) => {
    setAccent(a);
    saveAccent(a);
  };
  const isActive = (a: Accent) => accent.c1 === a.c1 && accent.c2 === a.c2;

  return (
    <div className="theme-controls">
      <button
        className="theme-mode-btn"
        onClick={toggleMode}
        title={mode === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
        aria-label="切换深色/浅色模式"
      >
        {mode === 'dark' ? '🌙' : '☀️'}
      </button>
      <div className="theme-swatches" role="group" aria-label="主题色">
        {ACCENTS.map((a) => (
          <button
            key={a.name}
            className={'theme-swatch' + (isActive(a) ? ' active' : '')}
            style={{ background: `linear-gradient(135deg, ${a.c1}, ${a.c2})` }}
            title={a.name}
            aria-label={'主题色 ' + a.name}
            onClick={() => pick(a)}
          />
        ))}
        <label className="theme-swatch theme-swatch-custom" title="自定义主题色">
          🎨
          <input
            type="color"
            value={accent.c1}
            onChange={(e) => pick({ name: 'custom', c1: e.target.value, c2: lighten(e.target.value) })}
          />
        </label>
      </div>
    </div>
  );
}
