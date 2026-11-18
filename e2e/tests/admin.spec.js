import { expect, test } from '@playwright/test';

const KEY = 'e2e-key';

async function login(page, key = KEY) {
  await page.goto('/');
  await page.getByRole('link', { name: 'Вхід для адміністратора' }).click();
  await page.getByLabel('Ключ доступу').fill(key);
  await page.getByRole('button', { name: 'Увійти' }).click();
}

test('13. Оновити дані з Wikidata (UC13, UC15)', async ({ page }) => {
  await login(page);
  await expect(page.getByRole('heading', { name: 'Адміністрування' })).toBeVisible();
  await expect(page.getByText('Адміністратор', { exact: true })).toBeVisible();
  const state = page.getByRole('region', { name: 'Стан даних' });
  await expect(state).toContainText('Фільмів14');
  await expect(state).toContainText('Персоналій14');

  await page.getByRole('button', { name: 'Оновити дані з Wikidata' }).click();
  const confirm = page.getByRole('alertdialog', { name: 'Оновити дані з Wikidata?' });
  await confirm.getByRole('button', { name: 'Оновити' }).click();
  const progress = page.getByRole('region', { name: 'Перебіг оновлення' });
  await expect(progress).toBeVisible();
  await expect(progress.getByText('Оновлення завершено')).toBeVisible({ timeout: 15_000 });
  await expect(progress.getByText('100%')).toBeVisible();
  await expect(progress.getByText('Додано 0, змінено 0')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Оновити дані з Wikidata' })).toBeEnabled();
});

test('14. Переглянути журнал оновлень (UC14, UC15)', async ({ page }) => {
  await page.goto('/admin');
  await expect(page.getByRole('heading', { name: 'Вхід для адміністратора' })).toBeVisible();
  await page.getByLabel('Ключ доступу').fill('wrong-key');
  await page.getByRole('button', { name: 'Увійти' }).click();
  await expect(page.getByRole('alert')).toHaveText('Неправильний ключ доступу');

  await page.getByLabel('Ключ доступу').fill(KEY);
  await page.getByRole('button', { name: 'Увійти' }).click();
  const journal = page.locator('section.journal');
  const rows = journal.getByRole('table').getByRole('row');
  const initialLoad = rows.last();
  await expect(initialLoad).toContainText('успішно');
  await expect(initialLoad.getByRole('cell').nth(2)).toHaveText('14');

  await initialLoad.click();
  const details = page.getByRole('dialog');
  await expect(details.getByRole('heading', { name: /^Оновлення / })).toBeVisible();
  await expect(details.getByRole('listitem')).toHaveText([/Фільми\s*готово/, /Учасники\s*готово/, /Жанри\s*готово/, /Нагороди\s*готово/, /Запис у сховище\s*готово/]);
  await details.getByRole('button', { name: 'Закрити' }).click();

  await page.getByRole('button', { name: 'Вийти' }).click();
  await expect(page.getByRole('link', { name: 'Вхід для адміністратора' })).toBeVisible();
  await page.goto('/admin');
  await expect(page.getByRole('heading', { name: 'Вхід для адміністратора' })).toBeVisible();
});
