import React, { useState } from 'react';
import { ArchitectureTree } from '../types';

interface ArchitecturePanelProps {
    architecture: ArchitectureTree;
    pipelineStage: string;
}

const LAYER_COLORS = [
    { bg: 'rgba(56, 189, 248, 0.1)', border: '#38bdf8', accent: '#38bdf8' },   // Layer 1 - Blue
    { bg: 'rgba(129, 140, 248, 0.1)', border: '#818cf8', accent: '#818cf8' },   // Layer 2 - Purple
    { bg: 'rgba(52, 211, 153, 0.1)', border: '#34d399', accent: '#34d399' },    // Layer 3 - Green
    { bg: 'rgba(251, 146, 60, 0.1)', border: '#fb923c', accent: '#fb923c' },    // Layer 4 - Orange
];

const ArchitecturePanel: React.FC<ArchitecturePanelProps> = ({ architecture, pipelineStage }) => {
    const [expandedLayer, setExpandedLayer] = useState<string | null>(null);
    const [showAgents, setShowAgents] = useState(false);

    return (
        <div className="architecture-panel">
            {/* System overview */}
            <div className="arch-header glass-panel">
                <div className="arch-title">
                    <h2>🏛️ {architecture.name}</h2>
                    <span className="version-badge">v{architecture.version}</span>
                </div>
                <p className="arch-desc">
                    Multi-layered, AI-native architecture with structural separation of
                    UI, cognitive processing, and validation environments.
                </p>
                <div className="arch-stats">
                    <div className="stat">
                        <span className="stat-value">{architecture.layers.length}</span>
                        <span className="stat-label">Layers</span>
                    </div>
                    <div className="stat">
                        <span className="stat-value">
                            {architecture.layers.reduce((a, l) => a + l.components.length, 0)}
                        </span>
                        <span className="stat-label">Components</span>
                    </div>
                    <div className="stat">
                        <span className="stat-value">{architecture.agents.length}</span>
                        <span className="stat-label">ALMAS Agents</span>
                    </div>
                </div>
            </div>

            {/* Layer stack */}
            <div className="layer-stack">
                {architecture.layers.map((layer, idx) => {
                    const colors = LAYER_COLORS[idx % LAYER_COLORS.length];
                    const isExpanded = expandedLayer === layer.id;

                    return (
                        <div
                            key={layer.id}
                            className={`layer-card ${isExpanded ? 'expanded' : ''}`}
                            style={{
                                background: colors.bg,
                                borderColor: colors.border,
                            }}
                            onClick={() => setExpandedLayer(isExpanded ? null : layer.id)}
                        >
                            <div className="layer-header">
                                <div className="layer-number" style={{ color: colors.accent }}>
                                    L{idx + 1}
                                </div>
                                <div className="layer-info">
                                    <h3 style={{ color: colors.accent }}>{layer.name}</h3>
                                    <p>{layer.purpose}</p>
                                </div>
                                <div className="layer-status" style={{ color: colors.accent }}>
                                    {layer.status === 'active' ? '🟢' : '🔴'} {layer.components.length} components
                                </div>
                            </div>

                            {isExpanded && (
                                <div className="layer-components">
                                    {layer.components.map(comp => (
                                        <div key={comp.id} className="component-card" style={{ borderLeftColor: colors.accent }}>
                                            <div className="comp-name">{comp.name}</div>
                                            <div className="comp-purpose">{comp.purpose}</div>
                                            <div className="comp-status">
                                                {comp.status === 'active' ? '🟢 Active' : '🔴 Inactive'}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* ALMAS Agents */}
            <div className="agents-section glass-panel">
                <div
                    className="agents-header"
                    onClick={() => setShowAgents(!showAgents)}
                    style={{ cursor: 'pointer' }}
                >
                    <h3>🤖 ALMAS Multi-Agent Framework</h3>
                    <span className="toggle-icon">{showAgents ? '▴' : '▾'}</span>
                </div>

                {showAgents && (
                    <div className="agents-grid">
                        {architecture.agents.map(agent => (
                            <div key={agent.id} className="agent-card">
                                <div className="agent-icon">
                                    {agent.role === 'Product Manager' ? '📋' :
                                        agent.role === 'Engineering Manager' ? '👔' :
                                            agent.role === 'Technical Writer' ? '📝' :
                                                agent.role === 'Systems Architect' ? '🏗️' :
                                                    agent.role === 'Software Engineer' ? '⚙️' :
                                                        agent.role === 'QA / Code Reviewer' ? '🔍' : '🤖'}
                                </div>
                                <div className="agent-info">
                                    <div className="agent-name">{agent.name}</div>
                                    <div className="agent-role">{agent.role}</div>
                                    <div className="agent-function">{agent.function}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Data flow diagram */}
            <div className="dataflow glass-panel">
                <h3>📊 Data Flow — ALMAS Pipeline</h3>
                <div className="flow-diagram">
                    <div className="flow-node">User Input</div>
                    <div className="flow-arrow">→</div>
                    <div className="flow-node highlight-blue">Sprint Agent</div>
                    <div className="flow-arrow">→</div>
                    <div className="flow-node highlight-purple">Policy Engine</div>
                    <div className="flow-arrow">→</div>
                    <div className="flow-node highlight-green">Blending Instructions</div>
                    <div className="flow-arrow">→</div>
                    <div className="flow-node highlight-blue">Neuro-Symbolic Engine</div>
                    <div className="flow-arrow">→</div>
                    <div className="flow-node highlight-orange">Socratic Engine</div>
                    <div className="flow-arrow">→</div>
                    <div className="flow-node">Guided Response</div>
                </div>
            </div>
        </div>
    );
};

export default ArchitecturePanel;
