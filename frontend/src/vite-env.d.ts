/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// MathJax is loaded from a CDN <script> in index.html.
interface Window {
  MathJax?: {
    typesetPromise?: (elements?: unknown[]) => Promise<void>;
    typeset?: (elements?: unknown[]) => void;
  };
}
