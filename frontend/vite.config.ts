import path from 'node:path';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    // Bind IPv4 explicitly. By default Vite listens on ::1 only, so teammates and
    // scripts hitting 127.0.0.1:5173 get a connection refused that looks like a
    // broken setup. Use `npm run dev -- --host` to expose on the LAN.
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
});
