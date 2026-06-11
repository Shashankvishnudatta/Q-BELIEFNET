/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_WS_URL?: string;
  readonly VITE_WS_BASE_URL?: string;
  readonly VITE_APP_MODE?: string;
  readonly VITE_ENABLE_DEMO_BADGES?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
