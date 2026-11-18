/** Сторінка 4.2 «Картка фільму»: учасники за ролями, нагороди, пов'язані фільми. */

import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client.js';
import { useApi } from '../api/useApi.js';
import { ROLE_COLORS, ROLE_LABELS } from '../components/format.js';
import { Icon } from '../components/Icon.jsx';
import { Avatar, Breadcrumbs, MissingData, PersonChip } from '../components/People.jsx';
import { Poster } from '../components/Poster.jsx';
import { RequestState } from '../components/States.jsx';
import './FilmPage.css';

const ROLES = ['director', 'screenwriter', 'composer', 'cast'];

function filmMeta(film) {
  return film.duration_min ? `${film.year} · ${film.duration_min} хв` : String(film.year);
}

function RelatedFilms({ related }) {
  if (related.length === 0) {
    return null;
  }
  return (
    <section className="related">
      <h2 className="panel-title">Пов'язані фільми</h2>
      <div className="related-list">
        {related.map(({ film, shared_people: people }) => (
          <Link key={film.qid} to={`/films/${film.qid}`} className="related-card">
            <Poster film={film} className="related-poster" showYear={false} width={300} />
            <span className="related-body">
              <span className="label muted">{film.year}</span>
              <span className={people ? 'related-note related-note-people' : 'related-note'}>
                {people ? `Спільних учасників: ${people}` : 'Спільний жанр'}
              </span>
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}

function ParticipantsTable({ participants, film }) {
  const from = { qid: film.qid, title: film.title };
  return (
    <section className="panel participants">
      <h2 className="panel-title">Учасники</h2>
      {ROLES.map((role) => (
        <div key={role} className="participants-row">
          <span className="label muted participants-role">{ROLE_LABELS[role].one}</span>
          {participants[role].length ? (
            <div className="participants-people">
              {participants[role].map((person) => (
                <PersonChip key={person.qid} person={person} role={role} from={from} />
              ))}
            </div>
          ) : (
            <MissingData wikidataUrl={film.wikidata_url} />
          )}
        </div>
      ))}
    </section>
  );
}

function ParticipantsAccordion({ participants, film }) {
  const [open, setOpen] = useState(() =>
    Object.fromEntries(
      ROLES.map((role, index) => [role, index === 0 || participants[role].length === 0]),
    ),
  );
  const from = { qid: film.qid, title: film.title };
  return (
    <section className="panel accordion">
      {ROLES.map((role) => {
        const people = participants[role];
        return (
          <div key={role} className="accordion-item">
            <button
              type="button"
              className="accordion-head"
              aria-expanded={open[role]}
              onClick={() => setOpen({ ...open, [role]: !open[role] })}
            >
              {ROLE_LABELS[role].one}
              <span className="label muted accordion-count">
                {people.length || ''}
                <Icon name={open[role] ? 'chevronUp' : 'chevronDown'} />
              </span>
            </button>
            {open[role] && (
              <div className="accordion-body">
                {people.map((person) => (
                  <Link
                    key={person.qid}
                    to={`/people/${person.qid}`}
                    state={{ from }}
                    className="accordion-person"
                  >
                    <Avatar name={person.name} color={ROLE_COLORS[role]} />
                    {person.name}
                  </Link>
                ))}
                {people.length === 0 && <MissingData wikidataUrl={film.wikidata_url} />}
              </div>
            )}
          </div>
        );
      })}
    </section>
  );
}

function Awards({ awards }) {
  if (awards.length === 0) {
    return null;
  }
  return (
    <section className="panel awards">
      <h2 className="panel-title">Нагороди</h2>
      <ul>
        {awards.map((award) => (
          <li key={award.qid}>{award.name}</li>
        ))}
      </ul>
    </section>
  );
}

function FilmActions({ film }) {
  return (
    <>
      <Link to={`/graph/${film.qid}`} className="btn btn-primary">
        <Icon name="share" />
        Граф зв'язків
      </Link>
      <a className="btn" href={film.wikidata_url} target="_blank" rel="noopener noreferrer">
        Запис у Wikidata
        <Icon name="external" size={16} />
      </a>
    </>
  );
}

export function FilmPage() {
  const { qid } = useParams();
  const request = useApi(() => api.film(qid), [qid]);
  const state = (
    <RequestState request={request} notFoundText="Фільму з таким ідентифікатором немає в довіднику." />
  );
  if (request.loading || request.error) {
    return <div className="page">{state}</div>;
  }
  const { film, participants, genres, awards, related } = request.data;
  return (
    <div className="film-page">
      <Poster film={film} className="film-hero phone-only" showYear={false} width={800} />
      <div className="page film">
        <Breadcrumbs items={[{ label: 'Каталог фільмів', to: '/' }, { label: film.title }]} />
        <div className="film-layout">
          <div className="film-side desktop-only">
            <Poster film={film} className="film-poster" width={600} />
            <FilmActions film={film} />
          </div>
          <div className="film-main">
            <div className="film-heading">
              <h1 className="page-title">{film.title}</h1>
              <span className="muted">{filmMeta(film)}</span>
              {genres.length > 0 && (
                <span className="tags film-genres">
                  {genres.map((genre) => (
                    <span key={genre.qid} className="tag">
                      {genre.name}
                    </span>
                  ))}
                </span>
              )}
            </div>
            <Awards awards={awards} />
            <div className="desktop-only">
              <ParticipantsTable participants={participants} film={film} />
            </div>
            <div className="phone-only">
              <ParticipantsAccordion participants={participants} film={film} />
            </div>
          </div>
        </div>
        <RelatedFilms related={related} />
      </div>
      <div className="film-actions-bar phone-only">
        <FilmActions film={film} />
      </div>
    </div>
  );
}
