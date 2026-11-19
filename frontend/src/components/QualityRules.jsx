/** Розділ «Перевірка за правилами» на сторінці 4.6: правила SHACL, частки й фільми із зауваженнями. */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import { useApi } from '../api/useApi.js';
import { filmsCount, formatDateTime, formatNumber, plural } from './format.js';
import { Icon } from './Icon.jsx';
import { Pagination } from './Pagination.jsx';
import { ISSUES_PAGE_SIZE, SEVERITIES, SEVERITY_LABELS, issueLabel, visibleIssues } from './qualityIssues.js';
import './QualityRules.css';

function rulesWord(count) {
  return plural(count, ['правилом', 'правилами', 'правилами']);
}

function summary(report) {
  const { violation, warning, info } = report.by_severity;
  return (
    `${filmsCount(report.films_checked)} перевірено за ${report.rules.length} ` +
    `${rulesWord(report.rules.length)} ${formatDateTime(report.checked_at)}. ` +
    `Зауваження мають ${filmsCount(report.films_with_issues)}: з помилками — ` +
    `${formatNumber(violation)}, з попередженнями — ${formatNumber(warning)}, ` +
    `лише з підказками — ${formatNumber(info)}.`
  );
}

function SeverityBadge({ severity }) {
  return <span className={`severity severity-${severity}`}>{SEVERITY_LABELS[severity]}</span>;
}

function RulesTable({ report }) {
  const total = report.films_checked;
  return (
    <>
      <table className="rules-table desktop-only">
        <thead>
          <tr>
            <th scope="col">Правило</th>
            <th scope="col">Рівень</th>
            <th scope="col" className="rules-number">
              Фільмів
            </th>
            <th scope="col">Частка від {formatNumber(total)}</th>
          </tr>
        </thead>
        <tbody>
          {report.rules.map(({ rule, films }) => (
            <tr key={rule.rule}>
              <th scope="row">
                {rule.name}
                {rule.property && <code className="rules-property"> {rule.property}</code>}
              </th>
              <td>
                <SeverityBadge severity={rule.severity} />
              </td>
              <td className="rules-number">{formatNumber(films)}</td>
              <td>
                <span className="rules-track" aria-hidden="true">
                  {films > 0 && (
                    <span
                      className={`rules-bar rules-bar-${rule.severity}`}
                      style={{ width: `${total ? (films / total) * 100 : 0}%` }}
                    />
                  )}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="rules-list phone-only">
        {report.rules.map(({ rule, films }) => (
          <li key={rule.rule}>
            <span className="rules-list-text">
              {rule.name}
              <SeverityBadge severity={rule.severity} />
            </span>
            <span className="rules-number">{formatNumber(films)}</span>
          </li>
        ))}
      </ul>
    </>
  );
}

function FilmIssues({ item, rule }) {
  const shown = visibleIssues(item.issues);
  const hidden = item.issues.filter((issue) => !shown.includes(issue));
  const target = item.issues.find((issue) => issue.rule === rule) ?? item.issues[0];
  return (
    <li className="film-issues">
      <div className="film-issues-text">
        <span className="film-issues-title">
          <Link to={`/films/${item.film.qid}`}>{item.film.title}</Link>
          <span className="label muted">{item.film.year}</span>
        </span>
        <span className="issue-tags">
          {shown.map((issue) => (
            <span key={issue.rule} className={`issue-tag issue-tag-${issue.severity}`}>
              {issueLabel(issue)}
            </span>
          ))}
          {hidden.length > 0 && (
            <span className="issue-tag issue-tag-info" title={hidden.map(issueLabel).join(', ')}>
              +{hidden.length}
            </span>
          )}
        </span>
      </div>
      <a className="btn" href={target.fix_url} target="_blank" rel="noopener noreferrer">
        Виправити у Wikidata
        <Icon name="external" size={16} />
        <span className="visually-hidden"> (фільм «{item.film.title}», відкривається в новій вкладці)</span>
      </a>
    </li>
  );
}

function IssuesList({ report }) {
  const [filters, setFilters] = useState({ rule: '', severity: '', page: 1 });
  const request = useApi(
    () => api.qualityIssues(filters),
    [filters.rule, filters.severity, filters.page],
  );
  const change = (name) => (event) =>
    setFilters({ ...filters, [name]: event.target.value, page: 1 });
  const data = request.data;
  const pages = data ? Math.ceil(data.total / ISSUES_PAGE_SIZE) : 0;
  const first = data ? (data.page - 1) * ISSUES_PAGE_SIZE + 1 : 0;
  const last = data ? first + data.items.length - 1 : 0;

  let content;
  if (request.loading) {
    content = <p className="label muted">Завантаження фільмів…</p>;
  } else if (request.error) {
    content = (
      <p className="issues-error" role="alert">
        Не вдалося завантажити фільми із зауваженнями.{' '}
        <button type="button" className="btn-link" onClick={request.reload}>
          Спробувати ще раз
        </button>
      </p>
    );
  } else if (data.total === 0) {
    content = <p className="label muted">Немає фільмів із такими зауваженнями.</p>;
  } else {
    content = (
      <>
        <ul className="issues">
          {data.items.map((item) => (
            <FilmIssues key={item.film.qid} item={item} rule={filters.rule} />
          ))}
        </ul>
        <Pagination
          page={data.page}
          pages={pages}
          onChange={(page) => setFilters({ ...filters, page })}
        />
      </>
    );
  }

  return (
    <div className="issues-block">
      <h3 className="issues-title">Фільми із зауваженнями</h3>
      <div className="issues-filters">
        <label className="issues-filter">
          <span className="label muted">Правило</span>
          <select className="select" value={filters.rule} onChange={change('rule')}>
            <option value="">Усі правила</option>
            {report.rules.map(({ rule }) => (
              <option key={rule.rule} value={rule.rule}>
                {rule.name}
              </option>
            ))}
          </select>
        </label>
        <label className="issues-filter">
          <span className="label muted">Рівень</span>
          <select className="select" value={filters.severity} onChange={change('severity')}>
            <option value="">Усі рівні</option>
            {SEVERITIES.map(({ value, filter }) => (
              <option key={value} value={value}>
                {filter}
              </option>
            ))}
          </select>
        </label>
        {data && data.total > 0 && !request.loading && (
          <span className="label muted issues-count" aria-live="polite">
            Показано {formatNumber(first)}–{formatNumber(last)} з {formatNumber(data.total)}
          </span>
        )}
      </div>
      {content}
    </div>
  );
}

export function QualityRules() {
  const request = useApi(() => api.qualityRules(), []);
  const report = request.data;
  let body;
  if (request.loading) {
    body = <p className="label muted">Завантаження результатів перевірки…</p>;
  } else if (request.error) {
    body = (
      <p className="issues-error" role="alert">
        Не вдалося отримати результати перевірки.{' '}
        <button type="button" className="btn-link" onClick={request.reload}>
          Спробувати ще раз
        </button>
      </p>
    );
  } else if (!report.checked_at) {
    body = (
      <p className="muted">
        Перевірки ще не було: вона виконується наприкінці оновлення даних з Wikidata.
      </p>
    );
  } else {
    body = (
      <>
        <p className="label muted rules-summary">{summary(report)}</p>
        <RulesTable report={report} />
        <IssuesList report={report} />
      </>
    );
  }
  return (
    <section className="panel rules" aria-labelledby="rules-title">
      <div className="rules-heading">
        <h2 id="rules-title" className="panel-title">
          Перевірка за правилами <code className="rules-shacl">SHACL</code>
        </h2>
        <div className="rules-downloads">
          <a className="btn" href="/api/quality/shapes.ttl" download="kinograf-shapes.ttl">
            <Icon name="download" />
            Правила
          </a>
          {report?.checked_at && (
            <a className="btn" href="/api/quality/report.ttl" download="kinograf-shacl-report.ttl">
              <Icon name="download" />
              Звіт перевірки
            </a>
          )}
        </div>
      </div>
      {body}
    </section>
  );
}
