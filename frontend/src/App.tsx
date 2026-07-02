import { useStore } from './store';
import { ProblemScreen } from './screens/ProblemScreen';
import { SelectScreen } from './screens/SelectScreen';
import { CheckScreen } from './screens/CheckScreen';
import { AssistantScreen } from './screens/AssistantScreen';
import { AskScreen } from './screens/AskScreen';
import { ThemeControls } from './components/ThemeControls';
import { ModelControls } from './components/ModelControls';

// Global header + the five guided-flow screens. Only the active screen is shown
// (CSS `.screen` / `.screen.active`). The problem screen uses the global header;
// screens ②–⑤ render their own back-button header.
export function App() {
  const { screen } = useStore();
  return (
    <>
      <ThemeControls />
      <ModelControls />
      <h1>AI Math Tutor</h1>
      <div className="subtitle">苏格拉底式数学辅导 · 引导而非直接给答案，正确性由多路共识保障</div>

      <div className="page-wrap">
        <ProblemScreen active={screen === 'problem'} />
        <SelectScreen active={screen === 'select'} />
        <CheckScreen active={screen === 'check'} />
        <AssistantScreen active={screen === 'assistant'} />
        <AskScreen active={screen === 'ask'} />
      </div>
    </>
  );
}
