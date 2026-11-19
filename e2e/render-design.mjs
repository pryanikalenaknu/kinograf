/**
 * Знімає еталонні екрани макета з дошок design/figma-board/doshka-*.html у design/screens.
 *
 * Запуск (потрібен інтернет для шрифтів Inter і JetBrains Mono): node render-design.mjs
 * Після зміни тексту на дошці (наприклад, справжніх чисел на екрані 4.10) знімки
 * перезнімаються цією командою.
 */
import { chromium } from '@playwright/test';
import { readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const BOARDS = fileURLToPath(new URL('../design/figma-board/', import.meta.url));
const OUT = fileURLToPath(new URL('../design/screens/', import.meta.url));

const SCREENS = [
  '4.1 Каталог',
  '4.2 Картка фільму',
  '4.3 Сторінка персоналії',
  "4.4 Граф зв'язків",
  '4.5 Статистика',
  '4.6 Якість даних',
  '4.7 SPARQL-консоль',
  '4.8 Вхід адміністратора',
  '4.9 Панель адміністрування',
  '4.10 Відкриті дані',
];

const SHOTS = [
  ...SCREENS.flatMap((screen) => {
    const id = screen.split(' ')[0].replace('.', '-');
    return [
      [`desktop_${id}.png`, `Десктоп / ${screen} / звичайний`],
      [`phone_${id}.png`, `Телефон / ${screen} / звичайний`],
    ];
  }),
  ['phone_4-2-open-data.png', 'Телефон / 4.2 Картка фільму / відкриті дані'],
  ['phone_4-3-open-data.png', 'Телефон / 4.3 Сторінка персоналії / відкриті дані'],
  ['desktop_4-6-rules.png', 'Десктоп / 4.6 Якість даних / перевірка за правилами'],
  ['phone_4-6-rules.png', 'Телефон / 4.6 Якість даних / перевірка за правилами'],
  ['desktop_4-10-access.png', 'Десктоп / 4.10 Відкриті дані / як отримати дані'],
  ['phone_4-10-access.png', 'Телефон / 4.10 Відкриті дані / як отримати дані'],
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const files = (await readdir(BOARDS)).filter((name) => /^doshka-\d+\.html$/.test(name)).sort();
const done = new Set();
for (const file of files) {
  await page.goto(`file://${BOARDS}${file}`);
  await page.evaluate(() => document.fonts.ready);
  for (const [name, label] of SHOTS) {
    if (done.has(name)) continue;
    const frame = page.locator(`[data-frame="${label}"]`);
    if ((await frame.count()) === 0) continue;
    await frame.screenshot({ path: `${OUT}${name}` });
    done.add(name);
    console.log(`${name} ← ${label}`);
  }
}
await browser.close();
const missing = SHOTS.filter(([name]) => !done.has(name)).map(([, label]) => label);
if (missing.length) {
  console.error(`Не знайдено фреймів: ${missing.join('; ')}`);
  process.exit(1);
}
