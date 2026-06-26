import { useState } from 'react'
import Whiteboard from './components/Whiteboard'
import { analyzeMath } from './api'
import './App.css'

function App() {
    const [manualInput, setManualInput] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    // In a real app, this would take the canvas image/strokes
    // send it to Mathpix, get LaTeX, then send to backend.
    // Here we mock the OCR part by allowing manual input or simulated logic.
    const handleAnalyze = async () => {
        if (!manualInput) {
            alert("Since this is a demo without live OCR keys, please type the math expression you 'drew' into the box.");
            return;
        }

        setLoading(true);
        try {
            const data = await analyzeMath(manualInput);
            setResult(data);
        } catch (error) {
            alert("Error connecting to backend");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="app-container">
            <h1>AI Math Tutor Demo</h1>

            <div className="main-content">
                <Whiteboard />

                <div className="sidebar">
                    <h2>AI Assistant</h2>
                    <p>1. Draw your math problem on the left.</p>
                    <p>2. (Mock OCR) Type what you drew below:</p>
                    <input
                        type="text"
                        placeholder="e.g. 2*x + 4 = 12"
                        value={manualInput}
                        onChange={(e) => setManualInput(e.target.value)}
                    />
                    <button onClick={handleAnalyze} disabled={loading}>
                        {loading ? "Thinking..." : "Analyze Drawing"}
                    </button>

                    {result && (
                        <div className="result-box">
                            <h3>Analysis Result</h3>
                            <p><strong>LaTeX:</strong> ${result.latex}</p>
                            {result.solution && <p><strong>Solution:</strong> {result.solution}</p>}
                            {result.steps && (
                                <div style={{ marginTop: '10px' }}>
                                    <strong>AI Steps:</strong>
                                    <ul style={{ paddingLeft: '20px' }}>
                                        {result.steps.map((step, i) => (
                                            <li key={i}>{step}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default App
