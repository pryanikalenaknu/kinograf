import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: { chunkSizeWarningLimit: 700 },
  server: {
    proxy: Object.fromEntries(
      ['/api', '/id/', '/data/', '/.well-known/void'].map((path) => [
        path,
        process.env.KINOGRAF_API_URL ?? 'http://127.0.0.1:8000',
      ]),
    ),
    fs: { allow: ['..'] },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.js'],
    include: ['tests/**/*.test.{js,jsx}'],
    css: false,
    testTimeout: 15_000,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{js,jsx}'],
      exclude: ['src/main.jsx'],
      reporter: ['text-summary', 'text'],
    },
  },
});
