import { defineConfig, devices } from '@playwright/test';

const API_PORT = 8001;
const WEB_PORT = 5174;

/**
 * Приймальні тести КіноГраф: 14 сценаріїв за прецедентами з docs/uml/01_usecase.puml.
 * Запускаються на тестових даних: server.py піднімає підставну Wikidata, наповнює свіже
 * сховище звичайним оновленням і запускає API; інтерфейс працює через Vite.
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    locale: 'uk-UA',
    timezoneId: 'Europe/Kyiv',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }],
  webServer: [
    {
      command: '../backend/.venv/bin/python server.py',
      url: `http://127.0.0.1:${API_PORT}/api/genres`,
      env: { E2E_API_PORT: String(API_PORT), E2E_ADMIN_KEY: 'e2e-key' },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npm --prefix ../frontend run dev -- --host 127.0.0.1 --port ${WEB_PORT} --strictPort`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      env: { KINOGRAF_API_URL: `http://127.0.0.1:${API_PORT}` },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
