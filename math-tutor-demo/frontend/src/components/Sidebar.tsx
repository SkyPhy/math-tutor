import React, { useState } from 'react';
import { MathResponse } from '../types';

interface SidebarProps {
    onAnalyze: (input: string) => void;
    result: MathResponse | null;
    isLoading: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ onAnalyze, result, isLoading }) => {
    const [input, setInput] = useState("");

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !isLoading) {
            onAnalyze(input);
        }
    };

    const exampleProblems = [
        { label: "Linear", expr: "2*x + 5 = 15" },
        { label: "Quadratic", expr: "x**2 - 5*x + 6 = 0" },
        { label: "Simplify", expr: "x**2 + 2*x + 1" },
        { label: "Complex", expr: "3*x**2 + 12*x = 0" },
    ];

    return (
        <div className="sidebar-panel glass-panel">
            <div className="sidebar-header">
                <h3>🎙️ Solve with Voice or Text</h3>
                <p className="sidebar-subtitle">Type or speak your solution — or work it out on the whiteboard</p>
            </div>

            <div className="input-group">
                <div className="input-row">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="e.g. 2*x + 4 = 10"
                        disabled={isLoading}
                    />
                    <button className="voice-btn" title="Voice Input (coming soon)" style={{
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: 12,
                        padding: '10px 14px',
                        fontSize: '1.2rem',
                        cursor: 'pointer',
                        color: 'white',
                        transition: 'all 0.2s ease',
                    }}>🎤</button>
                </div>

                <button
                    className="btn-primary analyze-btn"
                    onClick={() => onAnalyze(input)}
                    disabled={isLoading || !input.trim()}
                >
                    {isLoading ? (
                        <span className="btn-loading">
                            <span className="spinner"></span> Analyzing…
                        </span>
                    ) : (
                        '🔍 Analyze Expression'
                    )}
                </button>
            </div>

            {/* Example problems */}
            <div className="examples-section">
                <div className="examples-label">Quick Examples</div>
                <div className="examples-grid">
                    {exampleProblems.map(ex => (
                        <button
                            key={ex.expr}
                            className="example-btn"
                            onClick={() => {
                                setInput(ex.expr);
                                onAnalyze(ex.expr);
                            }}
                            disabled={isLoading}
                        >
                            <span className="example-label">{ex.label}</span>
                            <span className="example-expr">{ex.expr}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Classification badge */}
            {result?.classification && (
                <div className="classification-badge">
                    <div className="class-row">
                        <span className="class-label">Type:</span>
                        <span className="class-value">{result.classification.type?.replace(/_/g, ' ')}</span>
                    </div>
                    <div className="class-row">
                        <span className="class-label">Topic:</span>
                        <span className="class-value">{result.classification.topic}</span>
                    </div>
                    <div className="class-row">
                        <span className="class-label">Complexity:</span>
                        <span className={`class-value complexity-${result.classification.complexity}`}>
                            {result.classification.complexity}
                        </span>
                    </div>
                    {result.classification.variables && result.classification.variables.length > 0 && (
                        <div className="class-row">
                            <span className="class-label">Variables:</span>
                            <span className="class-value">{result.classification.variables.join(', ')}</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default Sidebar;
