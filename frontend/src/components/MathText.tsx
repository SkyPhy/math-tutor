import { useMathJax } from '../hooks/useMathJax';

// Renders a LaTeX string as MathJax display math (\[ ... \]), re-typesetting when
// it changes. Empty string renders nothing.
export function MathText({ latex, className }: { latex?: string; className?: string }) {
  const ref = useMathJax<HTMLDivElement>(latex);
  return (
    <div ref={ref} className={className}>
      {latex ? `\\[ ${latex} \\]` : ''}
    </div>
  );
}
