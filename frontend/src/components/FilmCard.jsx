/** Картка фільму в каталозі: вертикальна на десктопі, горизонтальна на телефоні. */

import { Link } from 'react-router-dom';
import { Poster } from './Poster.jsx';
import './FilmCard.css';

export function FilmCard({ item }) {
  const { film, directors, genres } = item;
  const directorNames = directors.map((person) => person.name).join(', ');
  return (
    <Link to={`/films/${film.qid}`} className="film-card">
      <Poster film={film} className="film-card-poster" />
      <div className="film-card-body">
        <span className="film-card-title">{film.title}</span>
        <span className="film-card-meta">
          <span>{film.year}</span>
          {directorNames && (
            <>
              <span className="film-card-sep"> · </span>
              <span className="film-card-director">{directorNames}</span>
            </>
          )}
        </span>
        {genres.length > 0 && (
          <span className="tags">
            {genres.map((genre) => (
              <span key={genre.qid} className="tag">
                {genre.name}
              </span>
            ))}
          </span>
        )}
      </div>
    </Link>
  );
}

export function FilmCardSkeleton() {
  return (
    <div className="film-card film-card-skeleton" aria-hidden="true">
      <div className="film-card-poster skeleton" />
      <div className="film-card-body">
        <div className="skeleton" style={{ height: 16, width: '80%' }} />
        <div className="skeleton" style={{ height: 12, width: '60%' }} />
      </div>
    </div>
  );
}
