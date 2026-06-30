import { createRoot } from 'react-dom/client';
import { App } from './App';
import { StoreProvider } from './store';
import './styles.css';

// NOTE: no <React.StrictMode> here on purpose — the whiteboard is an imperative
// canvas engine with a requestAnimationFrame loop + window pointer listeners, and
// StrictMode's double-invoke of effects would mount it twice in dev.
createRoot(document.getElementById('root')!).render(
  <StoreProvider>
    <App />
  </StoreProvider>,
);
