/** Форматування чисел, дат і українських множин. */

const numberFormat = new Intl.NumberFormat('uk-UA');

/**
 * Обирає форму слова для числа: «1 фільм», «2 фільми», «5 фільмів».
 *
 * @param {number} count
 * @param {[string, string, string]} forms
 */
export function plural(count, [one, few, many]) {
  const lastTwo = count % 100;
  const last = count % 10;
  if (lastTwo >= 11 && lastTwo <= 14) {
    return many;
  }
  if (last === 1) {
    return one;
  }
  return last >= 2 && last <= 4 ? few : many;
}

export function filmsCount(count) {
  return `${formatNumber(count)} ${plural(count, ['фільм', 'фільми', 'фільмів'])}`;
}

export function formatNumber(value) {
  return numberFormat.format(value).replace(/[\u00a0\u202f]/g, ' ');
}

export function formatPercent(share) {
  return `${Math.round(share * 100)}%`;
}

/** Дата й час у форматі «20.10.2026, 03:00» за місцевим часом. */
export function formatDateTime(value) {
  const date = new Date(value);
  const pad = (number) => String(number).padStart(2, '0');
  return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()}, ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

/** Тривалість між двома моментами у форматі «2 хв 14 с». */
export function formatDuration(start, end) {
  const seconds = Math.max(0, Math.round((new Date(end) - new Date(start)) / 1000));
  const minutes = Math.floor(seconds / 60);
  const rest = String(seconds % 60).padStart(minutes ? 2 : 1, '0');
  return minutes ? `${minutes} хв ${rest} с` : `${rest} с`;
}

/** Ініціали для аватара: «Олесь Санін» → «ОС»; символи поза базовою площиною не розриваються. */
export function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => Array.from(part)[0].toLocaleUpperCase('uk'))
    .join('');
}

export const ROLE_LABELS = {
  director: { one: 'Режисер', many: 'Режисери', lower: 'режисер' },
  screenwriter: { one: 'Сценарист', many: 'Сценаристи', lower: 'сценарист' },
  composer: { one: 'Композитор', many: 'Композитори', lower: 'композитор' },
  cast: { one: 'Актори', many: 'Актори', lower: 'актор' },
};

export const ROLE_COLORS = {
  director: 'var(--color-role-director)',
  screenwriter: 'var(--color-role-writer)',
  composer: 'var(--color-role-composer)',
  cast: 'var(--color-role-actor)',
};

/** Ролі через кому: «режисер, сценарист». */
export function rolesText(roles) {
  return roles.map((role) => ROLE_LABELS[role].lower).join(', ');
}

/** Екранує текст для вставлення у розмітку XML або SVG. */
export function escapeXml(text) {
  return text.replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`);
}
