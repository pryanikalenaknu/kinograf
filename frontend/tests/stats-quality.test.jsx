import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { SANIN, mockApi, person } from './fixtures.js';
import { renderApp } from './utils.jsx';

vi.mock('../src/components/ChartCanvas.jsx', () => ({
  ChartCanvas: ({ config, label }) => (
    <figure aria-label={label}>
      {config.data.datasets.map((dataset, index) => (
        <span key={index} data-testid="dataset">
          {dataset.label ?? 'дані'}: {config.data.labels.join(',')} = {dataset.data.join(',')}
        </span>
      ))}
    </figure>
  ),
}));

const STATS = {
  films_by_year: { 2003: 1, 2014: 2, 2019: 1 },
  genres_by_period: {
    '1991-2013': { драма: 1, 'історичний фільм': 1 },
    '2014-now': { драма: 3, 'документальний фільм': 1 },
  },
  top_directors: [
    { person: SANIN, films: 2 },
    { person: person('Q12', 'Валентин Васянович'), films: 1 },
  ],
  top_actors: [{ person: person('Q13', 'Андрій Римарук'), films: 2 }],
  completeness: { director: 0.75, cast: 0.5, genre: 1, poster: 0.25 },
  completeness_by_year: {
    2003: { director: 1, cast: 0, genre: 1, poster: 0 },
    2014: { director: 0.5, cast: 0.5, genre: 1, poster: 0.5 },
    2019: { director: 1, cast: 1, genre: 1, poster: 0 },
  },
  last_updated: '2026-10-20T00:00:00+00:00',
};

describe('статистика', () => {
  it('будує діаграму фільмів за роками', async () => {
    mockApi({ '/stats': STATS });
    renderApp('/stats');
    const chart = await screen.findByRole('figure', { name: /кількості фільмів за роками/ });
    expect(chart).toHaveTextContent('дані: 2003,2014,2019 = 1,2,1');
    expect(screen.getByText('2003–2019 · наведіть на стовпчик')).toBeInTheDocument();
  });

  it('порівнює жанри у двох періодах', async () => {
    mockApi({ '/stats': STATS });
    renderApp('/stats');
    const chart = await screen.findByRole('figure', { name: /жанрів у періодах/ });
    const [before, after] = within(chart).getAllByTestId('dataset');
    expect(before).toHaveTextContent(
      '1991–2013: драма,історичний фільм,документальний фільм = 1,1,0',
    );
    expect(after).toHaveTextContent('2014 — дотепер: драма,історичний фільм,документальний фільм = 3,0,1');
  });

  it('показує рейтинги режисерів і акторів з посиланнями', async () => {
    mockApi({ '/stats': STATS });
    renderApp('/stats');
    const directors = (await screen.findByRole('heading', { name: 'Топ-10 режисерів' })).closest(
      'section',
    );
    expect(within(directors).getByRole('link', { name: '1. Олесь Санін' })).toHaveAttribute(
      'href',
      '/people/Q11',
    );
    const actors = screen.getByRole('heading', { name: 'Топ-10 акторів' }).closest('section');
    expect(within(actors).getByText('1. Андрій Римарук')).toBeInTheDocument();
  });

  it('перемикає рейтинги вкладками на телефоні', async () => {
    mockApi({ '/stats': STATS });
    renderApp('/stats');
    const tabs = await screen.findByRole('tablist');
    await userEvent.click(within(tabs).getByRole('tab', { name: 'Топ-10 акторів' }));
    expect(within(tabs).getByRole('tab', { name: 'Топ-10 акторів' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(screen.getAllByText('1. Андрій Римарук')).toHaveLength(2);
  });

  it('повідомляє, що даних ще немає', async () => {
    mockApi({ '/stats': { ...STATS, films_by_year: {} } });
    renderApp('/stats');
    expect(await screen.findByRole('heading', { name: 'Немає даних' })).toBeInTheDocument();
  });
});

describe('якість даних', () => {
  it('показує картки-показники з часткою й кількістю', async () => {
    mockApi({ '/stats': STATS });
    renderApp('/quality');
    expect(await screen.findByText('Усього фільмів')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('3 з 4')).toBeInTheDocument();
    expect(screen.getByText('25%')).toBeInTheDocument();
    expect(screen.getByText(/^Дані оновлено: 20\.10\.2026/)).toBeInTheDocument();
  });

  it('будує лінії повноти за роками', async () => {
    mockApi({ '/stats': STATS });
    renderApp('/quality');
    const chart = await screen.findByRole('figure', { name: /частки фільмів із режисером/ });
    const [director, cast] = within(chart).getAllByTestId('dataset');
    expect(director).toHaveTextContent('з режисером: 2003,2014,2019 = 1,0.5,1');
    expect(cast).toHaveTextContent('з акторами: 2003,2014,2019 = 0,0.5,1');
  });

  it('для адміністратора веде до журналу оновлень', async () => {
    mockApi({ '/stats': { ...STATS, last_updated: null }, '/admin/log': [] });
    renderApp('/quality', { adminKey: 'secret' });
    expect(await screen.findByText('Дані ще не оновлювалися')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Журнал оновлень →' })).toHaveAttribute(
      'href',
      '/admin',
    );
  });

  it('показує помилку завантаження', async () => {
    mockApi({ '/stats': { status: 503, body: { detail: 'недоступно' } } });
    renderApp('/quality');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
