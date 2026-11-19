/** Сторінка 4.6 «Якість даних»: частка заповнених полів, повнота за роками й перевірка за правилами. */

import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useAdmin } from '../api/admin.js';
import { api } from '../api/client.js';
import { useApi } from '../api/useApi.js';
import { ChartCanvas } from '../components/ChartCanvas.jsx';
import { baseOptions, chartTheme } from '../components/chartTheme.js';
import { formatDateTime, formatNumber, formatPercent } from '../components/format.js';
import { QualityRules } from '../components/QualityRules.jsx';
import { EmptyState, RequestState } from '../components/States.jsx';
import './QualityPage.css';

const METRICS = [
  { field: 'director', label: 'З режисером' },
  { field: 'cast', label: 'З акторами' },
  { field: 'genre', label: 'З жанром' },
  { field: 'poster', label: 'З постером' },
];

function completenessConfig(byYear) {
  const theme = chartTheme();
  const years = Object.keys(byYear);
  const options = baseOptions(theme);
  options.interaction = { mode: 'index', intersect: false };
  options.plugins.tooltip.displayColors = true;
  options.plugins.tooltip.callbacks = {
    label: (item) => `${item.dataset.label}: ${formatPercent(item.raw)}`,
  };
  options.scales.y = {
    display: true,
    min: 0,
    max: 1,
    border: { display: false },
    grid: { color: theme.border },
    ticks: {
      stepSize: 0.5,
      color: theme.muted,
      font: theme.font,
      callback: (value) => formatPercent(value),
    },
  };
  const line = (label, field, color) => ({
    label,
    data: years.map((year) => byYear[year][field]),
    borderColor: color,
    backgroundColor: color,
    borderWidth: 3,
    pointRadius: 0,
    pointHoverRadius: 4,
    tension: 0,
  });
  return {
    type: 'line',
    data: {
      labels: years,
      datasets: [
        line('з режисером', 'director', theme.primary),
        line('з акторами', 'cast', theme.actor),
      ],
    },
    options,
  };
}

function MetricCard({ label, value, share, sub }) {
  return (
    <div className="panel metric">
      <span className="label muted">{label}</span>
      <span className="metric-value">{value}</span>
      <span className="metric-track">
        <span className="metric-bar" style={{ width: `${share * 100}%` }} />
      </span>
      <span className="label muted">{sub}</span>
    </div>
  );
}

export function QualityPage() {
  const { isAdmin } = useAdmin();
  const request = useApi(() => api.stats(), []);
  const stats = request.data;
  const chart = useMemo(
    () => (stats ? completenessConfig(stats.completeness_by_year) : null),
    [stats],
  );

  if (request.loading || request.error) {
    return (
      <div className="page">
        <RequestState request={request} />
      </div>
    );
  }
  const total = Object.values(stats.films_by_year).reduce((sum, count) => sum + count, 0);
  const updated = stats.last_updated
    ? `Дані оновлено: ${formatDateTime(stats.last_updated)}`
    : 'Дані ще не оновлювалися';

  return (
    <div className="page quality">
      <div className="quality-heading">
        <h1 className="page-title">Якість даних</h1>
        <div className="label muted quality-updated">
          <span>{updated}</span>
          {isAdmin && <Link to="/admin">Журнал оновлень →</Link>}
        </div>
      </div>
      {total === 0 ? (
        <EmptyState text="Дані ще не завантажено з Wikidata. Адміністратор може запустити оновлення." />
      ) : (
        <>
          <div className="metrics">
            <MetricCard
              label="Усього фільмів"
              value={formatNumber(total)}
              share={1}
              sub="у довіднику з 1991 року"
            />
            {METRICS.map(({ field, label }) => (
              <MetricCard
                key={field}
                label={label}
                value={formatPercent(stats.completeness[field])}
                share={stats.completeness[field]}
                sub={`${formatNumber(Math.round(stats.completeness[field] * total))} з ${formatNumber(total)}`}
              />
            ))}
          </div>
          <section className="panel completeness">
            <div className="completeness-heading">
              <h2 className="panel-title">Повнота даних за роками</h2>
              <div className="legend label muted">
                <span>
                  <span className="legend-line legend-director" />з режисером
                </span>
                <span>
                  <span className="legend-line legend-cast" />з акторами
                </span>
              </div>
            </div>
            <ChartCanvas
              config={chart}
              className="chart chart-completeness"
              label="Лінійна діаграма частки фільмів із режисером і з акторами за роками"
            />
          </section>
          <QualityRules />
        </>
      )}
    </div>
  );
}
