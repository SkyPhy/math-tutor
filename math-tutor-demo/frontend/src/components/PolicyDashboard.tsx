import React from 'react';
import { PoliciesResponse, MathResponse } from '../types';

interface PolicyDashboardProps {
    policies: PoliciesResponse;
    result: MathResponse | null;
}

const POLICY_ICONS: Record<string, string> = {
    pedagogical: '🎓',
    security: '🔒',
    resource: '⚡',
    domain: '📐',
};

const POLICY_COLORS: Record<string, string> = {
    pedagogical: '#818cf8',
    security: '#f87171',
    resource: '#fbbf24',
    domain: '#34d399',
};

const PolicyDashboard: React.FC<PolicyDashboardProps> = ({ policies, result }) => {
    return (
        <div className="policy-dashboard">
            {/* Framework header */}
            <div className="policy-header glass-panel">
                <h2>🛡️ Policy Governance</h2>
                <div className="framework-name">{policies.framework}</div>
                <p className="framework-desc">{policies.constraint}</p>
                <div className="threshold-display">
                    <span className="threshold-label">Penalty Threshold:</span>
                    <span className="threshold-value">{policies.penalty_threshold}</span>
                    <span className="threshold-desc">— actions exceeding this score are blocked</span>
                </div>
            </div>

            {/* Active policies grid */}
            <div className="policies-grid">
                {policies.policies.map((policy) => {
                    const icon = POLICY_ICONS[policy.type] || '📋';
                    const color = POLICY_COLORS[policy.type] || '#94a3b8';

                    return (
                        <div key={policy.name} className="policy-card glass-panel" style={{ borderLeftColor: color }}>
                            <div className="policy-icon" style={{ color }}>{icon}</div>
                            <div className="policy-info">
                                <div className="policy-name" style={{ color }}>
                                    {policy.name.replace(/_/g, ' ')}
                                </div>
                                <div className="policy-description">{policy.description}</div>
                            </div>
                            <div className="policy-penalty">
                                <div className="penalty-value" style={{
                                    color: policy.penalty >= 8 ? '#f87171' : policy.penalty >= 5 ? '#fbbf24' : '#34d399'
                                }}>
                                    {policy.penalty}
                                </div>
                                <div className="penalty-label">penalty</div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Live status */}
            <div className="policy-live-status glass-panel">
                <h3>📡 Live Compliance Status</h3>
                {result ? (
                    <div className="status-grid">
                        <div className="status-item">
                            <span className="status-icon">✅</span>
                            <span>Policy Check: <strong>Passed</strong></span>
                        </div>
                        <div className="status-item">
                            <span className="status-icon">🎓</span>
                            <span>Socratic Constraint: <strong>Active</strong></span>
                        </div>
                        <div className="status-item">
                            <span className="status-icon">🔒</span>
                            <span>Direct Answer: <strong>Forbidden</strong></span>
                        </div>
                        <div className="status-item">
                            <span className="status-icon">✅</span>
                            <span>Verification: <strong>{result.verification_status || 'N/A'}</strong></span>
                        </div>
                    </div>
                ) : (
                    <div className="status-empty">
                        Submit an expression to see live compliance status.
                    </div>
                )}
            </div>

            {/* Socratic constraint explainer */}
            <div className="socratic-explainer glass-panel">
                <h3>📖 The Socratic Constraint</h3>
                <blockquote>
                    &ldquo;You are a tutor. Break the problem down into steps, explain the underlying logic,
                    and never output the final answer immediately.&rdquo;
                </blockquote>
                <p>
                    This constraint is <strong>architecturally enforced</strong> and cannot be bypassed.
                    The system uses progressive hint levels (0–4) to gradually guide the student
                    toward understanding, ensuring cognitive engagement at every step.
                </p>
                <div className="hint-levels-visual">
                    {[
                        { level: 0, name: 'Recognize', desc: 'Problem restatement and classification' },
                        { level: 1, name: 'Strategy', desc: 'What approach should we use?' },
                        { level: 2, name: 'First Step', desc: 'Show the first concrete manipulation' },
                        { level: 3, name: 'Walkthrough', desc: 'Most steps, user does the final one' },
                        { level: 4, name: 'Full Guide', desc: 'Complete guided solution with reflection' },
                    ].map(h => (
                        <div key={h.level} className="hint-level-item">
                            <div className="hint-level-num">{h.level}</div>
                            <div className="hint-level-info">
                                <strong>{h.name}</strong>
                                <span>{h.desc}</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Lattice Framework */}
            <div className="lattice-section glass-panel">
                <h3>🔄 Lattice Framework — Continuous Guardrail Optimization</h3>
                <div className="lattice-steps">
                    {[
                        { step: 1, name: 'Risk Assessment', desc: 'Dual-check evaluation to identify coverage gaps', icon: '🔍' },
                        { step: 2, name: 'Case Expansion', desc: 'Generate adversarial variations to discover vulnerabilities', icon: '🧪' },
                        { step: 3, name: 'Guardrail Optimization', desc: 'Autonomously update policy definitions', icon: '⚡' },
                        { step: 4, name: 'Performance Evaluation', desc: 'Validate and auto-revert if efficacy degrades', icon: '📊' },
                    ].map(s => (
                        <div key={s.step} className="lattice-step">
                            <div className="lattice-icon">{s.icon}</div>
                            <div className="lattice-info">
                                <strong>Step {s.step}: {s.name}</strong>
                                <p>{s.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default PolicyDashboard;
