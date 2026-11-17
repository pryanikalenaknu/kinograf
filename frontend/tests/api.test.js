import { describe, expect, it, vi } from 'vitest';
import { ApiError, api, queryString } from '../src/api/client.js';
import { jsonResponse } from './utils.jsx';

describe('клієнт API', () => {
  it('будує рядок запиту без порожніх значень', () => {
    expect(queryString({ q: 'плем', page: 2, genre: '', has_cast: false, director: null })).toBe(
      '?q=%D0%BF%D0%BB%D0%B5%D0%BC&page=2',
    );
    expect(queryString({})).toBe('');
  });

  it('передає фільтри каталогу в параметрах', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockReturnValue(jsonResponse({ items: [] }));
    await api.films({ q: 'мамай', period: '2014-now', hasCast: true, sort: 'title' }, 3);
    expect(fetch).toHaveBeenCalledWith(
      '/api/films?q=%D0%BC%D0%B0%D0%BC%D0%B0%D0%B9&period=2014-now&has_cast=true&sort=title&page=3',
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('надсилає ключ адміністратора в заголовку', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockReturnValue(jsonResponse([]));
    await api.adminLog('secret');
    expect(fetch.mock.calls[0][1].headers).toEqual({ 'X-Admin-Key': 'secret' });
  });

  it('надсилає SPARQL-запит як JSON', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockReturnValue(jsonResponse({ rows: [] }));
    await api.sparql('SELECT * WHERE {}');
    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe('/api/sparql');
    expect(JSON.parse(options.body)).toEqual({ query: 'SELECT * WHERE {}' });
  });

  it('перетворює відповідь з помилкою на ApiError з описом сервера', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse({ detail: 'фільм не знайдено' }, 404),
    );
    const error = await api.film('Q999').catch((caught) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(404);
    expect(error.message).toBe('фільм не знайдено');
  });

  it('повідомляє про недоступний сервер', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'));
    const error = await api.stats().catch((caught) => caught);
    expect(error.status).toBe(0);
    expect(error.message).toBe('Сервер недоступний');
  });

  it('завантажує експорт каталогу з фільтрами як файл', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response('qid,title', { status: 200 }));
    const file = await api.exportFilms({ genre: 'Q130232', sort: 'year' }, 'csv');
    expect(fetchMock.mock.calls[0][0]).toBe('/api/export/films?genre=Q130232&sort=year&format=csv');
    expect(file).toBeInstanceOf(Blob);
    expect(await file.text()).toBe('qid,title');
  });
});
