/** Сторінка 4.9 «Панель адміністрування»: стан даних, запуск оновлення з етапами, журнал. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdmin } from '../api/admin.js';
import { api } from '../api/client.js';
import { useApi } from '../api/useApi.js';
import { formatDateTime, formatDuration, formatNumber } from '../components/format.js';
import { Icon } from '../components/Icon.jsx';
import { Dialog } from '../components/Overlay.jsx';
import { ErrorState, LoadingState } from '../components/States.jsx';
import './AdminPage.css';

const POLL_INTERVAL = 2000;

const STAGES = [
  { key: 'films', label: 'Фільми' },
  { key: 'participations', label: 'Учасники' },
  { key: 'genres', label: 'Жанри' },
  { key: 'awards', label: 'Нагороди' },
  { key: 'links', label: 'Посилання' },
  { key: 'storage', label: 'Запис у сховище' },
  { key: 'publication', label: 'Публікація' },
  { key: 'validation', label: 'Перевірка якості' },
];

function stageStates(log) {
  const current = Math.max(
    0,
    STAGES.findIndex((stage) => stage.key === log.stage),
  );
  return STAGES.map((stage, index) => {
    if (log.status === 'success' || index < current) {
      return { ...stage, state: 'done' };
    }
    if (index === current) {
      return { ...stage, state: log.status === 'error' ? 'fail' : 'current' };
    }
    return { ...stage, state: 'pending' };
  });
}

function progress(log) {
  if (log.status === 'success') {
    return 100;
  }
  const index = STAGES.findIndex((stage) => stage.key === log.stage);
  return Math.round((Math.max(0, index) / STAGES.length) * 100);
}

const STAGE_NOTES = { done: 'готово', current: 'виконується', fail: 'зупинено', pending: '' };

function StatusBadge({ status }) {
  const labels = { success: 'успішно', error: 'помилка', running: 'виконується' };
  return <span className={`status status-${status}`}>{labels[status] ?? status}</span>;
}

function UpdateProgress({ log, onClose, onRetry }) {
  const title = {
    running: 'Оновлення виконується…',
    success: 'Оновлення завершено',
    error: 'Оновлення зупинено',
  }[log.status];
  const percent = progress(log);
  return (
    <section className="panel progress" aria-live="polite" aria-label="Перебіг оновлення">
      <div className="progress-head">
        <h2 className="panel-title">{title}</h2>
        <span className="label muted progress-percent">{percent}%</span>
      </div>
      <div className="progress-track">
        <div className={`progress-bar progress-${log.status}`} style={{ width: `${percent}%` }} />
      </div>
      <ol className="stages">
        {stageStates(log).map((stage) => (
          <li key={stage.key} className={`stage stage-${stage.state}`}>
            <span className="stage-mark">
              {stage.state === 'done' && <Icon name="check" size={14} />}
              {stage.state === 'fail' && <Icon name="close" size={14} />}
            </span>
            <span className="stage-text">
              <span>{stage.label}</span>
              <span className="stage-note">{STAGE_NOTES[stage.state]}</span>
            </span>
          </li>
        ))}
      </ol>
      {log.status === 'success' && (
        <div className="notice notice-success">
          <span>
            Додано {log.films_added}, змінено {log.films_changed}
          </span>
          <button type="button" className="btn-text" onClick={onClose}>
            Закрити
          </button>
        </div>
      )}
      {log.status === 'error' && (
        <div className="notice notice-error" role="alert">
          <span>{log.message || 'Оновлення не вдалося'}</span>
          <button type="button" className="btn-text btn-outline" onClick={onRetry}>
            Повторити
          </button>
        </div>
      )}
    </section>
  );
}

function LogDetails({ log, onClose }) {
  const stages = STAGES.map((stage, index) => {
    const failedAt = STAGES.findIndex((item) => item.key === log.stage);
    let state = 'готово';
    if (log.status === 'error' && index === failedAt) {
      state = 'помилка';
    } else if (log.status === 'error' && index > failedAt) {
      state = 'не виконано';
    } else if (log.status === 'running' && index >= failedAt) {
      state = index === failedAt ? 'виконується' : 'не виконано';
    }
    return { ...stage, state };
  });
  return (
    <Dialog title={`Оновлення ${formatDateTime(log.started_at)}`} onClose={onClose}>
      <StatusBadge status={log.status} />
      <div className="details-numbers">
        <div>
          <span className="label muted">Тривалість</span>
          <strong>{log.finished_at ? formatDuration(log.started_at, log.finished_at) : '—'}</strong>
        </div>
        <div>
          <span className="label muted">Додано</span>
          <strong>{log.films_added}</strong>
        </div>
        <div>
          <span className="label muted">Змінено</span>
          <strong>{log.films_changed}</strong>
        </div>
      </div>
      <ul className="details-stages">
        {stages.map((stage) => (
          <li key={stage.key}>
            <span>{stage.label}</span>
            <span className={`details-state details-${stage.state === 'помилка' ? 'error' : stage.state === 'готово' ? 'done' : 'pending'}`}>
              {stage.state}
            </span>
          </li>
        ))}
      </ul>
      {log.message && (
        <div className="notice notice-error" role="alert">
          {log.message}
        </div>
      )}
      <div className="dialog-actions">
        <button type="button" className="btn" onClick={onClose}>
          Закрити
        </button>
      </div>
    </Dialog>
  );
}

function UpdateLog({ logs, onOpen }) {
  const [descending, setDescending] = useState(true);
  const sorted = [...logs].sort((a, b) =>
    descending ? b.started_at.localeCompare(a.started_at) : a.started_at.localeCompare(b.started_at),
  );
  const duration = (log) => (log.finished_at ? formatDuration(log.started_at, log.finished_at) : '—');
  const sortButton = (className) => (
    <button
      type="button"
      className={className}
      aria-label={descending ? 'Сортування: спочатку нові' : 'Сортування: спочатку старі'}
      onClick={() => setDescending(!descending)}
    >
      <span className="desktop-only">Дата</span>
      <Icon name={descending ? 'arrowDown' : 'arrowUp'} size={16} />
      <span className="phone-only">{descending ? 'спочатку нові' : 'спочатку старі'}</span>
    </button>
  );
  return (
    <section className="panel journal">
      <div className="journal-head">
        <h2 className="panel-title">Журнал оновлень</h2>
        {logs.length > 0 && <span className="phone-only">{sortButton('btn journal-sort')}</span>}
      </div>
      {logs.length === 0 ? (
        <p className="journal-empty label muted">Журнал порожній — оновлень ще не було.</p>
      ) : (
        <>
          <table className="journal-table desktop-only">
            <thead>
              <tr>
                <th scope="col" aria-sort={descending ? 'descending' : 'ascending'}>
                  {sortButton('journal-sort-header')}
                </th>
                <th scope="col">Тривалість</th>
                <th scope="col">Додано</th>
                <th scope="col">Змінено</th>
                <th scope="col">Статус</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((log) => (
                <tr key={log.id} tabIndex={0} onClick={() => onOpen(log)} onKeyDown={(event) => event.key === 'Enter' && onOpen(log)}>
                  <td>{formatDateTime(log.started_at)}</td>
                  <td className="muted">{duration(log)}</td>
                  <td>{log.films_added}</td>
                  <td>{log.films_changed}</td>
                  <td>
                    <StatusBadge status={log.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="journal-cards phone-only">
            {sorted.map((log) => (
              <button key={log.id} type="button" className="journal-card" onClick={() => onOpen(log)}>
                <span className="journal-card-top">
                  <span className="journal-card-date">{formatDateTime(log.started_at)}</span>
                  <StatusBadge status={log.status} />
                </span>
                <span className="label muted">
                  {duration(log)} · додано {log.films_added}, змінено {log.films_changed}
                </span>
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export function AdminPage() {
  const { adminKey, logout } = useAdmin();
  const navigate = useNavigate();
  const stats = useApi(() => api.stats(), []);
  const logs = useApi(() => api.adminLog(adminKey), [adminKey]);
  const [confirming, setConfirming] = useState(false);
  const [current, setCurrent] = useState(null);
  const [details, setDetails] = useState(null);
  const [startError, setStartError] = useState('');

  const running = current?.status === 'running' ? current : null;
  const resumable = !current && logs.data?.find((log) => log.status === 'running');
  const tracked = running ?? resumable ?? null;
  const reloadStats = stats.reload;
  const reloadLogs = logs.reload;

  const unauthorized = logs.error?.status === 401;
  useEffect(() => {
    if (unauthorized) {
      logout();
      navigate('/admin/login', { replace: true });
    }
  }, [unauthorized, logout, navigate]);

  const poll = useCallback(
    (id) =>
      api
        .updateStatus(id, adminKey)
        .then((log) => {
          setCurrent(log);
          if (log.status !== 'running') {
            reloadStats();
            reloadLogs();
          }
        })
        .catch((error) => {
          if (error.status === 401) {
            logout();
            navigate('/admin/login', { replace: true });
          }
        }),
    [adminKey, reloadStats, reloadLogs, logout, navigate],
  );

  const trackedId = tracked?.id;
  useEffect(() => {
    if (trackedId === undefined) {
      return undefined;
    }
    let active = true;
    let timer;
    const tick = async () => {
      await poll(trackedId);
      if (active) {
        timer = setTimeout(tick, POLL_INTERVAL);
      }
    };
    timer = setTimeout(tick, POLL_INTERVAL);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [trackedId, poll]);

  const start = async () => {
    setConfirming(false);
    setStartError('');
    try {
      const log = await api.startUpdate(adminKey);
      setCurrent(log);
      reloadLogs();
    } catch (error) {
      setStartError(
        error.status === 409 ? 'Оновлення вже виконується' : `Не вдалося запустити оновлення: ${error.message}`,
      );
      reloadLogs();
    }
  };

  if (stats.loading && !stats.data) {
    return (
      <div className="page">
        <LoadingState />
      </div>
    );
  }
  if (stats.error || (logs.error && !unauthorized)) {
    return (
      <div className="page">
        <ErrorState
          onRetry={() => {
            reloadStats();
            reloadLogs();
          }}
        />
      </div>
    );
  }

  const shown = current ?? resumable;
  return (
    <div className="page admin">
      <h1 className="page-title">Адміністрування</h1>
      <section className="panel admin-state" aria-label="Стан даних">
        <div className="admin-figure">
          <span className="label muted">Фільмів</span>
          <span className="admin-number">{formatNumber(stats.data.totals.films)}</span>
        </div>
        <div className="admin-figure">
          <span className="label muted">Персоналій</span>
          <span className="admin-number">{formatNumber(stats.data.totals.people)}</span>
        </div>
        <div className="admin-figure">
          <span className="label muted">Останнє оновлення</span>
          <span className="admin-date">
            {stats.data.last_updated ? formatDateTime(stats.data.last_updated) : 'ще не було'}
          </span>
        </div>
        <button
          type="button"
          className="btn btn-primary admin-update"
          disabled={Boolean(tracked)}
          onClick={() => setConfirming(true)}
        >
          <Icon name="refresh" />
          Оновити дані з Wikidata
        </button>
      </section>
      {startError && (
        <div className="notice notice-error" role="alert">
          {startError}
        </div>
      )}
      {shown && (
        <UpdateProgress
          log={shown}
          onClose={() => setCurrent(null)}
          onRetry={() => setConfirming(true)}
        />
      )}
      <UpdateLog logs={logs.data ?? []} onOpen={setDetails} />
      {confirming && (
        <Dialog
          title="Оновити дані з Wikidata?"
          role="alertdialog"
          onClose={() => setConfirming(false)}
        >
          <p className="muted confirm-text">
            Буде завантажено актуальні записи про фільми, учасників, жанри й нагороди. Оновлення
            триває кілька хвилин, каталог залишається доступним.
          </p>
          <div className="dialog-actions">
            <button type="button" className="btn btn-ghost" onClick={() => setConfirming(false)}>
              Скасувати
            </button>
            <button type="button" className="btn btn-primary" onClick={start}>
              Оновити
            </button>
          </div>
        </Dialog>
      )}
      {details && <LogDetails log={details} onClose={() => setDetails(null)} />}
    </div>
  );
}
