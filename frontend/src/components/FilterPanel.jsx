/** Поля фільтрів каталогу; використовуються в боковій панелі й у шторці на телефоні. */

import { MAX_YEAR, MIN_YEAR } from './filters.js';
import './FilterPanel.css';

const PERIODS = [
  { value: '1991-2013', label: '1991–2013' },
  { value: '2014-now', label: '2014 — дотепер' },
];

export function FilterPanel({ filters, genres, directors, onChange, onReset, footer }) {
  const yearFrom = filters.yearFrom ?? MIN_YEAR;
  const yearTo = filters.yearTo ?? MAX_YEAR;

  const setYear = (name, value) => {
    const year = Number(value);
    const bound = name === 'yearFrom' ? MIN_YEAR : MAX_YEAR;
    onChange({ [name]: year === bound ? undefined : year });
  };

  return (
    <div className="filters">
      <div className="filters-group">
        <div className="filters-years">
          <span className="muted">Роки</span>
          <span className="filters-years-value">
            {yearFrom} — {yearTo}
          </span>
        </div>
        <label className="filters-range">
          <span>від</span>
          <input
            type="range"
            min={MIN_YEAR}
            max={MAX_YEAR}
            value={yearFrom}
            aria-label="Рік від"
            onChange={(event) =>
              setYear('yearFrom', Math.min(Number(event.target.value), yearTo))
            }
          />
        </label>
        <label className="filters-range">
          <span>до</span>
          <input
            type="range"
            min={MIN_YEAR}
            max={MAX_YEAR}
            value={yearTo}
            aria-label="Рік до"
            onChange={(event) =>
              setYear('yearTo', Math.max(Number(event.target.value), yearFrom))
            }
          />
        </label>
      </div>
      <div className="filters-group">
        <span className="label muted">Період</span>
        <div className="filters-periods">
          {PERIODS.map((period) => (
            <button
              key={period.value}
              type="button"
              aria-pressed={filters.period === period.value}
              onClick={() =>
                onChange({ period: filters.period === period.value ? undefined : period.value })
              }
            >
              {period.label}
            </button>
          ))}
        </div>
      </div>
      <label className="filters-field">
        Жанр
        <select
          className="select"
          value={filters.genre ?? ''}
          onChange={(event) => onChange({ genre: event.target.value || undefined })}
        >
          <option value="">Усі жанри</option>
          {genres.map((genre) => (
            <option key={genre.qid} value={genre.qid}>
              {genre.name}
            </option>
          ))}
        </select>
      </label>
      <label className="filters-field">
        Режисер
        <select
          className="select"
          value={filters.director ?? ''}
          onChange={(event) => onChange({ director: event.target.value || undefined })}
        >
          <option value="">Усі режисери</option>
          {directors.map((person) => (
            <option key={person.qid} value={person.qid}>
              {person.name}
            </option>
          ))}
        </select>
      </label>
      <label className="filters-check">
        <input
          type="checkbox"
          checked={Boolean(filters.hasCast)}
          onChange={(event) => onChange({ hasCast: event.target.checked || undefined })}
        />
        Лише з акторами
      </label>
      {footer}
      <button type="button" className="btn" onClick={onReset}>
        Скинути фільтри
      </button>
    </div>
  );
}
