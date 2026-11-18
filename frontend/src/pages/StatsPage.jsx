/** Сторінка 4.5 «Статистика»: фільми за роками, жанри у двох періодах, топ-10 режисерів і акторів. */

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import { useApi } from '../api/useApi.js';
import { ChartCanvas } from '../components/ChartCanvas.jsx';
import { baseOptions, chartTheme } from '../components/chartTheme.js';
import { filmsCount } from '../components/format.js';
import { EmptyState, RequestState } from '../components/States.jsx';
import './StatsPage.css';

const PERIODS = ['1991-2013', '2014-now'];
const GENRES_SHOWN = 6;

function topGenres(genresByPeriod, limit = GENRES_SHOWN) {
  const totals = new Map();
  PERIODS.forEach((period) =>
    Object.entries(genresByPeriod[period] ?? {}).forEach(([name, count]) =>
      totals.set(name, (totals.get(name) ?? 0) + count),
    ),
  );
  return [...totals.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([name]) => ({
      name,
      before: genresByPeriod['1991-2013']?.[name] ?? 0,
      after: genresByPeriod['2014-now']?.[name] ?? 0,
    }));
}

function yearsConfig(filmsByYear) {
  const theme = chartTheme();
  const years = Object.keys(filmsByYear);
  const options = baseOptions(theme);
  options.plugins.tooltip.callbacks = {
    title: () => '',
    label: (item) => `${item.label}: ${filmsCount(item.raw)}`,
  };
  return {
    type: 'bar',
    data: {
      labels: years,
      datasets: [
        {
          data: Object.values(filmsByYear),
          backgroundColor: theme.primary,
          hoverBackgroundColor: theme.accent,
          borderRadius: { topLeft: 3, topRight: 3 },
          categoryPercentage: 0.9,
          barPercentage: 0.95,
        },
      ],
    },
    options,
  };
}

function genresConfig(genres) {
  const theme = chartTheme();
  const options = baseOptions(theme);
  options.plugins.tooltip.callbacks = {
    label: (item) => `${item.dataset.label}: ${filmsCount(item.raw)}`,
  };
  options.scales.x.ticks.autoSkip = false;
  options.scales.x.ticks.callback = (_, index) => [
    ...genres[index].name.split(' '),
    `${genres[index].before} / ${genres[index].after}`,
  ];
  return {
    type: 'bar',
    data: {
      labels: genres.map((genre) => genre.name),
      datasets: [
        {
          label: '1991–2013',
          data: genres.map((genre) => genre.before),
          backgroundColor: theme.primaryLight,
          borderRadius: { topLeft: 3, topRight: 3 },
        },
        {
          label: '2014 — дотепер',
          data: genres.map((genre) => genre.after),
          backgroundColor: theme.primary,
          borderRadius: { topLeft: 3, topRight: 3 },
        },
      ],
    },
    options,
  };
}

function Ranking({ title, people, color }) {
  const max = Math.max(1, ...people.map((entry) => entry.films));
  return (
    <section className="panel ranking">
      {title && <h2 className="panel-title">{title}</h2>}
      <ol>
        {people.map(({ person, films }, index) => (
          <li key={person.qid}>
            <span className="ranking-row">
              <Link to={`/people/${person.qid}`}>
                {index + 1}. {person.name}
              </Link>
              <span className="muted">{films}</span>
            </span>
            <span className="ranking-track">
              <span
                className="ranking-bar"
                style={{ width: `${(films / max) * 100}%`, background: color }}
              />
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Legend() {
  return (
    <div className="legend label muted">
      <span>
        <span className="legend-swatch legend-before" />
        1991–2013
      </span>
      <span>
        <span className="legend-swatch legend-after" />
        2014 — дотепер
      </span>
    </div>
  );
}

export function StatsPage() {
  const request = useApi(() => api.stats(), []);
  const [tab, setTab] = useState('directors');
  const stats = request.data;
  const years = useMemo(() => (stats ? yearsConfig(stats.films_by_year) : null), [stats]);
  const genres = useMemo(() => (stats ? topGenres(stats.genres_by_period) : []), [stats]);
  const genreChart = useMemo(() => genresConfig(genres), [genres]);

  if (request.loading || request.error) {
    return (
      <div className="page">
        <RequestState request={request} />
      </div>
    );
  }
  const yearList = Object.keys(stats.films_by_year);
  if (yearList.length === 0) {
    return (
      <div className="page">
        <h1 className="page-title">Статистика</h1>
        <EmptyState text="Дані ще не завантажено з Wikidata. Адміністратор може запустити оновлення." />
      </div>
    );
  }
  const directors = (
    <Ranking people={stats.top_directors} color="var(--color-role-director)" />
  );
  const actors = <Ranking people={stats.top_actors} color="var(--color-role-actor)" />;

  return (
    <div className="page stats">
      <h1 className="page-title">Статистика</h1>
      <section className="panel stats-years">
        <div className="stats-heading">
          <h2 className="panel-title">Фільми за роками</h2>
          <span className="label muted desktop-only">
            {yearList[0]}–{yearList.at(-1)} · наведіть на стовпчик
          </span>
          <span className="label muted phone-only">Торкніться стовпчика · гортайте вбік</span>
        </div>
        <div className="chart-scroll">
          <ChartCanvas
            config={years}
            className="chart chart-years"
            label={`Стовпчикова діаграма кількості фільмів за роками з ${yearList[0]} по ${yearList.at(-1)}`}
          />
        </div>
      </section>
      <section className="panel stats-genres">
        <h2 className="panel-title">Жанри у двох періодах</h2>
        <Legend />
        <div className="chart-scroll">
          <ChartCanvas
            config={genreChart}
            className="chart chart-genres"
            label="Стовпчикова діаграма кількості фільмів найпоширеніших жанрів у періодах 1991–2013 і 2014 — дотепер"
          />
        </div>
      </section>
      <div className="stats-top desktop-only">
        <Ranking
          title="Топ-10 режисерів"
          people={stats.top_directors}
          color="var(--color-role-director)"
        />
        <Ranking title="Топ-10 акторів" people={stats.top_actors} color="var(--color-role-actor)" />
      </div>
      <div className="phone-only stats-tabs">
        <div className="segmented" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'directors'}
            aria-pressed={tab === 'directors'}
            onClick={() => setTab('directors')}
          >
            Топ-10 режисерів
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'actors'}
            aria-pressed={tab === 'actors'}
            onClick={() => setTab('actors')}
          >
            Топ-10 акторів
          </button>
        </div>
        {tab === 'directors' ? directors : actors}
      </div>
    </div>
  );
}
