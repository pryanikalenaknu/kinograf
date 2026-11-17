/**
 * Клієнт REST API КіноГраф. Усі запити йдуть на відносний шлях `/api`,
 * який під час розробки Vite перенаправляє на локальний uvicorn.
 */

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function queryString(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([name, value]) => {
    if (value !== undefined && value !== null && value !== '' && value !== false) {
      search.set(name, String(value));
    }
  });
  const text = search.toString();
  return text ? `?${text}` : '';
}

async function errorMessage(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') {
      return body.detail;
    }
  } catch {
    return response.statusText;
  }
  return response.statusText;
}

async function request(path, { method = 'GET', body, adminKey, raw = false } = {}) {
  const headers = {};
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (adminKey) {
    headers['X-Admin-Key'] = adminKey;
  }
  let response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, 'Сервер недоступний');
  }
  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response));
  }
  return raw ? response.blob() : response.json();
}

export function filmQuery(filters) {
  return {
    q: filters.q,
    year_from: filters.yearFrom,
    year_to: filters.yearTo,
    period: filters.period,
    genre: filters.genre,
    director: filters.director,
    has_cast: filters.hasCast,
    sort: filters.sort,
  };
}

export const api = {
  films: (filters, page = 1) => request(`/films${queryString({ ...filmQuery(filters), page })}`),
  film: (qid) => request(`/films/${encodeURIComponent(qid)}`),
  person: (qid) => request(`/people/${encodeURIComponent(qid)}`),
  graph: (qid, depth) => request(`/graph/${encodeURIComponent(qid)}${queryString({ depth })}`),
  genres: () => request('/genres'),
  directors: () => request('/directors'),
  stats: () => request('/stats'),
  sparql: (query) => request('/sparql', { method: 'POST', body: { query } }),
  exportFilms: (filters, format) =>
    request(`/export/films${queryString({ ...filmQuery(filters), format })}`, { raw: true }),
  exportSparql: (query, format) =>
    request('/export/sparql', { method: 'POST', body: { query, format }, raw: true }),
  adminLog: (adminKey) => request('/admin/log', { adminKey }),
  startUpdate: (adminKey) => request('/admin/update', { method: 'POST', adminKey }),
  updateStatus: (id, adminKey) => request(`/admin/update/${id}`, { adminKey }),
};
