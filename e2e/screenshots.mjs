/**
 * Знімки всіх десяти екранів запущеного застосунку для README і звіту.
 *
 * Запуск: KINOGRAF_URL=http://localhost:8080 KINOGRAF_ADMIN_KEY=... node screenshots.mjs
 * Знімки зберігаються в docs/screenshots/{desktop,phone}_4-N.png, як еталони в design/screens.
 */
import { chromium } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const BASE = process.env.KINOGRAF_URL ?? 'http://localhost:8080';
const ADMIN_KEY = process.env.KINOGRAF_ADMIN_KEY ?? '';
const FILM = process.env.KINOGRAF_FILM ?? 'Q12141247';
const PERSON = process.env.KINOGRAF_PERSON ?? 'Q12150557';
const OUT = fileURLToPath(new URL('../docs/screenshots/', import.meta.url));

const DEVICES = {
  desktop: { viewport: { width: 1440, height: 900 } },
  phone: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
};

const SCREENS = [
  { id: '4-1', path: '/' },
  { id: '4-2', path: `/films/${FILM}` },
  { id: '4-3', path: `/people/${PERSON}` },
  { id: '4-4', path: `/graph/${FILM}` },
  { id: '4-5', path: '/stats' },
  { id: '4-6', path: '/quality' },
  {
    id: '4-7',
    path: '/sparql',
    prepare: async (page) => {
      await page.getByRole('button', { name: 'Виконати' }).click();
      await page.getByText(/рядк(ів|и|ок) · /).waitFor();
    },
  },
  { id: '4-8', path: '/admin/login' },
  { id: '4-9', path: '/admin', admin: true },
  { id: '4-10', path: '/open-data' },
];

await mkdir(OUT, { recursive: true });
const browser = await chromium.launch();
for (const [device, options] of Object.entries(DEVICES)) {
  for (const screen of SCREENS) {
    const context = await browser.newContext({ ...options, locale: 'uk-UA', timezoneId: 'Europe/Kyiv' });
    if (screen.admin) {
      await context.addInitScript((key) => sessionStorage.setItem('kinograf-admin-key', key), ADMIN_KEY);
    }
    const page = await context.newPage();
    await page.goto(BASE + screen.path, { waitUntil: 'load' });
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => null);
    await page.locator('h1').first().waitFor();
    await screen.prepare?.(page);
    await page.waitForTimeout(screen.id === '4-4' ? 2500 : 500);
    const file = `${OUT}${device}_${screen.id}.png`;
    await page.screenshot({ path: file });
    console.log(file);
    await context.close();
  }
}
await browser.close();
