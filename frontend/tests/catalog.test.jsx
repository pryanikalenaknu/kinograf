import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { saveFile } from '../src/components/download.js';
import { DRAMA, MAMAI, POVODYR, SANIN, mockApi, requestedPaths } from './fixtures.js';
import { renderApp } from './utils.jsx';

vi.mock('../src/components/download.js', () => ({ saveFile: vi.fn() }));

function page(items, total = items.length, number = 1) {
  return { items, total, page: number };
}

const ITEMS = [
  { film: POVODYR, directors: [SANIN], genres: [DRAMA] },
  { film: MAMAI, directors: [SANIN], genres: [] },
];

function catalogApi(films = () => page(ITEMS)) {
  return mockApi({
    '/films': films,
    '/genres': [DRAMA],
    '/directors': [SANIN],
  });
}

function lastExportRequest(fetchMock) {
  return requestedPaths(fetchMock)
    .filter((url) => url.startsWith('/api/export'))
    .at(-1);
}

function lastFilmsRequest(fetchMock) {
  return requestedPaths(fetchMock)
    .filter((url) => url.startsWith('/api/films'))
    .at(-1);
}

describe('каталог', () => {
  it('показує картки з роком, режисером і жанрами', async () => {
    catalogApi();
    renderApp('/');
    const card = (await screen.findByText('Поводир', { selector: '.film-card-title' })).closest(
      'a',
    );
    expect(card).toHaveAttribute('href', '/films/Q4');
    expect(within(card).getByText('Олесь Санін')).toBeInTheDocument();
    expect(within(card).getByText('драма')).toBeInTheDocument();
    expect(screen.getAllByText('Знайдено: 2 фільми')[0]).toBeInTheDocument();
  });

  it('шукає за назвою із затримкою', async () => {
    const fetchMock = catalogApi();
    renderApp('/');
    await screen.findAllByText('Поводир');
    await userEvent.type(screen.getByRole('searchbox'), 'мамай');
    await waitFor(() =>
      expect(lastFilmsRequest(fetchMock)).toBe(
        '/api/films?q=%D0%BC%D0%B0%D0%BC%D0%B0%D0%B9&sort=year&page=1',
      ),
    );
  });

  it('застосовує й поєднує фільтри', async () => {
    const fetchMock = catalogApi();
    renderApp('/');
    const filters = await screen.findByRole('complementary', { name: 'Фільтри' });
    await userEvent.click(within(filters).getByRole('button', { name: '2014 — дотепер' }));
    await userEvent.selectOptions(within(filters).getByRole('combobox', { name: 'Жанр' }), 'Q130232');
    await userEvent.click(within(filters).getByRole('checkbox', { name: 'Лише з акторами' }));
    await waitFor(() =>
      expect(lastFilmsRequest(fetchMock)).toBe(
        '/api/films?period=2014-now&genre=Q130232&has_cast=true&sort=year&page=1',
      ),
    );
    await userEvent.click(within(filters).getByRole('button', { name: 'Скинути фільтри' }));
    await waitFor(() => expect(lastFilmsRequest(fetchMock)).toBe('/api/films?sort=year&page=1'));
  });

  it('змінює сортування', async () => {
    const fetchMock = catalogApi();
    renderApp('/');
    await screen.findAllByText('Поводир');
    const sorting = screen.getByRole('group', { name: 'Сортування' });
    await userEvent.click(within(sorting).getByRole('button', { name: 'За назвою' }));
    await waitFor(() => expect(lastFilmsRequest(fetchMock)).toBe('/api/films?sort=title&page=1'));
    expect(within(sorting).getByRole('button', { name: 'За назвою' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('гортає сторінки', async () => {
    const fetchMock = catalogApi((path) => page(ITEMS, 30, path.includes('page=2') ? 2 : 1));
    renderApp('/');
    const pagination = await screen.findByRole('navigation', { name: 'Пагінація' });
    expect(within(pagination).getByRole('button', { name: '3' })).toBeInTheDocument();
    await userEvent.click(within(pagination).getByRole('button', { name: 'Наступна сторінка' }));
    await waitFor(() => expect(lastFilmsRequest(fetchMock)).toBe('/api/films?sort=year&page=2'));
  });

  it('повідомляє, що нічого не знайдено', async () => {
    catalogApi(() => page([]));
    renderApp('/?q=nema');
    expect(await screen.findByRole('heading', { name: 'Нічого не знайдено' })).toBeInTheDocument();
  });

  it('показує помилку й повторює запит', async () => {
    let calls = 0;
    catalogApi(() => {
      calls += 1;
      return calls === 1 ? { status: 500, body: { detail: 'збій' } } : page(ITEMS);
    });
    renderApp('/');
    await userEvent.click(await screen.findByRole('button', { name: 'Спробувати ще раз' }));
    expect(await screen.findAllByText('Поводир')).not.toHaveLength(0);
  });

  it('експортує результати з поточними фільтрами', async () => {
    const fetchMock = catalogApi();
    fetchMock.mockImplementation(async (url) => {
      if (url.startsWith('/api/export/films')) {
        return new Response('{}', { status: 200 });
      }
      if (url.startsWith('/api/films')) {
        return new Response(JSON.stringify(page(ITEMS)), { status: 200 });
      }
      return new Response('[]', { status: 200 });
    });
    renderApp('/?genre=Q130232');
    await screen.findAllByText('Поводир');
    await userEvent.click(screen.getAllByRole('button', { name: 'Експорт' })[0]);
    const dialog = screen.getByRole('dialog', { name: 'Експорт каталогу · 2 фільми' });
    await userEvent.click(within(dialog).getByRole('radio', { name: /JSON/ }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Завантажити' }));
    await waitFor(() => expect(saveFile).toHaveBeenCalledWith(expect.any(Blob), 'films.json'));
    expect(lastExportRequest(fetchMock)).toBe('/api/export/films?genre=Q130232&sort=year&format=json');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('показує помилку експорту замість збереження файлу з помилкою', async () => {
    const fetchMock = catalogApi();
    fetchMock.mockImplementation(async (url) => {
      if (url.startsWith('/api/export/films')) {
        return new Response(JSON.stringify({ detail: 'сервер перевантажено' }), { status: 503 });
      }
      return new Response(JSON.stringify(url.startsWith('/api/films') ? page(ITEMS) : []), {
        status: 200,
      });
    });
    renderApp('/');
    await screen.findAllByText('Поводир');
    await userEvent.click(screen.getAllByRole('button', { name: 'Експорт' })[0]);
    await userEvent.click(screen.getByRole('button', { name: 'Завантажити' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('сервер перевантажено');
    expect(saveFile).not.toHaveBeenCalled();
  });

  it('переводить на останню сторінку, якщо номер завеликий', async () => {
    const fetchMock = catalogApi((path) => page(path.includes('page=2') ? ITEMS : [], 14, 2));
    renderApp('/?page=99');
    await waitFor(() => expect(lastFilmsRequest(fetchMock)).toBe('/api/films?sort=year&page=2'));
    expect(await screen.findAllByText('Поводир')).not.toHaveLength(0);
  });

  it('ігнорує нечислові роки в адресі', async () => {
    const fetchMock = catalogApi();
    renderApp('/?year_from=abc&year_to=2014');
    await waitFor(() =>
      expect(lastFilmsRequest(fetchMock)).toBe('/api/films?year_to=2014&sort=year&page=1'),
    );
  });

  it('переводить фокус у діалог експорту й повертає його після закриття', async () => {
    catalogApi();
    renderApp('/');
    await screen.findAllByText('Поводир');
    const button = screen.getAllByRole('button', { name: 'Експорт' })[0];
    await userEvent.click(button);
    expect(screen.getByRole('radio', { name: /CSV/ })).toHaveFocus();
    await userEvent.keyboard('{Escape}');
    expect(button).toHaveFocus();
  });
});

describe('каталог на телефоні', () => {
  function asPhone() {
    vi.spyOn(window, 'matchMedia').mockImplementation((query) => ({
      matches: true,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    }));
  }

  it('відкриває шторку фільтрів і показує кількість знайдених фільмів', async () => {
    asPhone();
    catalogApi();
    renderApp('/?period=2014-now');
    await userEvent.click(await screen.findByRole('button', { name: 'Фільтри (1)' }));
    const sheet = screen.getByRole('dialog', { name: 'Фільтри (1)' });
    await userEvent.click(within(sheet).getByRole('button', { name: 'Показати 2 фільми' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('довантажує наступну сторінку кнопкою «Показати ще»', async () => {
    asPhone();
    const second = [{ film: { ...MAMAI, qid: 'Q30', title: 'Кіборги' }, directors: [], genres: [] }];
    catalogApi((path) => (path.includes('page=2') ? page(second, 14, 2) : page(ITEMS, 14)));
    renderApp('/');
    await userEvent.click(await screen.findByRole('button', { name: 'Показати ще' }));
    expect(await screen.findByText('Кіборги', { selector: '.film-card-title' })).toBeInTheDocument();
    expect(screen.getByText('Поводир', { selector: '.film-card-title' })).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Пагінація' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Показати ще' })).not.toBeInTheDocument();
  });
});

describe('швидкі зміни фільтрів', () => {
  it('скидання й новий фільтр одразу після нього не накладаються на старі фільтри', async () => {
    const fetchMock = catalogApi();
    renderApp('/?period=2014-now&genre=Q130232&has_cast=true');
    const filters = await screen.findByRole('complementary', { name: 'Фільтри' });
    await screen.findAllByText('Поводир');
    act(() => {
      within(filters).getByRole('button', { name: 'Скинути фільтри' }).click();
      fireEvent.change(within(filters).getByRole('combobox', { name: 'Режисер' }), {
        target: { value: 'Q11' },
      });
    });
    await waitFor(() =>
      expect(lastFilmsRequest(fetchMock)).toBe('/api/films?director=Q11&sort=year&page=1'),
    );
  });
});
