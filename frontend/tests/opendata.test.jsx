import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { POVODYR, SANIN, mockApi, requestedPaths } from './fixtures.js';
import { renderApp } from './utils.jsx';

const OVERVIEW = {
  base_url: 'http://localhost:8080',
  license: 'https://creativecommons.org/publicdomain/zero/1.0/',
  source: 'https://www.wikidata.org/',
  modified: '2026-10-20T00:00:00+00:00',
  triples: 34067,
  films: 1404,
  people: 2797,
  linksets: [
    { target: 'Wikidata', homepage: 'https://www.wikidata.org/', predicate: 'owl:sameAs', films: 1404, people: 2797 },
    { target: 'Вікіпедія (укр.)', homepage: 'https://uk.wikipedia.org/', predicate: 'schema:sameAs', films: 1012, people: 2104 },
    { target: 'IMDb', homepage: 'https://www.imdb.com/', predicate: 'schema:sameAs', films: 936, people: 1873 },
    { target: 'DBpedia', homepage: 'https://dbpedia.org/', predicate: 'owl:sameAs', films: 468, people: 1129 },
  ],
  endpoints: {
    void: 'http://localhost:8080/.well-known/void',
    dump: 'http://localhost:8080/data/kinograf.ttl',
    sparql: 'http://localhost:8080/data/sparql',
  },
  example_film: 'Q4',
};

const DETAILS = {
  film: { ...POVODYR, title: 'Поводир, або "квіти"', release_date: '2014-11-13' },
  participants: { director: [SANIN], screenwriter: [], composer: [], cast: [] },
  genres: [],
  awards: [],
  related: [],
};

describe('відкриті дані', () => {
  it('показує п\'ять зірок і опис набору', async () => {
    mockApi({ '/opendata': OVERVIEW, '/films/Q4': DETAILS });
    renderApp('/open-data');
    expect(await screen.findByRole('heading', { name: 'Відкриті дані', level: 1 })).toBeVisible();
    const stars = screen.getByRole('region', { name: "П'ять зірок відкритих даних" });
    expect(within(stars).getAllByRole('listitem')).toHaveLength(5);
    expect(within(stars).getByRole('img', { name: '5 з 5' })).toBeInTheDocument();
    expect(within(stars).getByText("Зв'язані з іншими наборами")).toBeInTheDocument();
    const dataset = screen.getByRole('region', { name: 'Набір даних' });
    expect(within(dataset).getByText('34 067')).toBeInTheDocument();
    expect(within(dataset).getByText('1 404')).toBeInTheDocument();
    expect(within(dataset).getByText('2 797')).toBeInTheDocument();
    expect(within(dataset).getByRole('link', { name: 'CC0 1.0' })).toHaveAttribute(
      'href',
      OVERVIEW.license,
    );
    expect(within(dataset).getByText(/20\.10\.2026/)).toBeInTheDocument();
  });

  it('веде до вивантаження набору й опису VoID', async () => {
    mockApi({ '/opendata': OVERVIEW, '/films/Q4': DETAILS });
    renderApp('/open-data');
    const dump = await screen.findByRole('link', { name: 'Завантажити набір (Turtle)' });
    expect(dump).toHaveAttribute('href', '/data/kinograf.ttl');
    expect(dump).toHaveAttribute('download');
    expect(screen.getByRole('link', { name: 'Опис набору (VoID)' })).toHaveAttribute(
      'href',
      '/.well-known/void',
    );
  });

  it('показує зв\'язки з іншими наборами в таблиці', async () => {
    mockApi({ '/opendata': OVERVIEW, '/films/Q4': DETAILS });
    renderApp('/open-data');
    const table = await screen.findByRole('table');
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      'Wikidataowl:sameAs1 4042 797',
      'Вікіпедія (укр.)schema:sameAs1 0122 104',
      'IMDbschema:sameAs9361 873',
      'DBpediaowl:sameAs4681 129',
    ]);
    const bars = rows[3].querySelectorAll('.od-bar');
    expect(bars[0]).toHaveStyle({ width: `${(468 / 1404) * 100}%` });
  });

  it('пояснює, як отримати дані, на прикладі фільму', async () => {
    const fetchMock = mockApi({ '/opendata': OVERVIEW, '/films/Q4': DETAILS });
    renderApp('/open-data');
    const access = await screen.findByRole('region', { name: 'Як отримати дані' });
    ['/id/film/{qid}', '/.well-known/void', '/data/kinograf.ttl', '/data/sparql'].forEach((path) =>
      expect(within(access).getByText(path)).toBeInTheDocument(),
    );
    const example = await within(access).findByLabelText('Приклад запиту й відповіді');
    expect(example).toHaveTextContent('curl -L -H "Accept: text/turtle"');
    expect(example).toHaveTextContent('<http://localhost:8080/id/film/Q4>');
    expect(example).toHaveTextContent('schema:name "Поводир, або \\"квіти\\""@uk');
    expect(example).toHaveTextContent('"2014-11-13"^^xsd:date');
    expect(example).toHaveTextContent('<http://localhost:8080/id/person/Q11>');
    expect(example).toHaveTextContent('owl:sameAs wd:Q4 .');
    expect(within(access).getByRole('link', { name: /Відкрити сторінку цього фільму/ })).toHaveAttribute(
      'href',
      '/films/Q4',
    );
    expect(requestedPaths(fetchMock)).toContain('/api/films/Q4');
  });

  it('не показує прикладу, якщо фільм для нього недоступний', async () => {
    mockApi({ '/opendata': { ...OVERVIEW, example_film: null } });
    renderApp('/open-data');
    await screen.findByRole('region', { name: 'Як отримати дані' });
    expect(screen.queryByLabelText('Приклад запиту й відповіді')).not.toBeInTheDocument();
  });

  it('показує порожній стан, якщо набір ще не опубліковано', async () => {
    mockApi({
      '/opendata': { ...OVERVIEW, triples: 0, films: 0, people: 0, example_film: null },
    });
    renderApp('/open-data');
    expect(
      await screen.findByText('Набір ще не опубліковано: дані не завантажено з Wikidata.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Повернутися до каталогу' })).toBeInTheDocument();
  });

  it('показує помилку й повторює запит', async () => {
    let calls = 0;
    mockApi({
      '/opendata': () => {
        calls += 1;
        return calls === 1 ? { status: 500, body: { detail: 'збій' } } : OVERVIEW;
      },
      '/films/Q4': DETAILS,
    });
    renderApp('/open-data');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Не вдалося отримати опис набору. Спробуйте ще раз за хвилину.');
    await userEvent.click(within(alert).getByRole('button', { name: 'Спробувати ще раз' }));
    expect(await screen.findByRole('heading', { name: 'Відкриті дані', level: 1 })).toBeVisible();
  });

  it('відкривається з меню після пункту SPARQL', async () => {
    mockApi({ '/opendata': OVERVIEW, '/films/Q4': DETAILS, '/films': { items: [], total: 0, page: 1 } });
    renderApp('/sparql');
    const nav = screen.getAllByRole('navigation', { name: 'Головне меню' })[0];
    await userEvent.click(within(nav).getByRole('link', { name: 'Відкриті дані' }));
    expect(await screen.findByRole('heading', { name: 'Відкриті дані', level: 1 })).toBeVisible();
    expect(within(nav).getByRole('link', { name: 'Відкриті дані' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });
});
