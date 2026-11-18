/** Елементи сторінок фільму й персоналії: навігаційний шлях, учасник, тег ролі, «не вказано». */

import { Link } from 'react-router-dom';
import { initials, ROLE_COLORS, ROLE_LABELS } from './format.js';
import './People.css';

export function Breadcrumbs({ items }) {
  return (
    <nav className="breadcrumbs" aria-label="Навігаційний шлях">
      {items.map((item, index) => (
        <span key={item.label} className="breadcrumbs-item">
          {index > 0 && <span aria-hidden="true">→</span>}
          {item.to ? (
            <Link to={item.to} state={item.state}>
              {item.label}
            </Link>
          ) : (
            <span aria-current="page">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}

export function Avatar({ name, color, size = 'small' }) {
  return (
    <span
      className={`avatar avatar-${size}`}
      style={color ? { borderColor: color } : undefined}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  );
}

export function PersonChip({ person, role, from }) {
  return (
    <Link to={`/people/${person.qid}`} state={from && { from }} className="person-chip">
      <Avatar name={person.name} color={ROLE_COLORS[role]} />
      <span>{person.name}</span>
    </Link>
  );
}

export function RoleTag({ role }) {
  return (
    <span className="role-tag">
      <span className="role-dot" style={{ background: ROLE_COLORS[role] }} />
      {ROLE_LABELS[role].lower}
    </span>
  );
}

export function MissingData({ wikidataUrl }) {
  return (
    <div className="missing">
      <span>У відкритих даних не вказано</span>
      <a href={wikidataUrl} target="_blank" rel="noopener noreferrer">
        Доповнити у Wikidata ↗
      </a>
    </div>
  );
}
