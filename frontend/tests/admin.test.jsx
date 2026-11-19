import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ADMIN_STORAGE_KEY } from '../src/api/admin.js';
import { mockApi } from './fixtures.js';
import { renderApp } from './utils.jsx';

const STATS = {
  totals: { films: 1403, people: 4812 },
  last_updated: '2026-10-20T00:00:00+00:00',
};

function log(id, status, extra = {}) {
  return {
    id,
    started_at: `2026-10-${String(id).padStart(2, '0')}T00:00:00+00:00`,
    finished_at: status === 'running' ? null : `2026-10-${String(id).padStart(2, '0')}T00:02:14+00:00`,
    status,
    films_added: 0,
    films_changed: 0,
    message: '',
    stage: 'storage',
    ...extra,
  };
}

const HISTORY = [
  log(20, 'success', { films_added: 12, films_changed: 37 }),
  log(6, 'error', { stage: 'participations', message: 'Wikidata не відповідає після 3 спроб' }),
];

describe('вхід адміністратора', () => {
  it('перевіряє ключ на сервері й відкриває панель', async () => {
    const fetchMock = mockApi({ '/admin/log': HISTORY, '/stats': STATS });
    renderApp('/admin/login');
    await userEvent.type(screen.getByLabelText('Ключ доступу'), 'secret');
    await userEvent.click(screen.getByRole('button', { name: 'Увійти' }));
    expect(await screen.findByRole('heading', { name: 'Адміністрування' })).toBeInTheDocument();
    expect(sessionStorage.getItem(ADMIN_STORAGE_KEY)).toBe('secret');
    expect(fetchMock.mock.calls[0][1].headers['X-Admin-Key']).toBe('secret');
  });

  it('повідомляє про неправильний ключ', async () => {
    mockApi({ '/admin/log': { status: 401, body: { detail: 'неправильний ключ' } } });
    renderApp('/admin/login');
    await userEvent.type(screen.getByLabelText('Ключ доступу'), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: 'Увійти' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Неправильний ключ доступу');
    expect(screen.getByLabelText('Ключ доступу')).toHaveAttribute('aria-invalid', 'true');
    expect(sessionStorage.getItem(ADMIN_STORAGE_KEY)).toBeNull();
  });

  it('вимагає ключ і показує недоступність сервера', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'));
    renderApp('/admin/login');
    await userEvent.click(screen.getByRole('button', { name: 'Увійти' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Введіть ключ доступу');
    await userEvent.type(screen.getByLabelText('Ключ доступу'), 'secret');
    await userEvent.click(screen.getByRole('button', { name: 'Увійти' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Сервер недоступний');
  });

  it('показує й ховає ключ', async () => {
    renderApp('/admin/login');
    const input = screen.getByLabelText('Ключ доступу');
    expect(input).toHaveAttribute('type', 'password');
    await userEvent.click(screen.getByRole('button', { name: 'Показати' }));
    expect(input).toHaveAttribute('type', 'text');
    await userEvent.click(screen.getByRole('button', { name: 'Сховати' }));
    expect(input).toHaveAttribute('type', 'password');
  });
});

describe('панель адміністрування', () => {
  it('показує стан даних і журнал', async () => {
    mockApi({ '/admin/log': HISTORY, '/stats': STATS });
    renderApp('/admin', { adminKey: 'secret' });
    const state = await screen.findByRole('region', { name: 'Стан даних' });
    expect(within(state).getByText('1 403')).toBeInTheDocument();
    expect(within(state).getByText('4 812')).toBeInTheDocument();
    const table = await screen.findByRole('table');
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows[0]).toHaveTextContent('2 хв 14 с1237успішно');
    expect(rows[1]).toHaveTextContent('помилка');
  });

  it('сортує журнал за датою', async () => {
    mockApi({ '/admin/log': HISTORY, '/stats': STATS });
    renderApp('/admin', { adminKey: 'secret' });
    const table = await screen.findByRole('table');
    await userEvent.click(within(table).getByRole('button', { name: 'Сортування: спочатку нові' }));
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows[0]).toHaveTextContent('помилка');
  });

  it('відкриває подробиці запису журналу', async () => {
    mockApi({ '/admin/log': HISTORY, '/stats': STATS });
    renderApp('/admin', { adminKey: 'secret' });
    const table = await screen.findByRole('table');
    await userEvent.click(within(table).getAllByRole('row')[2]);
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText('Фільми').nextSibling).toHaveTextContent('готово');
    expect(within(dialog).getByText('Учасники').nextSibling).toHaveTextContent('помилка');
    expect(within(dialog).getByText('Жанри').nextSibling).toHaveTextContent('не виконано');
    expect(within(dialog).getByRole('alert')).toHaveTextContent('Wikidata не відповідає після 3 спроб');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Закрити' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('запускає оновлення після підтвердження й показує етапи до завершення', async () => {
    let finished = false;
    const fetchMock = mockApi({
      '/admin/log': () => (finished ? [log(27, 'success', { films_added: 3 }), ...HISTORY] : HISTORY),
      '/stats': STATS,
      '/admin/update/27': () => {
        finished = true;
        return log(27, 'success', { films_added: 3, films_changed: 1 });
      },
      '/admin/update': log(27, 'running', { stage: '' }),
    });
    renderApp('/admin', { adminKey: 'secret' });
    await userEvent.click(await screen.findByRole('button', { name: 'Оновити дані з Wikidata' }));
    const confirm = screen.getByRole('alertdialog', { name: 'Оновити дані з Wikidata?' });
    await userEvent.click(within(confirm).getByRole('button', { name: 'Оновити' }));
    const progress = await screen.findByRole('region', { name: 'Перебіг оновлення' });
    expect(within(progress).getByRole('heading')).toHaveTextContent('Оновлення виконується…');
    expect(within(progress).getByText('0%')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Оновити дані з Wikidata' })).toBeDisabled();
    expect(
      await within(progress).findByText('Додано 3, змінено 1', {}, { timeout: 3500 }),
    ).toBeInTheDocument();
    expect(within(progress).getByText('100%')).toBeInTheDocument();
    const start = fetchMock.mock.calls.find(([url]) => url === '/api/admin/update');
    expect(start[1].method).toBe('POST');
    await userEvent.click(within(progress).getByRole('button', { name: 'Закрити' }));
    expect(screen.queryByRole('region', { name: 'Перебіг оновлення' })).not.toBeInTheDocument();
  });

  it('показує етап, на якому оновлення зупинилося', async () => {
    mockApi({
      '/admin/log': HISTORY,
      '/stats': STATS,
      '/admin/update/27': log(27, 'error', { stage: 'genres', message: 'Wikidata не відповідає' }),
      '/admin/update': log(27, 'running', { stage: 'films' }),
    });
    renderApp('/admin', { adminKey: 'secret' });
    await userEvent.click(await screen.findByRole('button', { name: 'Оновити дані з Wikidata' }));
    await userEvent.click(screen.getByRole('button', { name: 'Оновити' }));
    const alert = await screen.findByRole('alert', {}, { timeout: 3500 });
    expect(alert).toHaveTextContent('Wikidata не відповідає');
    const progress = screen.getByRole('region', { name: 'Перебіг оновлення' });
    expect(within(progress).getByText('Оновлення зупинено')).toBeInTheDocument();
    expect(within(progress).getByText('25%')).toBeInTheDocument();
    expect(within(alert).getByRole('button', { name: 'Повторити' })).toBeInTheDocument();
  });

  it('повідомляє, що оновлення вже виконується', async () => {
    mockApi({
      '/admin/log': HISTORY,
      '/stats': STATS,
      '/admin/update': { status: 409, body: { detail: 'оновлення вже виконується' } },
    });
    renderApp('/admin', { adminKey: 'secret' });
    await userEvent.click(await screen.findByRole('button', { name: 'Оновити дані з Wikidata' }));
    await userEvent.click(screen.getByRole('button', { name: 'Оновити' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Оновлення вже виконується');
  });

  it('продовжує стежити за оновленням, що вже виконується', async () => {
    mockApi({
      '/admin/log': [log(27, 'running', { stage: 'awards' }), ...HISTORY],
      '/stats': STATS,
    });
    renderApp('/admin', { adminKey: 'secret' });
    const progress = await screen.findByRole('region', { name: 'Перебіг оновлення' });
    expect(within(progress).getByText('38%')).toBeInTheDocument();
    expect(within(progress).getByText('Нагороди').nextSibling).toHaveTextContent('виконується');
    const stages = within(progress)
      .getAllByRole('listitem')
      .map((item) => item.querySelector('.stage-text span').textContent);
    expect(stages).toEqual([
      'Фільми',
      'Учасники',
      'Жанри',
      'Нагороди',
      'Посилання',
      'Запис у сховище',
      'Публікація',
      'Перевірка якості',
    ]);
  });

  it('повертає на вхід, якщо ключ більше не діє', async () => {
    mockApi({ '/admin/log': { status: 401, body: { detail: 'неправильний ключ' } }, '/stats': STATS });
    renderApp('/admin', { adminKey: 'old' });
    expect(await screen.findByRole('heading', { name: 'Вхід для адміністратора' })).toBeInTheDocument();
    await waitFor(() => expect(sessionStorage.getItem(ADMIN_STORAGE_KEY)).toBeNull());
  });
});
