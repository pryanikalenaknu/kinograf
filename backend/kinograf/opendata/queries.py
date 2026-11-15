"""SPARQL-запити до Wikidata для отримання даних про українські фільми."""

PREFIXES = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX bd: <http://www.bigdata.com/rdf#>
"""

LABELS = 'SERVICE wikibase:label { bd:serviceParam wikibase:language "uk,en". }'

ROLE_PROPERTIES = {
    "director": "P57",
    "screenwriter": "P58",
    "composer": "P86",
    "cast": "P161",
}


def _ukrainian_films(min_year: int) -> str:
    """Повертає шаблон відбору українських фільмів, що вийшли не раніше заданого року."""
    return f"""  ?film wdt:P31 wd:Q11424 ;
        wdt:P495 wd:Q212 ;
        wdt:P577 ?date .
  FILTER(YEAR(?date) >= {min_year})"""


def films_query(min_year: int) -> str:
    """Будує запит основних даних фільмів.

    Для кожного фільму повертається одна строка: найраніша дата виходу,
    тривалість і одне зображення.

    Args:
        min_year: Перший рік випуску фільмів у вибірці.

    Returns:
        Текст SPARQL-запиту.
    """
    return f"""{PREFIXES}
SELECT ?film ?filmLabel (MIN(?date) AS ?released)
       (SAMPLE(?minutes) AS ?duration) (SAMPLE(?image) AS ?poster)
WHERE {{
{_ukrainian_films(min_year)}
  OPTIONAL {{ ?film wdt:P2047 ?minutes . }}
  OPTIONAL {{ ?film wdt:P18 ?image . }}
  {LABELS}
}}
GROUP BY ?film ?filmLabel"""


def participations_query(min_year: int) -> str:
    """Будує запит учасників фільмів з їхніми ролями.

    Args:
        min_year: Перший рік випуску фільмів у вибірці.

    Returns:
        Текст SPARQL-запиту.
    """
    pairs = " ".join(f'(wdt:{prop} "{role}")' for role, prop in ROLE_PROPERTIES.items())
    return f"""{PREFIXES}
SELECT DISTINCT ?film ?person ?personLabel ?role WHERE {{
{_ukrainian_films(min_year)}
  VALUES (?property ?role) {{ {pairs} }}
  ?film ?property ?person .
  {LABELS}
}}"""


def genres_query(min_year: int) -> str:
    """Будує запит жанрів фільмів.

    Args:
        min_year: Перший рік випуску фільмів у вибірці.

    Returns:
        Текст SPARQL-запиту.
    """
    return f"""{PREFIXES}
SELECT DISTINCT ?film ?genre ?genreLabel WHERE {{
{_ukrainian_films(min_year)}
  ?film wdt:P136 ?genre .
  {LABELS}
}}"""


def awards_query(min_year: int) -> str:
    """Будує запит нагород фільмів.

    Args:
        min_year: Перший рік випуску фільмів у вибірці.

    Returns:
        Текст SPARQL-запиту.
    """
    return f"""{PREFIXES}
SELECT DISTINCT ?film ?award ?awardLabel WHERE {{
{_ukrainian_films(min_year)}
  ?film wdt:P166 ?award .
  {LABELS}
}}"""
