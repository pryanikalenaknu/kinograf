import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';

function cards(page) {
  return page.locator('.catalog-grid').getByRole('link');
}

function count(page) {
  return page.locator('.catalog-count').filter({ visible: true });
}

test('1. Переглянути каталог фільмів (UC1)', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Каталог фільмів' })).toBeVisible();
  await expect(count(page)).toHaveText('Знайдено: 14 фільмів');
  await expect(cards(page)).toHaveCount(12);
  await expect(cards(page).first()).toContainText('Памфір');

  const pagination = page.getByRole('navigation', { name: 'Пагінація' });
  await pagination.getByRole('button', { name: '2' }).click();
  await expect(page).toHaveURL(/page=2/);
  await expect(cards(page)).toHaveCount(2);

  await page.goto('/');
  await page.getByRole('group', { name: 'Сортування' }).getByRole('button', { name: 'За назвою' }).click();
  await expect(cards(page).first()).toContainText('Атлантида');
});

test('2. Шукати фільм за назвою (UC2)', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('searchbox', { name: 'Пошук за назвою фільму' }).fill('плем');
  await expect(page).toHaveURL(/q=/);
  await expect(cards(page)).toHaveCount(1);
  await expect(cards(page).first()).toContainText("Плем'я");
  await expect(count(page)).toHaveText('Знайдено: 1 фільм');

  await page.getByRole('searchbox', { name: 'Пошук за назвою фільму' }).fill('неіснуючий фільм');
  await expect(page.getByRole('heading', { name: 'Нічого не знайдено' })).toBeVisible();
  await page.getByRole('button', { name: 'Скинути фільтри' }).last().click();
  await expect(count(page)).toHaveText('Знайдено: 14 фільмів');
});

test('3. Фільтрувати фільми (UC3)', async ({ page }) => {
  await page.goto('/');
  const filters = page.getByRole('complementary', { name: 'Фільтри' });
  await filters.getByRole('button', { name: '2014 — дотепер' }).click();
  await filters.getByLabel('Жанр').selectOption({ label: 'драма' });
  await filters.getByRole('checkbox', { name: 'Лише з акторами' }).click();
  await expect(filters.getByRole('checkbox', { name: 'Лише з акторами' })).toBeChecked();
  await expect(count(page)).toHaveText('Знайдено: 4 фільми');
  await expect(cards(page)).toHaveText([/Відблиск/, /Атлантида/, /Додому/, /Плем'я/]);

  await filters.getByRole('button', { name: 'Скинути фільтри' }).click();
  await filters.getByLabel('Режисер').selectOption({ label: 'Олесь Санін' });
  await expect(cards(page)).toHaveText([/Поводир/, /Мамай/]);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Фільтри', exact: true }).click();
  const sheet = page.getByRole('dialog');
  await sheet.getByRole('button', { name: '1991–2013' }).click();
  await sheet.getByRole('button', { name: 'Показати 2 фільми' }).click();
  await expect(sheet).toBeHidden();
  await expect(page.getByRole('button', { name: 'Фільтри (1)' })).toBeVisible();
  await expect(cards(page)).toHaveText([/Мамай/, /Їжак/]);
});

test('4. Експортувати результати (UC11)', async ({ page }) => {
  await page.goto('/?genre=Q130232&sort=title');
  await expect(count(page)).toHaveText('Знайдено: 11 фільмів');
  await page.getByRole('button', { name: 'Експорт' }).filter({ visible: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Експорт каталогу · 11 фільмів' });
  const csvDownload = page.waitForEvent('download');
  await dialog.getByRole('button', { name: 'Завантажити' }).click();
  const csv = await csvDownload;
  expect(csv.suggestedFilename()).toBe('films.csv');
  const table = await readFile(await csv.path(), 'utf-8');
  const lines = table.replace(/^﻿/, '').trim().split(/\r?\n/);
  expect(lines[0]).toBe('qid,title,year,release_date,duration_min,image_url,wikidata_url');
  expect(lines).toHaveLength(12);
  expect(lines[1]).toContain('Атлантида');

  await page.goto('/sparql');
  await page.getByRole('button', { name: 'Виконати' }).click();
  await page.getByRole('region', { name: 'Результати' }).getByRole('button', { name: 'Експорт' }).click();
  await page.getByRole('dialog').getByText('JSON', { exact: true }).click();
  await expect(page.getByRole('radio', { name: /JSON/ })).toBeChecked();
  const jsonDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Завантажити' }).click();
  const json = await jsonDownload;
  expect(json.suggestedFilename()).toBe('sparql.json');
  const rows = JSON.parse(await readFile(await json.path(), 'utf-8'));
  expect(rows).toHaveLength(11);
  expect(rows[0]).toHaveProperty('filmLabel');
});
