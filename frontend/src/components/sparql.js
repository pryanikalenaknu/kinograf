/** Готові приклади SPARQL-запитів і підсвітка синтаксису для консолі. */

const PREFIXES = `PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>`;

export const EXAMPLES = [
  {
    label: 'Фільми за жанром',
    query: `${PREFIXES}
# Українські драми від 1991 року
SELECT ?filmLabel ?year WHERE {
  ?film wdt:P31 wd:Q11424 ;
        wdt:P136 wd:Q130232 ;
        wdt:P577 ?date ;
        rdfs:label ?filmLabel .
  BIND(YEAR(?date) AS ?year)
  FILTER(?year >= 1991)
}
ORDER BY DESC(?year)
LIMIT 50`,
  },
  {
    label: 'Режисери з найбільшою кількістю фільмів',
    query: `${PREFIXES}
SELECT ?directorLabel (COUNT(?film) AS ?films) WHERE {
  ?film wdt:P57 ?director .
  ?director rdfs:label ?directorLabel .
}
GROUP BY ?directorLabel
ORDER BY DESC(?films)
LIMIT 10`,
  },
  {
    label: 'Фільми одного актора',
    query: `${PREFIXES}
SELECT ?filmLabel ?year WHERE {
  ?actor rdfs:label "Богдан Ступка"@uk .
  ?film wdt:P161 ?actor ;
        rdfs:label ?filmLabel ;
        wdt:P577 ?date .
  BIND(YEAR(?date) AS ?year)
}
ORDER BY ?year`,
  },
];

const KEYWORDS = new Set(
  `SELECT WHERE PREFIX FILTER BIND AS ORDER BY DESC ASC LIMIT OFFSET OPTIONAL DISTINCT GROUP
  HAVING COUNT SUM MIN MAX AVG SAMPLE YEAR STR LANG LANGMATCHES REGEX CONTAINS UNION MINUS
  VALUES IN NOT EXISTS SERVICE IF COALESCE BOUND a`.split(/\s+/),
);

const TOKEN = /<[^>\s]*>|"[^"]*"(?:@[\w-]+|\^\^\S+)?|[?$]\w+|[A-Za-z_][\w-]*:[\w-]*|[A-Za-z_]\w*|\s+|./g;

/**
 * Розбиває рядок запиту на лексеми з типом для підсвітки.
 *
 * @param {string} line
 * @returns {{text: string, kind: string}[]}
 */
export function highlightLine(line) {
  if (/^\s*#/.test(line)) {
    return [{ text: line, kind: 'comment' }];
  }
  return [...line.matchAll(TOKEN)].map(([text]) => {
    let kind = 'plain';
    if (text.startsWith('<') && text.length > 1) {
      kind = 'iri';
    } else if (text.startsWith('"')) {
      kind = 'string';
    } else if (/^[?$]/.test(text) && text.length > 1) {
      kind = 'variable';
    } else if (text.includes(':')) {
      kind = 'prefixed';
    } else if (KEYWORDS.has(text.toUpperCase()) || text === 'a') {
      kind = 'keyword';
    }
    return { text, kind };
  });
}

/** Номер рядка з повідомлення про синтаксичну помилку rdflib, якщо він є. */
export function errorLine(message) {
  const match = message.match(/line:\s*(\d+)/);
  return match ? Number(match[1]) : null;
}
