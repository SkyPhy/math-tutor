import { useEffect, useRef } from 'react';

// Typeset a subtree with MathJax after `dep` changes (e.g. a new problem's LaTeX).
// MathJax is loaded from a CDN <script> in index.html and may not be ready yet —
// the call is guarded and failures are swallowed (same as the legacy page).
export function useMathJax<T extends HTMLElement = HTMLDivElement>(dep: unknown) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const mj = window.MathJax;
    if (mj?.typesetPromise && ref.current) {
      mj.typesetPromise([ref.current]).catch(() => {});
    }
  }, [dep]);
  return ref;
}
