import { expect, test } from '@playwright/test';

test("9. Досліджувати граф зв'язків (UC7)", async ({ page }) => {
  await page.goto('/films/Q1004');
  await page.getByRole('link', { name: "Граф зв'язків" }).filter({ visible: true }).click();
  await expect(page).toHaveURL(/\/graph\/Q1004$/);
  await expect(page.getByText("Вузлів: 4 · зв'язків: 4")).toBeVisible();
  await expect(page.locator('.graph-network canvas')).toBeVisible();

  const depth = page.getByRole('group', { name: 'Глибина графа' });
  await depth.getByRole('button', { name: '1 рівень' }).click();
  await expect(page.getByText("Вузлів: 3 · зв'язків: 2")).toBeVisible();
  await depth.getByRole('button', { name: '2 рівні' }).click();
  await expect(page.getByText("Вузлів: 4 · зв'язків: 4")).toBeVisible();

  await page.getByRole('textbox', { name: 'Знайти вузол' }).fill('мам');
  await page.getByRole('option', { name: /Мамай/ }).click();
  const panel = page.getByRole('complementary', { name: 'Вибраний вузол' });
  await expect(panel.getByRole('heading', { name: 'Мамай' })).toBeVisible();
  await expect(panel.getByText('2003 · Олесь Санін')).toBeVisible();
  await panel.getByRole('button', { name: 'Зробити центром графа' }).click();
  await expect(page).toHaveURL(/\/graph\/Q1003$/);
  await expect(page.getByText(/Центр: «Мамай»/)).toBeVisible();
});

test('10. Переглянути статистику (UC8)', async ({ page }) => {
  await page.goto('/stats');
  await expect(page.getByRole('heading', { name: 'Статистика' })).toBeVisible();
  await expect(page.getByRole('img', { name: /кількості фільмів за роками з 1995 по 2022/ })).toBeVisible();
  await expect(page.getByRole('img', { name: /жанрів у періодах/ })).toBeVisible();
  const directors = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Топ-10 режисерів' }) });
  await expect(directors.getByRole('listitem').first()).toHaveText(/1\. Валентин Васянович\s*2/);
  const actors = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Топ-10 акторів' }) });
  await expect(actors.getByRole('listitem').first()).toHaveText(/1\. Андрій Римарук\s*2/);
});

test('11. Переглянути якість даних (UC9)', async ({ page }) => {
  await page.goto('/quality');
  await expect(page.getByRole('heading', { name: 'Якість даних' })).toBeVisible();
  await expect(page.getByText(/^Дані оновлено: \d{2}\.\d{2}\.\d{4}, \d{2}:\d{2}$/)).toBeVisible();
  const metric = (label) => page.locator('.metric').filter({ hasText: label });
  await expect(metric('Усього фільмів')).toContainText('14');
  await expect(metric('З режисером')).toContainText('93%');
  await expect(metric('З режисером')).toContainText('13 з 14');
  await expect(metric('З акторами')).toContainText('4 з 14');
  await expect(page.getByRole('img', { name: /частки фільмів із режисером/ })).toBeVisible();
});

test('12. Виконати SPARQL-запит (UC10)', async ({ page }) => {
  await page.goto('/sparql');
  await page.getByRole('button', { name: 'Виконати' }).click();
  const results = page.getByRole('region', { name: 'Результати' });
  await expect(results.getByText(/^11 рядків · /)).toBeVisible();
  await expect(results.getByRole('columnheader')).toHaveText(['?filmLabel', '?year']);

  const examples = page.getByRole('complementary', { name: 'Готові приклади' });
  await examples.getByRole('button', { name: 'Режисери з найбільшою кількістю фільмів' }).click();
  await page.getByRole('button', { name: 'Виконати' }).click();
  await expect(results.getByRole('columnheader')).toHaveText(['?directorLabel', '?films']);
  await expect(results.getByRole('row').nth(1)).toContainText('2');

  await examples.getByRole('button', { name: 'Фільми одного актора' }).click();
  await page.getByRole('button', { name: 'Виконати' }).click();
  await expect(results.getByText('Порожній результат')).toBeVisible();

  await page.getByRole('textbox', { name: 'Текст SPARQL-запиту' }).fill('SELECT ?x WHERE {\n  ?x ?y\n');
  await page.getByRole('textbox', { name: 'Текст SPARQL-запиту' }).press('Control+Enter');
  await expect(results.getByRole('alert')).toContainText('синтаксична помилка');

  await page.getByRole('textbox', { name: 'Текст SPARQL-запиту' }).fill('ASK { ?s ?p ?o }');
  await page.getByRole('button', { name: 'Виконати' }).click();
  await expect(results.getByRole('alert')).toContainText('дозволено лише запити SELECT');
});
