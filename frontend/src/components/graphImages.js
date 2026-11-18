/** Зображення вузлів графа: кружок із ініціалами персоналії у вигляді SVG. */

import { escapeXml, initials } from './format.js';

/**
 * Будує data-URI SVG-кружка з ініціалами; текст екранується, тож будь-яке ім'я дає коректний SVG.
 *
 * @param {string} name ім'я персоналії
 * @param {string} color колір кружка
 */
export function personImage(name, color) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48"><circle cx="24" cy="24" r="22" fill="${escapeXml(color)}"/><text x="24" y="29" text-anchor="middle" font-family="Inter, sans-serif" font-size="15" font-weight="600" fill="#FFFFFF">${escapeXml(initials(name))}</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}
