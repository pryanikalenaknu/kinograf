/** Постер фільму: зображення з Wikimedia Commons або градієнт із назвою. */

import { useState } from 'react';

function gradientAngle(qid) {
  const digits = Number(qid.replace(/\D/g, '')) || 0;
  return `${140 + (digits % 10) * 11}deg`;
}

function thumbnail(url, width) {
  const secure = url.replace(/^http:\/\/commons\.wikimedia\.org\//, 'https://commons.wikimedia.org/');
  return secure.includes('Special:FilePath') ? `${secure}?width=${width}` : secure;
}

export function Poster({ film, className = '', width = 400, showYear = true }) {
  const [failed, setFailed] = useState(false);
  const label = `Постер: ${film.title}, ${film.year}`;
  return (
    <div
      className={`poster ${className}`}
      role="img"
      aria-label={label}
      style={{ '--poster-angle': gradientAngle(film.qid) }}
    >
      {film.image_url && !failed && (
        <img
          src={thumbnail(film.image_url, width)}
          alt=""
          loading="lazy"
          onError={() => setFailed(true)}
        />
      )}
      {(!film.image_url || failed) && (
        <span className="poster-caption">
          <span className="poster-title">{film.title}</span>
          {showYear && <span className="poster-year">{film.year}</span>}
        </span>
      )}
    </div>
  );
}
