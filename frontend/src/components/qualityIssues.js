/** Рівні й короткі назви зауважень перевірки за правилами SHACL. */

import { formatNumber } from './format.js';

export const ISSUES_PAGE_SIZE = 12;
const TAG_LIMIT = 5;

export const SEVERITIES = [
  { value: 'violation', label: 'помилка', filter: 'Помилки' },
  { value: 'warning', label: 'попередження', filter: 'Попередження' },
  { value: 'info', label: 'підказка', filter: 'Підказки' },
];

export const SEVERITY_LABELS = Object.fromEntries(SEVERITIES.map(({ value, label }) => [value, label]));

const TAGS = {
  'release-date': () => 'немає дати виходу',
  'duration-range': (issue) =>
    issue.value ? `тривалість ${formatNumber(Number(issue.value))} хв` : 'тривалість поза межами',
  'title-uk': () => 'немає назви українською',
  director: () => 'немає режисера',
  cast: () => 'немає акторів',
  genre: () => 'немає жанру',
  duration: () => 'немає тривалості',
  screenwriter: () => 'немає сценариста',
  image: () => 'немає зображення',
  announced: () => 'ще не вийшов',
};

/** Підказки про відсутні необов'язкові поля, які згортаються в «+N», коли зауважень багато. */
const MINOR = new Set(['duration', 'screenwriter', 'image']);

export function issueLabel(issue) {
  return TAGS[issue.rule]?.(issue) ?? issue.message;
}

/** Зауваження, що показуються тегами; решта згортається в «+N». */
export function visibleIssues(issues) {
  if (issues.length <= TAG_LIMIT) {
    return issues;
  }
  return issues.filter((issue) => issue.severity !== 'info' || !MINOR.has(issue.rule));
}
