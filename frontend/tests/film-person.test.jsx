import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DRAMA, MAMAI, POVODYR, SANIN, ZAHAIKEVYCH, film, mockApi } from './fixtures.js';
import { renderApp } from './utils.jsx';

const DETAILS = {
  film: POVODYR,
  participants: { director: [SANIN], screenwriter: [SANIN], composer: [ZAHAIKEVYCH], cast: [] },
  genres: [DRAMA, { qid: 'Q17013749', name: 'історичний' }],
  awards: [{ qid: 'Q100', name: 'Кінопремія «Золота дзиґа»' }],
  related: [
    { film: MAMAI, shared_people: 2, shared_genres: 1 },
    { film: film('Q5', 'Атлантида', 2019), shared_people: 0, shared_genres: 1 },
  ],
};

const PROFILE = {
  person: SANIN,
  filmography: [
    { film: POVODYR, roles: ['director', 'screenwriter'] },
    { film: MAMAI, roles: ['director', 'screenwriter'] },
  ],
  collaborators: [{ person: ZAHAIKEVYCH, films: 2 }],
};

describe('картка фільму', () => {
  it('показує дані фільму, учасників за ролями й нагороди', async () => {
    mockApi({ '/films/Q4': DETAILS });
    renderApp('/films/Q4');
    expect(await screen.findByRole('heading', { level: 1, name: 'Поводир' })).toBeInTheDocument();
    expect(screen.getByText('2014 · 122 хв')).toBeInTheDocument();
    expect(screen.getByText('історичний')).toBeInTheDocument();
    expect(screen.getByText('Кінопремія «Золота дзиґа»')).toBeInTheDocument();
    const table = screen.getByRole('heading', { name: 'Учасники' }).closest('section');
    expect(within(table).getAllByRole('link', { name: /Олесь Санін/ })).toHaveLength(2);
    expect(within(table).getByRole('link', { name: /Алла Загайкевич/ })).toHaveAttribute(
      'href',
      '/people/Q14',
    );
  });

  it('позначає відсутні дані й веде до Wikidata', async () => {
    mockApi({ '/films/Q4': DETAILS });
    renderApp('/films/Q4');
    const table = (await screen.findByRole('heading', { name: 'Учасники' })).closest('section');
    expect(within(table).getByText('У відкритих даних не вказано')).toBeInTheDocument();
    expect(within(table).getByRole('link', { name: 'Доповнити у Wikidata ↗' })).toHaveAttribute(
      'href',
      'https://www.wikidata.org/wiki/Q4',
    );
  });

  it('показує пов\'язані фільми з причиною зв\'язку', async () => {
    mockApi({ '/films/Q4': DETAILS });
    renderApp('/films/Q4');
    const related = (await screen.findByRole('heading', { name: "Пов'язані фільми" })).closest(
      'section',
    );
    const links = within(related).getAllByRole('link');
    expect(links.map((link) => link.getAttribute('href'))).toEqual(['/films/Q3', '/films/Q5']);
    expect(within(related).getByText('Спільних учасників: 2')).toBeInTheDocument();
    expect(within(related).getByText('Спільний жанр')).toBeInTheDocument();
  });

  it('веде до графа зв\'язків і запису у Wikidata', async () => {
    mockApi({ '/films/Q4': DETAILS });
    renderApp('/films/Q4');
    await screen.findByRole('heading', { level: 1, name: 'Поводир' });
    expect(screen.getAllByRole('link', { name: "Граф зв'язків" })[0]).toHaveAttribute(
      'href',
      '/graph/Q4',
    );
    expect(screen.getAllByRole('link', { name: 'Запис у Wikidata' })[0]).toHaveAttribute(
      'href',
      'https://www.wikidata.org/wiki/Q4',
    );
  });

  it('розгортає й згортає ролі в акордеоні на телефоні', async () => {
    mockApi({ '/films/Q4': DETAILS });
    renderApp('/films/Q4');
    const director = await screen.findByRole('button', { name: /Режисер/ });
    const writer = screen.getByRole('button', { name: /Сценарист/ });
    expect(director).toHaveAttribute('aria-expanded', 'true');
    expect(writer).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('button', { name: /Актори/ })).toHaveAttribute('aria-expanded', 'true');
    await userEvent.click(writer);
    expect(writer).toHaveAttribute('aria-expanded', 'true');
    await userEvent.click(director);
    expect(director).toHaveAttribute('aria-expanded', 'false');
  });

  it('повідомляє, що фільму немає', async () => {
    mockApi({});
    renderApp('/films/Q999');
    expect(await screen.findByRole('heading', { name: 'Не знайдено' })).toBeInTheDocument();
  });

  it('показує помилку сервера з повтором', async () => {
    mockApi({ '/films/Q4': { status: 500, body: { detail: 'збій' } } });
    renderApp('/films/Q4');
    expect(await screen.findByRole('alert')).toHaveTextContent('Не вдалося завантажити дані');
  });
});

describe('сторінка персоналії', () => {
  it('показує ролі, кількість фільмів, фільмографію й співробітників', async () => {
    mockApi({ '/people/Q11': PROFILE });
    renderApp('/people/Q11');
    expect(await screen.findByRole('heading', { level: 1, name: 'Олесь Санін' })).toBeInTheDocument();
    expect(screen.getAllByText('2 фільми у довіднику')[0]).toBeInTheDocument();
    const table = screen.getByRole('table');
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      '2014Поводиррежисер, сценарист',
      '2003Мамайрежисер, сценарист',
    ]);
    const collaborators = screen
      .getByRole('heading', { name: 'Постійні співробітники' })
      .closest('section');
    expect(within(collaborators).getByText('Спільних фільмів: 2')).toBeInTheDocument();
    expect(within(collaborators).getByRole('link')).toHaveAttribute('href', '/people/Q14');
  });

  it('показує хронологію за роками', async () => {
    mockApi({ '/people/Q11': PROFILE, '/films/Q4': DETAILS });
    renderApp('/people/Q11');
    const timeline = (await screen.findByRole('heading', { name: 'Хронологія' })).closest('section');
    expect(within(timeline).getAllByRole('button', { name: 'Мамай, 2003' })).not.toHaveLength(0);
    await userEvent.click(within(timeline).getAllByRole('button', { name: 'Поводир, 2014' })[0]);
    expect(await screen.findByRole('heading', { level: 1, name: 'Поводир' })).toBeInTheDocument();
  });

  it('додає фільм, з якого прийшов користувач, до навігаційного шляху', async () => {
    mockApi({ '/films/Q4': DETAILS, '/people/Q11': PROFILE });
    renderApp('/films/Q4');
    const table = (await screen.findByRole('heading', { name: 'Учасники' })).closest('section');
    await userEvent.click(within(table).getAllByRole('link', { name: /Олесь Санін/ })[0]);
    const crumbs = await screen.findByRole('navigation', { name: 'Навігаційний шлях' });
    expect(within(crumbs).getByRole('link', { name: 'Поводир' })).toHaveAttribute(
      'href',
      '/films/Q4',
    );
    expect(within(crumbs).getByText('Олесь Санін')).toBeInTheDocument();
  });

  it('повідомляє, що персоналії немає', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    mockApi({});
    renderApp('/people/Q999');
    expect(await screen.findByRole('heading', { name: 'Не знайдено' })).toBeInTheDocument();
  });
});
