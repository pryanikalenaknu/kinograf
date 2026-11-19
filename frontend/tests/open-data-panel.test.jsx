import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MAMAI, POVODYR, SANIN, ZAHAIKEVYCH, mockApi } from './fixtures.js';
import { renderApp } from './utils.jsx';

const BASE = 'http://localhost:8080';

function links(kind, qid, extra = {}) {
  return {
    uri: `${BASE}/id/${kind}/${qid}`,
    wikidata: `https://www.wikidata.org/wiki/${qid}`,
    imdb: null,
    wikipedia: null,
    dbpedia: null,
    turtle: `${BASE}/data/${kind}/${qid}.ttl`,
    jsonld: `${BASE}/data/${kind}/${qid}.jsonld`,
    ...extra,
  };
}

const DETAILS = {
  film: POVODYR,
  participants: { director: [SANIN], screenwriter: [], composer: [], cast: [] },
  genres: [],
  awards: [],
  related: [],
  links: links('film', 'Q4', {
    imdb: 'https://www.imdb.com/title/tt3699354/',
    wikipedia: 'https://uk.wikipedia.org/wiki/%D0%9F%D0%BE%D0%B2%D0%BE%D0%B4%D0%B8%D1%80',
  }),
};

const PROFILE = {
  person: SANIN,
  filmography: [{ film: POVODYR, roles: ['director'] }, { film: MAMAI, roles: ['director'] }],
  collaborators: [{ person: ZAHAIKEVYCH, films: 2 }],
  links: links('person', 'Q11', { dbpedia: 'http://dbpedia.org/resource/Oles_Sanin' }),
};

const FILM_JSONLD = {
  '@context': { '@vocab': 'https://schema.org/' },
  '@id': `${BASE}/id/film/Q4`,
  '@type': 'Movie',
  name: 'Поводир',
};

const PERSON_JSONLD = { '@id': `${BASE}/id/person/Q11`, '@type': 'Person', name: 'Олесь Санін' };

const ROUTES = {
  '/films/Q4': DETAILS,
  '/people/Q11': PROFILE,
  '/data/film/Q4.jsonld': FILM_JSONLD,
  '/data/person/Q11.jsonld': PERSON_JSONLD,
  '/opendata': { films: 0, people: 0, triples: 0, linksets: [] },
};

function structuredData() {
  return [...document.head.querySelectorAll('script[type="application/ld+json"]')];
}

async function panel() {
  const heading = await screen.findByRole('heading', { name: 'Відкриті дані', level: 2 });
  return heading.closest('section');
}

afterEach(() => {
  structuredData().forEach((script) => script.remove());
});

describe('панель «Відкриті дані»', () => {
  it('показує на картці фільму лише наявні набори', async () => {
    mockApi(ROUTES);
    renderApp('/films/Q4');
    const section = await panel();
    const chips = within(section).getAllByRole('listitem').map((item) => item.textContent);
    expect(chips).toEqual(['Wikidata', 'IMDb', 'Вікіпедія']);
    expect(within(section).queryByRole('link', { name: /DBpedia/ })).not.toBeInTheDocument();
    expect(within(section).getByRole('link', { name: /IMDb/ })).toHaveAttribute(
      'href',
      'https://www.imdb.com/title/tt3699354/',
    );
    expect(within(section).getByRole('link', { name: /IMDb/ })).toHaveAttribute('target', '_blank');
  });

  it('показує постійну адресу й посилання на Turtle і JSON-LD', async () => {
    mockApi(ROUTES);
    renderApp('/films/Q4');
    const section = await panel();
    expect(within(section).getByText(`${BASE}/id/film/Q4`)).toHaveAttribute(
      'title',
      `${BASE}/id/film/Q4`,
    );
    expect(within(section).getByRole('link', { name: 'Turtle' })).toHaveAttribute(
      'href',
      '/data/film/Q4.ttl',
    );
    expect(within(section).getByRole('link', { name: 'JSON-LD' })).toHaveAttribute(
      'href',
      '/data/film/Q4.jsonld',
    );
    expect(within(section).getByRole('link', { name: 'Про набір даних →' })).toHaveAttribute(
      'href',
      '/open-data',
    );
  });

  it('копіює постійну адресу', async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue();
    mockApi(ROUTES);
    renderApp('/films/Q4');
    const section = await panel();
    await user.click(within(section).getByRole('button', { name: 'Копіювати адресу' }));
    expect(writeText).toHaveBeenCalledWith(`${BASE}/id/film/Q4`);
    expect(await within(section).findByRole('status')).toHaveTextContent('Адресу скопійовано');
  });

  it('копіює адресу й без Clipboard API, як на адресі в локальній мережі', async () => {
    const clipboard = Object.getOwnPropertyDescriptor(navigator, 'clipboard');
    Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true });
    document.execCommand = vi.fn(() => true);
    try {
      mockApi(ROUTES);
      renderApp('/films/Q4');
      const section = await panel();
      await userEvent.click(within(section).getByRole('button', { name: 'Копіювати адресу' }));
      expect(document.execCommand).toHaveBeenCalledWith('copy');
      expect(await within(section).findByRole('status')).toHaveTextContent('Адресу скопійовано');
    } finally {
      if (clipboard) {
        Object.defineProperty(navigator, 'clipboard', clipboard);
      } else {
        delete navigator.clipboard;
      }
      delete document.execCommand;
    }
  });

  it('стоїть на сторінці персоналії під постійними співробітниками', async () => {
    mockApi(ROUTES);
    renderApp('/people/Q11');
    const section = await panel();
    const side = section.parentElement;
    expect(within(side).getByRole('heading', { name: 'Постійні співробітники' })).toBeInTheDocument();
    const chips = within(section).getAllByRole('listitem').map((item) => item.textContent);
    expect(chips).toEqual(['Wikidata', 'DBpedia']);
    expect(within(section).getByText(`${BASE}/id/person/Q11`)).toBeInTheDocument();
  });
});

describe('розмітка schema.org', () => {
  it('додає документ JSON-LD у head картки фільму', async () => {
    mockApi(ROUTES);
    renderApp('/films/Q4');
    await panel();
    await waitFor(() => expect(structuredData()).toHaveLength(1));
    const [script] = structuredData();
    expect(script.getAttribute('data-kinograf-entity')).toBe('film/Q4');
    expect(JSON.parse(script.textContent)).toEqual(FILM_JSONLD);
  });

  it('прибирає документ після переходу на іншу сторінку', async () => {
    mockApi(ROUTES);
    renderApp('/films/Q4');
    await waitFor(() => expect(structuredData()).toHaveLength(1));
    const nav = screen.getAllByRole('navigation', { name: 'Головне меню' })[0];
    await userEvent.click(within(nav).getByRole('link', { name: 'Відкриті дані' }));
    await screen.findByText('Набір ще не опубліковано: дані не завантажено з Wikidata.');
    expect(structuredData()).toHaveLength(0);
  });

  it('замінює документ при переході від фільму до персоналії', async () => {
    mockApi(ROUTES);
    renderApp('/films/Q4');
    await waitFor(() => expect(structuredData()).toHaveLength(1));
    const participants = screen.getByRole('heading', { name: 'Учасники' }).closest('section');
    await userEvent.click(within(participants).getByRole('link', { name: /Олесь Санін/ }));
    await waitFor(() =>
      expect(structuredData().map((script) => script.getAttribute('data-kinograf-entity'))).toEqual(
        ['person/Q11'],
      ),
    );
  });

  it('нічого не додає, якщо документа немає', async () => {
    mockApi({ '/films/Q4': DETAILS });
    renderApp('/films/Q4');
    await panel();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(structuredData()).toHaveLength(0);
  });
});
