import { expect, test } from '@playwright/test';

async function openPovodyr(page) {
  await page.goto('/?q=поводир');
  await page.locator('.catalog-grid').getByRole('link', { name: /Поводир/ }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Поводир' })).toBeVisible();
}

function participants(page) {
  return page.locator('section').filter({ has: page.getByRole('heading', { name: 'Учасники' }) });
}

test('5. Переглянути картку фільму (UC4)', async ({ page }) => {
  await openPovodyr(page);
  await expect(page).toHaveURL(/\/films\/Q1004$/);
  await expect(page.getByText('2014 · 122 хв')).toBeVisible();
  await expect(page.locator('.film-genres')).toHaveText(/драма.*історичний фільм/);
  await expect(page.getByText('Кінопремія «Золота дзиґа»')).toBeVisible();
  const table = participants(page);
  await expect(table.getByRole('link', { name: /Олесь Санін/ })).toHaveCount(2);
  await expect(table.getByRole('link', { name: /Алла Загайкевич/ })).toBeVisible();
  await expect(table.getByText('У відкритих даних не вказано')).toBeVisible();
});

test("6. Переглянути пов'язані фільми (UC5)", async ({ page }) => {
  await openPovodyr(page);
  const related = page.locator('section.related');
  await expect(related.getByRole('link').first()).toContainText('Мамай');
  await expect(related.getByRole('link').first()).toContainText('Спільних учасників: 2');
  await expect(related.getByText('Спільний жанр').first()).toBeVisible();
  await related.getByRole('link').first().click();
  await expect(page.getByRole('heading', { level: 1, name: 'Мамай' })).toBeVisible();
});

test('7. Перейти до запису у Wikidata (UC12)', async ({ page }) => {
  await openPovodyr(page);
  const record = page.getByRole('link', { name: 'Запис у Wikidata' }).filter({ visible: true });
  await expect(record).toHaveAttribute('href', 'https://www.wikidata.org/wiki/Q1004');
  await expect(record).toHaveAttribute('target', '_blank');
  await expect(
    participants(page).getByRole('link', { name: 'Доповнити у Wikidata ↗' }),
  ).toHaveAttribute('href', 'https://www.wikidata.org/wiki/Q1004');

  await page.goto('/people/Q2002');
  await expect(
    page.getByRole('link', { name: 'Запис у Wikidata' }).filter({ visible: true }),
  ).toHaveAttribute('href', 'https://www.wikidata.org/wiki/Q2002');
});

test('8. Переглянути сторінку персоналії (UC6)', async ({ page }) => {
  await openPovodyr(page);
  await participants(page).getByRole('link', { name: /Олесь Санін/ }).first().click();
  await expect(page.getByRole('heading', { level: 1, name: 'Олесь Санін' })).toBeVisible();
  const crumbs = page.getByRole('navigation', { name: 'Навігаційний шлях' });
  await expect(crumbs.getByRole('link', { name: 'Поводир' })).toHaveAttribute('href', '/films/Q1004');
  await expect(page.getByText('2 фільми у довіднику')).toBeVisible();
  const rows = page.getByRole('table').getByRole('row');
  await expect(rows).toHaveText([/Рік.*Назва.*Роль/, /2014.*Поводир.*режисер, сценарист/, /2003.*Мамай.*режисер, сценарист/]);
  const collaborators = page.locator('section.collaborators');
  await expect(collaborators).toContainText('Спільних фільмів: 2');
  await collaborators.getByRole('link', { name: /Алла Загайкевич/ }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Алла Загайкевич' })).toBeVisible();
});
