import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import {defineConfig, loadEnv} from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

dotenv.config({ path: path.resolve(__dirname, '.env.frontend') });

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, '.', '');
  return {
    plugins: [react(), tailwindcss()],
    define: {
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify(process.env.VITE_API_BASE_URL ?? env.VITE_API_BASE_URL ?? ''),
      'import.meta.env.VITE_WS_URL': JSON.stringify(process.env.VITE_WS_URL ?? env.VITE_WS_URL ?? ''),
      'import.meta.env.VITE_WS_BASE_URL': JSON.stringify(process.env.VITE_WS_BASE_URL ?? env.VITE_WS_BASE_URL ?? ''),
      'import.meta.env.VITE_APP_MODE': JSON.stringify(process.env.VITE_APP_MODE ?? env.VITE_APP_MODE ?? 'demo'),
      'import.meta.env.VITE_ENABLE_DEMO_BADGES': JSON.stringify(process.env.VITE_ENABLE_DEMO_BADGES ?? env.VITE_ENABLE_DEMO_BADGES ?? 'true'),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modifyâfile watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
    },
  };
});
