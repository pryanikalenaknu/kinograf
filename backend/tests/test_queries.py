"""Тести побудови SPARQL-запитів."""

from kinograf.opendata import queries


def test_every_query_selects_ukrainian_films(all_queries):
    for query in all_queries:
        assert "wdt:P31 wd:Q11424" in query
        assert "wdt:P495 wd:Q212" in query


def test_every_query_filters_by_minimal_year(all_queries):
    for query in all_queries:
        assert "FILTER(YEAR(?date) >= 1991)" in query


def test_minimal_year_is_configurable():
    assert "FILTER(YEAR(?date) >= 2014)" in queries.films_query(2014)


def test_labels_prefer_ukrainian(all_queries):
    for query in all_queries:
        assert 'wikibase:language "uk,en"' in query


def test_participations_query_covers_all_roles():
    query = queries.participations_query(1991)
    for prop in ("P57", "P58", "P86", "P161"):
        assert f"wdt:{prop}" in query


def test_films_query_returns_one_row_per_film():
    query = queries.films_query(1991)
    assert "GROUP BY ?film ?filmLabel" in query
    assert "MIN(?date)" in query
