/** Стани екранів: завантаження, порожньо, помилка. */

import { Link } from 'react-router-dom';
import { Icon } from './Icon.jsx';
import './States.css';

export function LoadingState({ text = 'Завантаження даних…' }) {
  return (
    <div className="state-loading" aria-busy="true">
      <div className="skeleton" style={{ width: '40%', height: 40 }} />
      <div className="skeleton" style={{ width: '70%', height: 20 }} />
      <div className="skeleton" style={{ height: 240 }} />
      <div className="state-loading-grid">
        <div className="skeleton" />
        <div className="skeleton" />
        <div className="skeleton" />
      </div>
      <span className="label muted">{text}</span>
    </div>
  );
}

export function EmptyState({ title = 'Немає даних', text, action }) {
  return (
    <div className="state-box">
      <Icon name="search" size={40} className="state-icon" />
      <h2 className="panel-title">{title}</h2>
      {text && <p className="muted">{text}</p>}
      {action ?? (
        <Link className="btn" to="/">
          Повернутися до каталогу
        </Link>
      )}
    </div>
  );
}

export function ErrorState({
  title = 'Не вдалося завантажити дані',
  text = 'Сервер не відповідає. Спробуйте ще раз за хвилину.',
  onRetry,
}) {
  return (
    <div className="state-box state-box-error" role="alert">
      <Icon name="alert" size={40} className="state-icon" />
      <h2 className="panel-title">{title}</h2>
      <p className="muted">{text}</p>
      {onRetry && (
        <button type="button" className="btn btn-primary" onClick={onRetry}>
          Спробувати ще раз
        </button>
      )}
    </div>
  );
}

/**
 * Показує стан запиту з `useApi`: завантаження, помилку або «не знайдено».
 * Повертає `null`, коли дані готові.
 */
export function RequestState({ request, notFoundText }) {
  if (request.loading) {
    return <LoadingState />;
  }
  if (request.error?.status === 404) {
    return <EmptyState title="Не знайдено" text={notFoundText} />;
  }
  if (request.error) {
    return <ErrorState onRetry={request.reload} />;
  }
  return null;
}
