import { useMathJax } from '../hooks/useMathJax';
import { asInlineMath } from '../lib/mathRender';

// Renders a LaTeX string as INLINE MathJax maths (\( ... \)) — fused, never on its own
// display line (see lib/mathRender) — re-typesetting when it changes. Empty → nothing.
export function MathText({ latex, className }: { latex?: string; className?: string }) {
  const ref = useMathJax<HTMLDivElement>(latex);
  return (
    <div ref={ref} className={className}>
      {latex ? asInlineMath(latex) : ''}
    </div>
  );
}
