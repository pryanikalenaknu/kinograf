/** Посторінкова навігація каталогу. */

import { Icon } from './Icon.jsx';
import './Pagination.css';

function visiblePages(current, last) {
  const pages = new Set([1, last, current - 1, current, current + 1]);
  const sorted = [...pages].filter((page) => page >= 1 && page <= last).sort((a, b) => a - b);
  return sorted.flatMap((page, index) =>
    index > 0 && page - sorted[index - 1] > 1 ? ['gap', page] : [page],
  );
}

export function Pagination({ page, pages, onChange }) {
  if (pages <= 1) {
    return null;
  }
  return (
    <nav className="pagination" aria-label="Пагінація">
      <button
        type="button"
        aria-label="Попередня сторінка"
        disabled={page === 1}
        onClick={() => onChange(page - 1)}
      >
        <Icon name="chevronLeft" />
      </button>
      {visiblePages(page, pages).map((item, index) =>
        item === 'gap' ? (
          <span key={`gap-${index}`} className="pagination-gap">
            …
          </span>
        ) : (
          <button
            key={item}
            type="button"
            aria-current={item === page ? 'page' : undefined}
            onClick={() => onChange(item)}
          >
            {item}
          </button>
        ),
      )}
      <button
        type="button"
        aria-label="Наступна сторінка"
        disabled={page === pages}
        onClick={() => onChange(page + 1)}
      >
        <Icon name="chevronRight" />
      </button>
    </nav>
  );
}
