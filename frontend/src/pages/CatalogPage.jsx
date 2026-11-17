/** Сторінка 4.1 «Каталог фільмів»: пошук, фільтри, сортування, пагінація, експорт. */

import { useEffect, useRef, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { api } from '../api/client.js';
import { useApi } from '../api/useApi.js';
import { saveFile } from '../components/download.js';
import { ExportDialog } from '../components/ExportDialog.jsx';
import { FilmCard, FilmCardSkeleton } from '../components/FilmCard.jsx';
import { FilterPanel } from '../components/FilterPanel.jsx';
import { activeFiltersCount, filtersFromParams, paramsFromFilters } from '../components/filters.js';
import { filmsCount } from '../components/format.js';
import { Icon } from '../components/Icon.jsx';
import { Sheet } from '../components/Overlay.jsx';
import { Pagination } from '../components/Pagination.jsx';
import { ErrorState } from '../components/States.jsx';
import { useIsPhone } from '../components/useIsPhone.js';
import './CatalogPage.css';

const PAGE_SIZE = 12;

const SORTS = [
  { value: 'year', label: 'За роком' },
  { value: 'title', label: 'За назвою' },
];

function SearchBox({ value, onChange, placeholder }) {
  const [text, setText] = useState(value);
  const [synced, setSynced] = useState(value);
  const [sent, setSent] = useState(value);

  if (value !== synced) {
    setSynced(value);
    if (value !== sent) {
      setSent(value);
      setText(value);
    }
  }

  useEffect(() => {
    if (text === sent) {
      return undefined;
    }
    const timer = setTimeout(() => {
      setSent(text);
      onChange(text);
    }, 300);
    return () => clearTimeout(timer);
  }, [text, sent, onChange]);

  return (
    <div className="search-box">
      <Icon name="search" size={20} className="muted" />
      <input
        type="search"
        value={text}
        placeholder={placeholder}
        aria-label="Пошук за назвою фільму"
        onChange={(event) => setText(event.target.value)}
      />
      {text && (
        <button
          type="button"
          className="btn-plain muted"
          aria-label="Очистити пошук"
          onClick={() => {
            setText('');
            setSent('');
            onChange('');
          }}
        >
          <Icon name="close" />
        </button>
      )}
    </div>
  );
}

function NothingFound({ onReset }) {
  return (
    <div className="catalog-empty">
      <h2 className="panel-title">Нічого не знайдено</h2>
      <p className="label muted">Спробуйте змінити запит або скинути фільтри.</p>
      <button type="button" className="btn btn-primary" onClick={onReset}>
        Скинути фільтри
      </button>
    </div>
  );
}

export function CatalogPage() {
  const [params, setParams] = useSearchParams();
  const filters = filtersFromParams(params);
  const page = Math.max(1, Number(params.get('page')) || 1);
  const isPhone = useIsPhone();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [exporting, setExporting] = useState({ open: false, busy: false, error: '' });
  const [more, setMore] = useState({ key: '', items: [], pages: 0, loading: false });

  const filterKey = paramsFromFilters(filters).toString();
  const films = useApi(() => api.films(filters, page), [filterKey, page]);
  const genres = useApi(() => api.genres(), []);
  const directors = useApi(() => api.directors(), []);

  const requested = useRef(params);
  useEffect(() => {
    requested.current = params;
  }, [params]);

  const navigateTo = (next, options) => {
    requested.current = next;
    setParams(next, options);
  };
  const update = (changes) =>
    navigateTo(paramsFromFilters({ ...filtersFromParams(requested.current), ...changes }), {
      replace: true,
    });
  const reset = () => {
    const { q, sort } = filtersFromParams(requested.current);
    navigateTo(paramsFromFilters({ q, sort }));
  };
  const goToPage = (next) => {
    navigateTo(paramsFromFilters(filtersFromParams(requested.current), next));
    window.scrollTo?.({ top: 0, behavior: 'smooth' });
  };

  const current = more.key === filterKey ? more : { items: [], pages: 0 };
  const items = [...(films.data?.items ?? []), ...current.items];
  const total = films.data?.total ?? 0;
  const pages = Math.ceil(total / PAGE_SIZE);
  const loadedPages = page + current.pages;

  const showMore = async () => {
    setMore({ ...current, key: filterKey, loading: true });
    try {
      const next = await api.films(filters, loadedPages + 1);
      setMore({
        key: filterKey,
        items: [...current.items, ...next.items],
        pages: current.pages + 1,
        loading: false,
      });
    } catch {
      setMore({ ...current, key: filterKey, loading: false });
    }
  };

  const activeCount = activeFiltersCount(filters);
  const filtersLabel = activeCount ? `Фільтри (${activeCount})` : 'Фільтри';
  const countText = films.loading && !films.data ? 'Пошук…' : `Знайдено: ${filmsCount(total)}`;

  const panel = (footer) => (
    <FilterPanel
      filters={filters}
      genres={genres.data ?? []}
      directors={directors.data ?? []}
      onChange={update}
      onReset={reset}
      footer={footer}
    />
  );

  let results;
  if (films.error) {
    results = <ErrorState onRetry={films.reload} />;
  } else if (films.loading) {
    results = (
      <div className="catalog-grid" aria-busy="true">
        {Array.from({ length: isPhone ? 4 : 8 }, (_, index) => (
          <FilmCardSkeleton key={index} />
        ))}
      </div>
    );
  } else if (total > 0 && page > pages) {
    results = <Navigate to={`?${paramsFromFilters(filters, pages)}`} replace />;
  } else if (items.length === 0) {
    results = <NothingFound onReset={() => navigateTo(new URLSearchParams())} />;
  } else {
    results = (
      <>
        <div className="catalog-grid">
          {items.map((item) => (
            <FilmCard key={item.film.qid} item={item} />
          ))}
        </div>
        {isPhone ? (
          loadedPages < pages && (
            <button
              type="button"
              className="btn catalog-more"
              disabled={more.loading}
              onClick={showMore}
            >
              Показати ще
            </button>
          )
        ) : (
          <Pagination page={page} pages={pages} onChange={goToPage} />
        )}
      </>
    );
  }

  return (
    <div className="page catalog">
      <aside className="catalog-filters panel desktop-only" aria-label="Фільтри">
        <h2 className="panel-title">Фільтри</h2>
        {panel()}
      </aside>
      <section className="catalog-main">
        <div>
          <h1 className="page-title">Каталог фільмів</h1>
          <p className="page-subtitle desktop-only">
            Українські фільми від 1991 року за відкритими даними Wikidata
          </p>
        </div>
        <SearchBox
          value={filters.q}
          onChange={(q) => update({ q })}
          placeholder={isPhone ? 'Пошук за назвою' : 'Пошук за назвою фільму'}
        />
        <div className="catalog-toolbar desktop-only">
          <span className="catalog-count" aria-live="polite">
            {countText}
          </span>
          <span className="label muted catalog-sort-label">Сортування:</span>
          <div className="segmented" role="group" aria-label="Сортування">
            {SORTS.map((sort) => (
              <button
                key={sort.value}
                type="button"
                aria-pressed={filters.sort === sort.value}
                onClick={() => update({ sort: sort.value })}
              >
                {sort.label}
              </button>
            ))}
          </div>
          <button type="button" className="btn" onClick={() => setExporting({ open: true, busy: false, error: '' })}>
            <Icon name="download" />
            Експорт
          </button>
        </div>
        <div className="catalog-toolbar-phone phone-only">
          <button type="button" className="btn" onClick={() => setSheetOpen(true)}>
            <Icon name="filters" />
            {filtersLabel}
          </button>
          <select
            className="select"
            aria-label="Сортування"
            value={filters.sort}
            onChange={(event) => update({ sort: event.target.value })}
          >
            {SORTS.map((sort) => (
              <option key={sort.value} value={sort.value}>
                {sort.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn-icon"
            aria-label="Експорт"
            onClick={() => setExporting({ open: true, busy: false, error: '' })}
          >
            <Icon name="download" />
          </button>
        </div>
        <span className="catalog-count phone-only" aria-live="polite">
          {countText}
        </span>
        {results}
      </section>
      {sheetOpen && (
        <Sheet title={filtersLabel} onClose={() => setSheetOpen(false)}>
          {panel(
            <button type="button" className="btn btn-primary" onClick={() => setSheetOpen(false)}>
              Показати {filmsCount(total)}
            </button>,
          )}
        </Sheet>
      )}
      {exporting.open && (
        <ExportDialog
          title={`Експорт каталогу · ${filmsCount(total)}`}
          busy={exporting.busy}
          error={exporting.error}
          onClose={() => setExporting({ open: false, busy: false, error: '' })}
          onExport={async (format) => {
            setExporting({ open: true, busy: true, error: '' });
            try {
              saveFile(await api.exportFilms(filters, format), `films.${format}`);
              setExporting({ open: false, busy: false, error: '' });
            } catch (error) {
              setExporting({ open: true, busy: false, error: error.message });
            }
          }}
        />
      )}
    </div>
  );
}
