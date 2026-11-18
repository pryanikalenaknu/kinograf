import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { escapeXml, initials } from '../src/components/format.js';
import { personImage } from '../src/components/graphImages.js';
import { EXAMPLES } from '../src/components/sparql.js';
import { ADMIN_STORAGE_KEY } from '../src/api/admin.js';
import { mockApi, requestedPaths } from './fixtures.js';
import { renderApp } from './utils.jsx';

vi.mock('../src/pages/StatsPage.jsx', () => ({
  StatsPage: () => {
    throw new Error('збій відображення');
  },
}));

function decodeSvg(uri) {
  return decodeURIComponent(uri.slice(uri.indexOf(',') + 1));
}

describe('аватари вузлів графа', () => {
  it('не розриває символи поза базовою площиною', () => {
    expect(initials('𝕏 Artist')).toBe('𝕏A');
    expect(() => personImage('𝕏 Artist', '#1F77B4')).not.toThrow();
  });

  it('екранує спеціальні символи XML в імені', () => {
    expect(escapeXml('<a href="x">&\'')).toBe('&#60;a href=&#34;x&#34;&#62;&#38;&#39;');
    const svg = decodeSvg(personImage('Simon & Garfunkel', '#1F77B4'));
    expect(svg).toContain('>S&#38;</text>');
    const parsed = new DOMParser().parseFromString(svg, 'image/svg+xml');
    expect(parsed.querySelector('parsererror')).toBeNull();
    expect(parsed.querySelector('text').textContent).toBe('S&');
  });
});

describe('межа помилок', () => {
  it('показує повідомлення замість сторінки й залишає меню', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    renderApp('/stats');
    expect(await screen.findByRole('heading', { name: 'Сторінку не вдалося показати' })).toBeInTheDocument();
    expect(screen.getAllByRole('navigation', { name: 'Головне меню' })[0]).toBeInTheDocument();
  });
});

describe('гонки в SPARQL-консолі', () => {
  function deferred() {
    let resolve;
    const promise = new Promise((done) => {
      resolve = done;
    });
    return { promise, resolve };
  }

  const RESULT = { columns: ['x'], rows: [{ x: 'старий' }], truncated: false, elapsed_ms: 1 };

  it('не запускає другий запит, поки виконується перший', async () => {
    const pending = deferred();
    const fetchMock = mockApi({ '/sparql': () => pending.promise });
    renderApp('/sparql');
    const editor = screen.getByRole('textbox', { name: 'Текст SPARQL-запиту' });
    fireEvent.keyDown(editor, { key: 'Enter', ctrlKey: true });
    fireEvent.keyDown(editor, { key: 'Enter', ctrlKey: true });
    expect(requestedPaths(fetchMock).filter((url) => url === '/api/sparql')).toHaveLength(1);
    await act(async () => pending.resolve(RESULT));
  });

  it('не показує результат старого запиту після вибору іншого прикладу', async () => {
    const pending = deferred();
    mockApi({ '/sparql': () => pending.promise });
    renderApp('/sparql');
    await userEvent.click(screen.getByRole('button', { name: 'Виконати' }));
    await userEvent.click(
      screen.getByRole('button', { name: 'Режисери з найбільшою кількістю фільмів' }),
    );
    await act(async () => pending.resolve(RESULT));
    expect(screen.queryByText('старий')).not.toBeInTheDocument();
    expect(screen.getByText(/Оберіть приклад або напишіть запит/)).toBeInTheDocument();
  });

  it('експортує той запит, результат якого показано', async () => {
    const fetchMock = mockApi({ '/sparql': RESULT, '/export/sparql': {} });
    renderApp('/sparql');
    await userEvent.click(screen.getByRole('button', { name: 'Виконати' }));
    await screen.findByText('старий');
    fireEvent.change(screen.getByRole('textbox', { name: 'Текст SPARQL-запиту' }), {
      target: { value: 'SELECT ?y WHERE { ?y ?p ?o }' },
    });
    await userEvent.click(screen.getByRole('button', { name: 'Експорт' }));
    await userEvent.click(screen.getByRole('button', { name: 'Завантажити' }));
    const [, options] = fetchMock.mock.calls.find(([url]) => url === '/api/export/sparql');
    expect(JSON.parse(options.body).query).toBe(EXAMPLES[0].query);
  });
});

describe('адміністрування', () => {
  it('відхиляє ключ із недопустимими символами без запиту до сервера', async () => {
    const fetchMock = mockApi({});
    renderApp('/admin/login');
    await userEvent.type(screen.getByLabelText('Ключ доступу'), 'ключ');
    await userEvent.click(screen.getByRole('button', { name: 'Увійти' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Неправильний ключ доступу');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('повертає на вхід, якщо ключ перестав діяти під час оновлення', async () => {
    mockApi({
      '/stats': { totals: { films: 1, people: 1 }, last_updated: null },
      '/admin/log': [
        {
          id: 5,
          started_at: '2026-10-30T00:00:00+00:00',
          finished_at: null,
          status: 'running',
          films_added: 0,
          films_changed: 0,
          message: '',
          stage: 'films',
        },
      ],
      '/admin/update/5': { status: 401, body: { detail: 'неправильний ключ' } },
    });
    renderApp('/admin', { adminKey: 'old' });
    expect(
      await screen.findByRole('heading', { name: 'Вхід для адміністратора' }, { timeout: 3500 }),
    ).toBeInTheDocument();
    await waitFor(() => expect(sessionStorage.getItem(ADMIN_STORAGE_KEY)).toBeNull());
  });
});

describe('граф зв\'язків', () => {
  it('запитує дані вибраного вузла один раз', async () => {
    const fetchMock = mockApi({
      '/graph/Q4': {
        nodes: [{ id: 'Q4', label: 'Поводир', type: 'film', level: 0 }],
        edges: [],
      },
      '/films/Q4': {
        film: { qid: 'Q4', title: 'Поводир', year: 2014 },
        participants: { director: [], screenwriter: [], composer: [], cast: [] },
        genres: [],
        awards: [],
        related: [],
      },
    });
    renderApp('/graph/Q4');
    const search = await screen.findByRole('textbox', { name: 'Знайти вузол' });
    await userEvent.type(search, 'пов');
    await userEvent.click(within(screen.getByRole('listbox')).getByRole('option'));
    await screen.findByText("Зв'язків у графі: 0");
    expect(requestedPaths(fetchMock).filter((url) => url === '/api/films/Q4')).toHaveLength(1);
  });
});
