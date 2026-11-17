/** Фільтри каталогу: межі років, читання з адресного рядка й запис у нього. */

export const MIN_YEAR = 1991;
export const MAX_YEAR = new Date().getFullYear();

const PARAMS = {
  q: 'q',
  yearFrom: 'year_from',
  yearTo: 'year_to',
  period: 'period',
  genre: 'genre',
  director: 'director',
  hasCast: 'has_cast',
  sort: 'sort',
};

/** Читає фільтри з параметрів адреси сторінки. */
export function filtersFromParams(params) {
  const number = (name) => {
    const value = Number.parseInt(params.get(name) ?? '', 10);
    return Number.isFinite(value) ? value : undefined;
  };
  return {
    q: params.get('q') ?? '',
    yearFrom: number('year_from'),
    yearTo: number('year_to'),
    period: params.get('period') ?? undefined,
    genre: params.get('genre') ?? undefined,
    director: params.get('director') ?? undefined,
    hasCast: params.get('has_cast') === 'true' || undefined,
    sort: params.get('sort') ?? 'year',
  };
}

/** Записує фільтри й номер сторінки в параметри адреси, пропускаючи типові значення. */
export function paramsFromFilters(filters, page = 1) {
  const params = new URLSearchParams();
  Object.entries(PARAMS).forEach(([name, param]) => {
    const value = filters[name];
    if (value !== undefined && value !== '' && !(name === 'sort' && value === 'year')) {
      params.set(param, String(value));
    }
  });
  if (page > 1) {
    params.set('page', String(page));
  }
  return params;
}

/** Кількість застосованих фільтрів (без пошуку й сортування). */
export function activeFiltersCount(filters) {
  return ['yearFrom', 'yearTo', 'period', 'genre', 'director', 'hasCast'].filter(
    (name) => filters[name] !== undefined,
  ).length;
}
