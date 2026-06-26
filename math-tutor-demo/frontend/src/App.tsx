import { useState, useRef, useEffect } from 'react'
import CanvasBoard, { CanvasBoardRef } from './components/CanvasBoard'
import Sidebar from './components/Sidebar'
import ProblemCard from './components/ProblemCard'
import ArchitecturePanel from './components/ArchitecturePanel'
import PolicyDashboard from './components/PolicyDashboard'
import ConversationPanel from './components/ConversationPanel'
import { MathResponse, HintResponse, ArchitectureTree, PoliciesResponse, SocraticMessage, Problem } from './types'
import axios from 'axios'

const BASE_URL = 'http://localhost:8000';

function App() {
    const [result, setResult] = useState<MathResponse | null>(null);
    const [isAnalyzeLoading, setIsAnalyzeLoading] = useState(false);
    const [canvasRef, setCanvasRef] = useState<any>(null);
    const canvasBoardRef = useRef<CanvasBoardRef>(null);

    // Socratic conversation state
    const [sessionId, setSessionId] = useState<string>("");
    const [conversation, setConversation] = useState<SocraticMessage[]>([]);
    const [currentExpression, setCurrentExpression] = useState<string>("");
    const [hintLevel, setHintLevel] = useState(0);
    const [canRevealMore, setCanRevealMore] = useState(false);

    // Architecture & policy state
    const [architecture, setArchitecture] = useState<ArchitectureTree | null>(null);
    const [policies, setPolicies] = useState<PoliciesResponse | null>(null);
    const [activeTab, setActiveTab] = useState<'tutor' | 'architecture' | 'policies'>('tutor');

    // Random problem state
    const [problem, setProblem] = useState<Problem | null>(null);
    const [isProblemLoading, setIsProblemLoading] = useState(false);

    // Pipeline animation state
    const [pipelineStage, setPipelineStage] = useState<string>("");
    const [verificationStatus, setVerificationStatus] = useState<string>("");

    // Fetch a random problem (used on mount and by the "New Problem" button)
    const loadProblem = async () => {
        setIsProblemLoading(true);
        try {
            const r = await axios.get(`${BASE_URL}/problems/random`, {
                params: problem ? { exclude_id: problem.id } : {},
            });
            setProblem(r.data);
        } catch (e) {
            console.error("Failed to load problem", e);
        } finally {
            setIsProblemLoading(false);
        }
    };

    // Fetch architecture, policies & first problem on mount
    useEffect(() => {
        axios.get(`${BASE_URL}/architecture`).then(r => setArchitecture(r.data)).catch(() => { });
        axios.get(`${BASE_URL}/policies`).then(r => setPolicies(r.data)).catch(() => { });
        loadProblem();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleAnalyze = async (input: string) => {
        setIsAnalyzeLoading(true);
        setResult(null);
        setConversation([]);
        setHintLevel(0);

        // Add user message to conversation
        const userMsg: SocraticMessage = { role: "user", content: `Solve: ${input}`, type: "request" };
        setConversation([userMsg]);

        // Animate pipeline stages
        setPipelineStage("sprint");
        await sleep(400);

        try {
            let response;

            if (!input.trim() && canvasBoardRef.current) {
                const blob = await canvasBoardRef.current.getCanvasBlob();
                if (blob) {
                    const formData = new FormData();
                    formData.append('file', blob, 'canvas_image.png');

                    setPipelineStage("control");
                    const recognizeResp = await axios.post(`${BASE_URL}/recognize`, formData, {
                        headers: { 'Content-Type': 'multipart/form-data' }
                    });
                    const recognizedText = recognizeResp.data.text;
                    if (!recognizedText) {
                        alert("Could not recognize any text.");
                        setIsAnalyzeLoading(false);
                        setPipelineStage("");
                        return;
                    }
                    setCurrentExpression(recognizedText);
                    setPipelineStage("developer");
                    response = await axios.post(`${BASE_URL}/analyze`, {
                        expression: recognizedText,
                        action: 'solve',
                        session_id: sessionId || undefined
                    });
                } else {
                    alert("Could not grab canvas image.");
                    setIsAnalyzeLoading(false);
                    setPipelineStage("");
                    return;
                }
            } else {
                setCurrentExpression(input);
                setPipelineStage("developer");
                await sleep(300);
                response = await axios.post(`${BASE_URL}/analyze`, {
                    expression: input,
                    action: 'solve',
                    session_id: sessionId || undefined
                });
            }

            setPipelineStage("peer");
            await sleep(300);

            const data: MathResponse = response.data;
            setSessionId(data.session_id);
            setResult(data);

            // Build conversation from Socratic response
            if (data.socratic) {
                const tutorMsgs: SocraticMessage[] = data.socratic.messages.map(m => ({
                    role: m.role as "tutor" | "user" | "system",
                    content: m.content,
                    type: m.type,
                }));
                setConversation(prev => [...prev, ...tutorMsgs]);
                setCanRevealMore(data.socratic.can_reveal_more);
                setHintLevel(data.socratic.hint_level);
            }

            setVerificationStatus(data.verification_status || "");
            setPipelineStage("complete");
            await sleep(600);
            setPipelineStage("");

        } catch (error: any) {
            console.error(error);
            const errMsg = error?.response?.data?.detail;
            if (typeof errMsg === 'object' && errMsg.violations) {
                setConversation(prev => [...prev, {
                    role: "system",
                    content: `🛡️ **Policy Violation:** ${errMsg.violations.join(", ")}`,
                    type: "policy_violation",
                }]);
            } else {
                setConversation(prev => [...prev, {
                    role: "system",
                    content: "⚠️ Error connecting to the backend.",
                    type: "error",
                }]);
            }
            setPipelineStage("");
        } finally {
            setIsAnalyzeLoading(false);
        }
    };

    const handleNextHint = async () => {
        if (!currentExpression || !canRevealMore) return;

        setIsAnalyzeLoading(true);
        try {
            const response = await axios.post(`${BASE_URL}/hint`, {
                expression: currentExpression,
                session_id: sessionId,
            });

            const data: HintResponse = response.data;
            const newMsgs: SocraticMessage[] = data.socratic.messages.map(m => ({
                role: m.role as "tutor" | "user" | "system",
                content: m.content,
                type: m.type,
            }));

            // Add a separator
            setConversation(prev => [
                ...prev,
                { role: "system", content: `── Hint Level ${data.hint_level} ──`, type: "separator" },
                ...newMsgs
            ]);
            setHintLevel(data.hint_level);
            setCanRevealMore(data.socratic.can_reveal_more);
            setVerificationStatus(data.verification_status);

        } catch (error) {
            console.error(error);
        } finally {
            setIsAnalyzeLoading(false);
        }
    };

    return (
        <div className="app-wrapper">
            {/* Animated background */}
            <div className="bg-orbs">
                <div className="orb orb-1"></div>
                <div className="orb orb-2"></div>
                <div className="orb orb-3"></div>
            </div>

            {/* Header */}
            <header className="app-header">
                <h1>AI Math Tutor</h1>
                <div className="subtitle">
                    Self-Evolving Architecture • Socratic Pedagogy • Neuro-Symbolic Verification
                </div>

                {/* ALMAS Pipeline Indicator */}
                {pipelineStage && (
                    <div className="pipeline-indicator">
                        <PipelineStage name="Sprint" icon="📋" active={pipelineStage === "sprint"} done={["control", "developer", "peer", "complete"].includes(pipelineStage)} />
                        <div className="pipeline-connector" />
                        <PipelineStage name="Control" icon="🏗️" active={pipelineStage === "control"} done={["developer", "peer", "complete"].includes(pipelineStage)} />
                        <div className="pipeline-connector" />
                        <PipelineStage name="Developer" icon="⚙️" active={pipelineStage === "developer"} done={["peer", "complete"].includes(pipelineStage)} />
                        <div className="pipeline-connector" />
                        <PipelineStage name="Peer Review" icon="🔍" active={pipelineStage === "peer"} done={["complete"].includes(pipelineStage)} />
                    </div>
                )}
            </header>

            {/* Tab Navigation */}
            <nav className="tab-nav">
                <button className={`tab-btn ${activeTab === 'tutor' ? 'active' : ''}`} onClick={() => setActiveTab('tutor')}>
                    🎓 Tutor
                </button>
                <button className={`tab-btn ${activeTab === 'architecture' ? 'active' : ''}`} onClick={() => setActiveTab('architecture')}>
                    🏛️ Architecture
                </button>
                <button className={`tab-btn ${activeTab === 'policies' ? 'active' : ''}`} onClick={() => setActiveTab('policies')}>
                    🛡️ Policies
                </button>
            </nav>

            {/* Main Content */}
            <main className="app-main">
                {activeTab === 'tutor' && (
                    <div className="tutor-tab">
                        {/* Random problem to solve */}
                        <ProblemCard
                            problem={problem}
                            isLoading={isProblemLoading}
                            onNewProblem={loadProblem}
                        />

                        {/* Whiteboard + "Solve with Voice or Text" — below the problem */}
                        <div className="tutor-layout">
                            <div className="tutor-left">
                                <CanvasBoard ref={canvasBoardRef} setCanvasRef={setCanvasRef} result={result} />
                            </div>
                            <div className="tutor-right">
                                <Sidebar
                                    onAnalyze={handleAnalyze}
                                    result={result}
                                    isLoading={isAnalyzeLoading}
                                />
                                <ConversationPanel
                                    conversation={conversation}
                                    hintLevel={hintLevel}
                                    canRevealMore={canRevealMore}
                                    onNextHint={handleNextHint}
                                    isLoading={isAnalyzeLoading}
                                    verificationStatus={verificationStatus}
                                />
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'architecture' && architecture && (
                    <ArchitecturePanel architecture={architecture} pipelineStage={pipelineStage} />
                )}

                {activeTab === 'policies' && policies && (
                    <PolicyDashboard policies={policies} result={result} />
                )}
            </main>

            {/* Footer */}
            <footer className="app-footer">
                <span className="footer-badge">SEPGA Compliant</span>
                <span className="footer-badge">SymPy CAS Verified</span>
                <span className="footer-badge">Socratic Guardrails Active</span>
                {sessionId && <span className="footer-session">Session: {sessionId.slice(0, 8)}…</span>}
            </footer>
        </div>
    )
}

function PipelineStage({ name, icon, active, done }: { name: string; icon: string; active: boolean; done: boolean }) {
    return (
        <div className={`pipeline-stage ${active ? 'active' : ''} ${done ? 'done' : ''}`}>
            <span className="pipeline-icon">{icon}</span>
            <span className="pipeline-name">{name}</span>
        </div>
    );
}

function sleep(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

export default App
