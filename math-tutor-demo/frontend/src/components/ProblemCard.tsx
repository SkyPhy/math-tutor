import React, { useEffect, useRef } from 'react';
import { Problem } from '../types';

interface ProblemCardProps {
    problem: Problem | null;
    isLoading: boolean;
    onNewProblem: () => void;
}

// MathJax is loaded globally via a <script> tag in index.html
declare global {
    interface Window {
        MathJax?: { typesetPromise?: (els?: HTMLElement[]) => Promise<void> };
    }
}

const difficultyClass: Record<string, string> = {
    easy: 'difficulty-easy',
    medium: 'difficulty-medium',
    hard: 'difficulty-hard',
};

const ProblemCard: React.FC<ProblemCardProps> = ({ problem, isLoading, onNewProblem }) => {
    const latexRef = useRef<HTMLDivElement>(null);

    // Re-typeset the LaTeX whenever the displayed problem changes.
    useEffect(() => {
        if (problem && latexRef.current && window.MathJax?.typesetPromise) {
            window.MathJax.typesetPromise([latexRef.current]).catch(() => { });
        }
    }, [problem]);

    return (
        <div className="problem-card glass-panel">
            <div className="problem-card-top">
                <div className="problem-meta">
                    {problem && (
                        <>
                            <span className="problem-topic">{problem.topic}</span>
                            <span className={`problem-difficulty ${difficultyClass[problem.difficulty] || ''}`}>
                                {problem.difficulty}
                            </span>
                        </>
                    )}
                </div>
                <button
                    className="btn-secondary problem-refresh"
                    onClick={onNewProblem}
                    disabled={isLoading}
                    title="Get another random problem"
                >
                    {isLoading ? '⏳ Loading…' : '🎲 New Problem'}
                </button>
            </div>

            {problem ? (
                <>
                    <h2 className="problem-title">{problem.title}</h2>
                    <p className="problem-statement">{problem.statement}</p>
                    <div className="problem-latex" ref={latexRef}>
                        {`\\[ ${problem.latex} \\]`}
                    </div>
                    <p className="problem-hint-line">
                        ✍️ Work it out on the whiteboard or solve with voice / text below.
                    </p>
                </>
            ) : (
                <div className="problem-empty">
                    {isLoading ? 'Fetching a problem…' : 'No problem loaded. Click “New Problem”.'}
                </div>
            )}
        </div>
    );
};

export default ProblemCard;
