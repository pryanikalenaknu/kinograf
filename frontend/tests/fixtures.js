import { vi } from 'vitest';

export function film(qid, title, year, extra = {}) {
  return {
    qid,
    title,
    release_date: `${year}-01-01`,
    year,
    duration_min: null,
    image_url: null,
    wikidata_url: `https://www.wikidata.org/wiki/${qid}`,
    ...extra,
  };
}

export function person(qid, name) {
  return { qid, name, wikidata_url: `https://www.wikidata.org/wiki/${qid}` };
}

export const SANIN = person('Q11', 'Олесь Санін');
export const ZAHAIKEVYCH = person('Q14', 'Алла Загайкевич');
export const POVODYR = film('Q4', 'Поводир', 2014, { duration_min: 122 });
export const MAMAI = film('Q3', 'Мамай', 2003, { duration_min: 80 });
export const DRAMA = { qid: 'Q130232', name: 'драма' };

/**
 * Підміняє fetch: відповідь шукається за найдовшим збігом початку шляху.
 * Значення маршруту — об'єкт відповіді, функція від URL або `{status, body}`.
 */
export function mockApi(routes) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
    const path = url.replace(/^\/api/, '');
    const key = Object.keys(routes)
      .filter((prefix) => path === prefix || path.startsWith(prefix))
      .sort((a, b) => b.length - a.length)[0];
    if (key === undefined) {
      return new Response(JSON.stringify({ detail: 'не знайдено' }), { status: 404 });
    }
    let value = routes[key];
    if (typeof value === 'function') {
      value = await value(path, options);
    }
    if (value && value.status && value.body !== undefined) {
      return new Response(JSON.stringify(value.body), { status: value.status });
    }
    return new Response(JSON.stringify(value), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  });
}

export function requestedPaths(fetchMock) {
  return fetchMock.mock.calls.map(([url]) => url);
}
