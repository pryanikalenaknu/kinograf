/** Сторінка 4.3 «Сторінка персоналії»: ролі, хронологія, фільмографія, співробітники. */

import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client.js';
import { useApi } from '../api/useApi.js';
import { filmsCount, initials, rolesText } from '../components/format.js';
import { Icon } from '../components/Icon.jsx';
import { Avatar, Breadcrumbs, RoleTag } from '../components/People.jsx';
import { RequestState } from '../components/States.jsx';
import './PersonPage.css';

const ROLE_ORDER = ['director', 'screenwriter', 'composer', 'cast'];
const MAX_LABELLED_YEARS = 8;

function byYear(filmography) {
  const years = new Map();
  [...filmography]
    .sort((a, b) => a.film.release_date.localeCompare(b.film.release_date))
    .forEach((entry) => {
      years.set(entry.film.year, [...(years.get(entry.film.year) ?? []), entry]);
    });
  return [...years.entries()];
}

function axisYears(first, last) {
  const span = Math.max(1, last - first);
  const step = span <= 12 ? 2 : Math.ceil(span / 6);
  const years = [];
  for (let year = first; year <= last; year += step) {
    years.push(year);
  }
  return years;
}

function Timeline({ filmography }) {
  const navigate = useNavigate();
  const years = byYear(filmography);
  const first = years[0][0] - 1;
  const last = years.at(-1)[0] + 1;
  const share = (year) => (year - first) / Math.max(1, last - first);
  const position = (year) => `${share(year) * 100}%`;
  const anchor = (year) => (share(year) < 0.12 ? 'start' : share(year) > 0.88 ? 'end' : 'middle');
  const labelled = years.length <= MAX_LABELLED_YEARS;
  return (
    <section className="panel timeline">
      <h2 className="panel-title">Хронологія</h2>
      <div className="timeline-axis desktop-only">
        <div className="timeline-line" />
        {axisYears(first, last).map((year) => (
          <span key={year} className="timeline-tick label muted" style={{ left: position(year) }}>
            {year}
          </span>
        ))}
        {years.map(([year, entries], index) => (
          <div
            key={year}
            className={`timeline-point timeline-${anchor(year)} timeline-tier-${index % 2}`}
            style={{ left: position(year) }}
          >
            {labelled &&
              entries.map(({ film }) => (
                <button
                  key={film.qid}
                  type="button"
                  className="timeline-chip"
                  title={film.title}
                  onClick={() => navigate(`/films/${film.qid}`)}
                >
                  {film.title}, {year}
                </button>
              ))}
            <button
              type="button"
              className="timeline-dot"
              aria-label={entries.map(({ film }) => `${film.title}, ${year}`).join('; ')}
              title={entries.map(({ film }) => film.title).join(', ')}
              onClick={() => navigate(`/films/${entries[0].film.qid}`)}
            />
          </div>
        ))}
      </div>
      <ol className="timeline-list phone-only">
        {years.map(([year, entries]) => (
          <li key={year}>
            <span className="timeline-year">{year}</span>
            {entries.map(({ film, roles }) => (
              <Link key={film.qid} to={`/films/${film.qid}`} className="timeline-film">
                <span>{film.title}</span>
                <span className="label muted">{rolesText(roles)}</span>
              </Link>
            ))}
          </li>
        ))}
      </ol>
    </section>
  );
}

function Filmography({ filmography }) {
  return (
    <section className="panel filmography">
      <h2 className="panel-title">Фільмографія</h2>
      <table className="filmography-table desktop-only">
        <thead>
          <tr>
            <th scope="col">Рік</th>
            <th scope="col">Назва</th>
            <th scope="col">Роль</th>
          </tr>
        </thead>
        <tbody>
          {filmography.map(({ film, roles }) => (
            <tr key={film.qid}>
              <td className="muted">{film.year}</td>
              <td>
                <Link to={`/films/${film.qid}`}>{film.title}</Link>
              </td>
              <td className="label">{rolesText(roles)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="filmography-cards phone-only">
        {filmography.map(({ film, roles }) => (
          <Link key={film.qid} to={`/films/${film.qid}`} className="filmography-card">
            <span className="filmography-card-text">
              <span className="filmography-card-title">{film.title}</span>
              <span className="label muted">{rolesText(roles)}</span>
            </span>
            <span className="label muted">{film.year}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

function Collaborators({ collaborators }) {
  return (
    <section className="panel collaborators">
      <h2 className="panel-title">Постійні співробітники</h2>
      {collaborators.map(({ person, films }) => (
        <Link key={person.qid} to={`/people/${person.qid}`} className="collaborator">
          <span className="avatar avatar-soft" aria-hidden="true">
            {initials(person.name)}
          </span>
          <span className="collaborator-text">
            <span className="collaborator-name">{person.name}</span>
            <span className="label muted">Спільних фільмів: {films}</span>
          </span>
        </Link>
      ))}
    </section>
  );
}

export function PersonPage() {
  const { qid } = useParams();
  const { state } = useLocation();
  const request = useApi(() => api.person(qid), [qid]);
  if (request.loading || request.error) {
    return (
      <div className="page">
        <RequestState
          request={request}
          notFoundText="Персоналії з таким ідентифікатором немає в довіднику."
        />
      </div>
    );
  }
  const { person, filmography, collaborators } = request.data;
  const roles = ROLE_ORDER.filter((role) => filmography.some((entry) => entry.roles.includes(role)));
  const from = state?.from;
  const crumbs = [
    { label: 'Каталог фільмів', to: '/' },
    ...(from ? [{ label: from.title, to: `/films/${from.qid}` }] : []),
    { label: person.name },
  ];
  const wikidata = (
    <a className="btn person-wikidata" href={person.wikidata_url} target="_blank" rel="noopener noreferrer">
      Запис у Wikidata
      <Icon name="external" size={16} />
    </a>
  );
  return (
    <div className="page person">
      <Breadcrumbs items={crumbs} />
      <header className="person-header">
        <Avatar name={person.name} size="large" />
        <div className="person-title">
          <h1 className="page-title">{person.name}</h1>
          <div className="person-tags">
            {roles.map((role) => (
              <span key={role} className="desktop-only">
                <RoleTag role={role} />
              </span>
            ))}
            <span className="label muted">{filmsCount(filmography.length)} у довіднику</span>
          </div>
        </div>
        <span className="desktop-only person-wikidata-desktop">{wikidata}</span>
      </header>
      <div className="person-tags phone-only">
        {roles.map((role) => (
          <RoleTag key={role} role={role} />
        ))}
      </div>
      <span className="phone-only">{wikidata}</span>
      {filmography.length > 0 && <Timeline filmography={filmography} />}
      <div className="person-columns">
        <Filmography filmography={filmography} />
        {collaborators.length > 0 && <Collaborators collaborators={collaborators} />}
      </div>
    </div>
  );
}
