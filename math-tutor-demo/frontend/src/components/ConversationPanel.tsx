import React, { useEffect, useRef } from 'react';
import { SocraticMessage } from '../types';

interface ConversationPanelProps {
    conversation: SocraticMessage[];
    hintLevel: number;
    canRevealMore: boolean;
    onNextHint: () => void;
    isLoading: boolean;
    verificationStatus: string;
}

const ConversationPanel: React.FC<ConversationPanelProps> = ({
    conversation,
    hintLevel,
    canRevealMore,
    onNextHint,
    isLoading,
    verificationStatus,
}) => {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [conversation]);

    if (conversation.length === 0) {
        return (
            <div className="conversation-panel glass-panel">
                <div className="conversation-empty">
                    <div className="empty-icon">💬</div>
                    <h3>Socratic Dialogue</h3>
                    <p>Enter a math expression above to start a guided learning conversation.</p>
                    <div className="empty-features">
                        <div className="feature-tag">🧠 Progressive Hints</div>
                        <div className="feature-tag">✅ CAS Verified</div>
                        <div className="feature-tag">🛡️ Pedagogical Guardrails</div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="conversation-panel glass-panel">
            <div className="conversation-header">
                <h3>🎓 Socratic Dialogue</h3>
                <div className="hint-badges">
                    <span className="hint-badge">Hint Level: {hintLevel}/4</span>
                    {verificationStatus === 'verified' && (
                        <span className="verification-badge verified">✅ CAS Verified</span>
                    )}
                    {verificationStatus === 'partial' && (
                        <span className="verification-badge partial">⚠️ Partial</span>
                    )}
                </div>
            </div>

            {/* Hint progress bar */}
            <div className="hint-progress">
                <div className="hint-progress-bar" style={{ width: `${(hintLevel / 4) * 100}%` }} />
                <div className="hint-progress-labels">
                    {['Recognize', 'Strategy', 'First Step', 'Walkthrough', 'Full Guide'].map((label, i) => (
                        <span key={i} className={`hint-label ${i <= hintLevel ? 'active' : ''}`}>{label}</span>
                    ))}
                </div>
            </div>

            {/* Messages */}
            <div className="conversation-messages">
                {conversation.map((msg, idx) => (
                    <MessageBubble key={idx} message={msg} index={idx} />
                ))}
                {isLoading && (
                    <div className="message-bubble tutor">
                        <div className="bubble-content">
                            <div className="typing-indicator">
                                <span></span><span></span><span></span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            {/* Action bar */}
            {canRevealMore && (
                <div className="conversation-actions">
                    <button
                        className="btn-hint"
                        onClick={onNextHint}
                        disabled={isLoading}
                    >
                        {isLoading ? 'Thinking…' : `💡 Next Hint (Level ${hintLevel + 1})`}
                    </button>
                    <span className="hint-warning">
                        {hintLevel < 2
                            ? "Try solving it yourself first!"
                            : hintLevel < 4
                                ? "Getting closer to the solution…"
                                : ""}
                    </span>
                </div>
            )}
        </div>
    );
};

function MessageBubble({ message, index }: { message: SocraticMessage; index: number }) {
    const isUser = message.role === 'user';
    const isSystem = message.role === 'system';
    const isSeparator = message.type === 'separator';

    if (isSeparator) {
        return (
            <div className="message-separator">
                <span>{message.content}</span>
            </div>
        );
    }

    const typeIcons: Record<string, string> = {
        encouragement: '🌟',
        observation: '👁️',
        classification: '📊',
        question: '🤔',
        prompt: '💡',
        strategy: '📋',
        step_header: '📐',
        step_detail: '📝',
        step: '📝',
        guidance: '🧭',
        challenge: '🎯',
        reflection: '🌟',
        verification: '✅',
        policy_violation: '🛡️',
        error: '⚠️',
    };

    const icon = typeIcons[message.type || ''] || (isUser ? '👤' : isSystem ? '⚙️' : '🎓');

    return (
        <div
            className={`message-bubble ${isUser ? 'user' : isSystem ? 'system' : 'tutor'}`}
            style={{ animationDelay: `${index * 0.08}s` }}
        >
            <div className="bubble-avatar">{icon}</div>
            <div className="bubble-content">
                <div className="bubble-role">{isUser ? 'You' : isSystem ? 'System' : 'AI Tutor'}</div>
                <div className="bubble-text" dangerouslySetInnerHTML={{
                    __html: formatMathContent(message.content)
                }} />
            </div>
        </div>
    );
}

function formatMathContent(text: string): string {
    // Convert **bold** to <strong>
    let result = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Convert $latex$ to <code class="math">
    result = result.replace(/\$(.*?)\$/g, '<code class="math-inline">$1</code>');
    // Convert newlines
    result = result.replace(/\n/g, '<br/>');
    return result;
}

export default ConversationPanel;
