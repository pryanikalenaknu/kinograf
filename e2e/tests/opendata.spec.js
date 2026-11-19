import { expect, test } from '@playwright/test';

test('15. Переглянути опис відкритих даних (UC16, UC22)', async ({ page }) => {
  await page.goto('/sparql');
  await page.getByRole('navigation', { name: 'Головне меню' }).getByRole('link', { name: 'Відкриті дані' }).click();
  await expect(page).toHaveURL(/\/open-data$/);
  await expect(page.getByRole('heading', { name: 'Відкриті дані', level: 1 })).toBeVisible();

  const stars = page.getByRole('region', { name: "П'ять зірок відкритих даних" });
  await expect(stars.getByRole('listitem')).toHaveCount(5);
  const dataset = page.getByRole('region', { name: 'Набір даних' });
  await expect(dataset).toContainText('Фільмів14');
  await expect(dataset).toContainText('Персоналій14');

  const links = page.getByRole('region', { name: "Зв'язки з іншими наборами" }).getByRole('table');
  await expect(links.getByRole('row')).toHaveText([
    /Набір\s*Властивість\s*Фільмів\s*Персоналій/,
    /Wikidata\s*owl:sameAs\s*14\s*14/,
    /Вікіпедія \(укр\.\)\s*schema:sameAs\s*5\s*3/,
    /IMDb\s*schema:sameAs\s*5\s*2/,
    /DBpedia\s*owl:sameAs\s*4\s*2/,
  ]);

  const access = page.getByRole('region', { name: 'Як отримати дані' });
  await expect(access.getByLabel('Приклад запиту й відповіді')).toContainText(
    'curl -L -H "Accept: text/turtle"',
  );

  const download = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Завантажити набір (Turtle)' }).click();
  expect((await download).suggestedFilename()).toBe('kinograf.ttl');
});

test('16. Отримати дані фільму у форматі RDF за постійною адресою (UC19, UC20)', async ({
  page,
  request,
}) => {
  const redirect = await request.get('/id/film/Q1004', {
    headers: { Accept: 'text/turtle' },
    maxRedirects: 0,
  });
  expect(redirect.status()).toBe(303);
  expect(redirect.headers().location).toBe('/data/film/Q1004.ttl');
  expect(redirect.headers().vary).toBe('Accept');
  expect(redirect.headers()['access-control-allow-origin']).toBe('*');

  const document = await request.get('/id/film/Q1004', { headers: { Accept: 'text/turtle' } });
  expect(document.status()).toBe(200);
  expect(document.headers()['content-type']).toBe('text/turtle; charset=utf-8');
  const turtle = await document.text();
  expect(turtle).toMatch(/<http:\/\/127\.0\.0\.1:5174\/id\/film\/Q1004> a schema:Movie/);
  expect(turtle).toContain('"Поводир"@uk');
  expect(turtle).toContain('owl:sameAs');

  const void_ = await request.get('/.well-known/void');
  expect(void_.headers()['content-type']).toBe('text/turtle; charset=utf-8');
  expect(await void_.text()).toContain('void:Linkset');

  await page.goto('/films/Q1004');
  const panel = page.getByRole('region', { name: 'Відкриті дані' });
  await expect(panel.getByText('http://127.0.0.1:5174/id/film/Q1004')).toBeVisible();
  await expect(panel.getByRole('link', { name: /IMDb/ })).toHaveAttribute(
    'href',
    'https://www.imdb.com/title/tt3699354/',
  );
  await expect(panel.getByRole('link', { name: /DBpedia/ })).toBeVisible();
  const script = page.locator('head script[type="application/ld+json"]');
  await expect(script).toHaveCount(1);
  expect(JSON.parse(await script.textContent())['@context']['@vocab']).toBe('https://schema.org/');

  const browserPage = await page.request.get('/id/film/Q1004', {
    headers: { Accept: 'text/html' },
    maxRedirects: 0,
  });
  expect(browserPage.headers().location).toBe('/films/Q1004');
});

test('17. Переглянути зауваження за правилами й перейти до виправлення (UC17, UC18)', async ({
  page,
}) => {
  await page.goto('/quality');
  const rules = page.getByRole('region', { name: /Перевірка за правилами/ });
  await expect(rules.getByText(/^14 фільмів перевірено за 10 правилами /)).toBeVisible();
  await expect(rules.getByText(/Зауваження мають 14 фільмів: з помилками — 0, з попередженнями — 10, лише з підказками — 4\./)).toBeVisible();
  const table = rules.getByRole('table');
  await expect(table.getByRole('row').filter({ hasText: 'Актори' })).toContainText('10');
  await expect(table.getByRole('row').filter({ hasText: 'Зображення' })).toContainText('14');

  await rules.getByLabel('Правило').selectOption({ label: 'Жанр' });
  await expect(rules.getByText('Показано 1–1 з 1')).toBeVisible();
  const item = rules.getByRole('listitem').filter({ has: page.getByRole('link', { name: 'Їжак' }) });
  await expect(item.locator('.issue-tag')).toHaveText(['немає режисера', 'немає акторів', 'немає жанру', '+3']);
  await expect(item.getByRole('link', { name: /Виправити у Wikidata/ })).toHaveAttribute(
    'href',
    'https://www.wikidata.org/wiki/Q1007#P136',
  );

  await rules.getByLabel('Правило').selectOption({ label: 'Усі правила' });
  await rules.getByLabel('Рівень').selectOption({ label: 'Підказки' });
  await expect(rules.getByText('Показано 1–12 з 14')).toBeVisible();
  const report = await page.request.get('/api/quality/report.ttl');
  expect(report.headers()['content-type']).toBe('text/turtle; charset=utf-8');
  expect(await report.text()).toContain('sh:ValidationReport');
});
