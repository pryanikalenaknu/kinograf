import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { issueLabel, visibleIssues } from '../src/components/qualityIssues.js';
import { film, mockApi, requestedPaths } from './fixtures.js';
import { renderApp } from './utils.jsx';

vi.mock('../src/components/ChartCanvas.jsx', () => ({ ChartCanvas: () => <figure /> }));

const STATS = {
  films_by_year: { 1992: 1, 2026: 1 },
  genres_by_period: {},
  top_directors: [],
  top_actors: [],
  completeness: { director: 0.5, cast: 0.5, genre: 0.5, poster: 0 },
  completeness_by_year: { 1992: { director: 1, cast: 1, genre: 1, poster: 0 } },
  last_updated: '2026-10-20T00:00:00+00:00',
};

const RULE_DATA = [
  ['release-date', 'Дата виходу', 'violation', 'P577', 0],
  ['duration-range', 'Тривалість від 1 до 600 хв', 'violation', 'P2047', 1],
  ['title-uk', 'Назва українською', 'warning', null, 382],
  ['director', 'Режисер', 'warning', 'P57', 445],
  ['cast', 'Актори', 'warning', 'P161', 742],
  ['genre', 'Жанр', 'warning', 'P136', 712],
  ['duration', 'Тривалість', 'info', 'P2047', 512],
  ['screenwriter', 'Сценарист', 'info', 'P58', 757],
  ['image', 'Зображення', 'info', 'P18', 1383],
  ['announced', 'Фільм уже вийшов', 'info', 'P577', 10],
];

const REPORT = {
  checked_at: '2026-10-20T00:00:00+00:00',
  films_checked: 1404,
  films_with_issues: 1390,
  by_severity: { violation: 1, warning: 1041, info: 348 },
  rules: RULE_DATA.map(([rule, name, severity, property, films], index) => ({
    rule: { rule, name, severity, message: name, property, order: index + 1 },
    films,
  })),
};

function issue(qid, rule, severity, property = null, value = null) {
  const anchor = property ? `#${property}` : '';
  return {
    rule,
    severity,
    message: rule,
    property,
    value,
    fix_url: `https://www.wikidata.org/wiki/${qid}${anchor}`,
  };
}

const PROSHCHENNIA = {
  film: film('Q1', 'Прощення', 1992),
  issues: [
    issue('Q1', 'duration-range', 'violation', 'P2047', '5345'),
    issue('Q1', 'screenwriter', 'info', 'P58'),
    issue('Q1', 'image', 'info', 'P18'),
  ],
};

const CHIMAERAS = {
  film: film('Q2', 'The House with Chimaeras', 2026),
  issues: [
    issue('Q2', 'title-uk', 'warning', null, 'The House with Chimaeras'),
    issue('Q2', 'director', 'warning', 'P57'),
    issue('Q2', 'cast', 'warning', 'P161'),
    issue('Q2', 'genre', 'warning', 'P136'),
    issue('Q2', 'duration', 'info', 'P2047'),
    issue('Q2', 'screenwriter', 'info', 'P58'),
    issue('Q2', 'image', 'info', 'P18'),
    issue('Q2', 'announced', 'info', 'P577', '2026-11-19'),
  ],
};

function issuesRoute(path) {
  const params = new URL(path, 'http://test').searchParams;
  const rule = params.get('rule');
  const severity = params.get('severity');
  const items = [PROSHCHENNIA, CHIMAERAS].filter(
    (item) =>
      (!rule || item.issues.some((entry) => entry.rule === rule)) &&
      (!severity || item.issues.some((entry) => entry.severity === severity)),
  );
  const page = Number(params.get('page') ?? 1);
  return { items, total: rule || severity ? items.length : 1390, page };
}

function routes(extra = {}) {
  return {
    '/stats': STATS,
    '/quality/rules': REPORT,
    '/quality/issues': issuesRoute,
    ...extra,
  };
}

async function section() {
  const heading = await screen.findByRole('heading', { name: /Перевірка за правилами/ });
  return heading.closest('section');
}

describe('перевірка за правилами', () => {
  it('підсумовує перевірку одним реченням', async () => {
    mockApi(routes());
    renderApp('/quality');
    const rules = await section();
    expect(
      await within(rules).findByText(
        /^1 404 фільми перевірено за 10 правилами 20\.10\.2026, \d\d:00\. Зауваження мають 1 390 фільмів: з помилками — 1, з попередженнями — 1 041, лише з підказками — 348\.$/,
      ),
    ).toBeInTheDocument();
  });

  it('показує таблицю правил із рівнями, кількістю й часткою', async () => {
    mockApi(routes());
    renderApp('/quality');
    const rules = await section();
    const table = await within(rules).findByRole('table');
    expect(within(table).getByRole('columnheader', { name: 'Частка від 1 404' })).toBeInTheDocument();
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows).toHaveLength(10);
    expect(rows[1]).toHaveTextContent('Тривалість від 1 до 600 хв P2047помилка1');
    expect(rows[2]).toHaveTextContent('Назва українськоюпопередження382');
    expect(rows[8]).toHaveTextContent('Зображення P18підказка1 383');
    expect(rows[0].querySelector('.rules-bar')).toBeNull();
    expect(rows[8].querySelector('.rules-bar')).toHaveStyle({ width: `${(1383 / 1404) * 100}%` });
    expect(rows[8].querySelector('.rules-bar')).toHaveClass('rules-bar-info');
  });

  it('дає завантажити правила й звіт перевірки', async () => {
    mockApi(routes());
    renderApp('/quality');
    const rules = await section();
    expect(within(rules).getByRole('link', { name: 'Правила' })).toHaveAttribute(
      'href',
      '/api/quality/shapes.ttl',
    );
    expect(await within(rules).findByRole('link', { name: 'Звіт перевірки' })).toHaveAttribute(
      'href',
      '/api/quality/report.ttl',
    );
  });

  it('показує фільми із зауваженнями тегами й посиланням на виправлення', async () => {
    mockApi(routes());
    renderApp('/quality');
    const rules = await section();
    await within(rules).findByText('Показано 1–2 з 1 390');
    const items = within(rules).getAllByRole('listitem');
    const first = items.find((item) => item.textContent.startsWith('Прощення'));
    expect(within(first).getByRole('link', { name: 'Прощення' })).toHaveAttribute('href', '/films/Q1');
    expect(within(first).getByText('тривалість 5 345 хв')).toHaveClass('issue-tag-violation');
    expect(within(first).getByText('немає сценариста')).toBeInTheDocument();
    expect(within(first).getByRole('link', { name: /Виправити у Wikidata/ })).toHaveAttribute(
      'href',
      'https://www.wikidata.org/wiki/Q1#P2047',
    );
    const second = items.find((item) => item.textContent.startsWith('The House with Chimaeras'));
    const tags = [...second.querySelectorAll('.issue-tag')].map((tag) => tag.textContent);
    expect(tags).toEqual([
      'немає назви українською',
      'немає режисера',
      'немає акторів',
      'немає жанру',
      'ще не вийшов',
      '+3',
    ]);
    expect(within(rules).getByText('Показано 1–2 з 1 390')).toBeInTheDocument();
  });

  it('фільтрує фільми за правилом і рівнем', async () => {
    const fetchMock = mockApi(routes());
    renderApp('/quality');
    const rules = await section();
    await within(rules).findByText('Показано 1–2 з 1 390');
    await userEvent.selectOptions(within(rules).getByLabelText('Правило'), 'announced');
    expect(await within(rules).findByText('Показано 1–1 з 1')).toBeInTheDocument();
    const item = within(rules).getByRole('link', { name: 'The House with Chimaeras' }).closest('li');
    expect(within(item).getByRole('link', { name: /Виправити у Wikidata/ })).toHaveAttribute(
      'href',
      'https://www.wikidata.org/wiki/Q2#P577',
    );
    await userEvent.selectOptions(within(rules).getByLabelText('Рівень'), 'violation');
    expect(await within(rules).findByText('Немає фільмів із такими зауваженнями.')).toBeInTheDocument();
    expect(requestedPaths(fetchMock)).toContain(
      '/api/quality/issues?rule=announced&severity=violation&page=1',
    );
  });

  it('гортає сторінки по 12 фільмів', async () => {
    const fetchMock = mockApi(routes());
    renderApp('/quality');
    const rules = await section();
    await within(rules).findByText('Показано 1–2 з 1 390');
    const pagination = within(rules).getByRole('navigation', { name: 'Пагінація' });
    expect(within(pagination).getByRole('button', { name: '116' })).toBeInTheDocument();
    await userEvent.click(within(pagination).getByRole('button', { name: 'Наступна сторінка' }));
    expect(await within(rules).findByText('Показано 13–14 з 1 390')).toBeInTheDocument();
    expect(requestedPaths(fetchMock)).toContain('/api/quality/issues?page=2');
  });

  it('пояснює, що перевірки ще не було', async () => {
    mockApi(routes({ '/quality/rules': { ...REPORT, checked_at: null } }));
    renderApp('/quality');
    const rules = await section();
    expect(
      await within(rules).findByText(/Перевірки ще не було: вона виконується наприкінці оновлення/),
    ).toBeInTheDocument();
    expect(within(rules).queryByRole('table')).not.toBeInTheDocument();
    expect(within(rules).queryByRole('link', { name: 'Звіт перевірки' })).not.toBeInTheDocument();
  });

  it('показує помилку й повторює запит правил', async () => {
    let calls = 0;
    mockApi(
      routes({
        '/quality/rules': () => {
          calls += 1;
          return calls === 1 ? { status: 500, body: { detail: 'збій' } } : REPORT;
        },
      }),
    );
    renderApp('/quality');
    const rules = await section();
    const alert = await within(rules).findByRole('alert');
    expect(alert).toHaveTextContent('Не вдалося отримати результати перевірки.');
    await userEvent.click(within(alert).getByRole('button', { name: 'Спробувати ще раз' }));
    expect(await within(rules).findByRole('table')).toBeInTheDocument();
  });
});

describe('теги зауважень', () => {
  it('називає зауваження коротко', () => {
    expect(issueLabel(issue('Q1', 'duration-range', 'violation', 'P2047', '5345'))).toBe(
      'тривалість 5 345 хв',
    );
    expect(issueLabel(issue('Q1', 'announced', 'info'))).toBe('ще не вийшов');
    expect(issueLabel({ ...issue('Q1', 'new-rule', 'info'), message: 'Нове правило' })).toBe(
      'Нове правило',
    );
  });

  it('згортає підказки про відсутні поля, коли зауважень більше п\'яти', () => {
    expect(visibleIssues(PROSHCHENNIA.issues)).toHaveLength(3);
    expect(visibleIssues(CHIMAERAS.issues).map((entry) => entry.rule)).toEqual([
      'title-uk',
      'director',
      'cast',
      'genre',
      'announced',
    ]);
  });
});
