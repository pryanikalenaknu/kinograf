"""Тести сховища фільмів: пошук, фільтри, сортування, пагінація, пов'язані фільми."""

from dataclasses import replace
from datetime import date

import pytest

from kinograf.models import Award, Film, Genre
from kinograf.repositories import FilmFilters, FilmRepository
from kinograf.repositories.films import fts_query
from tests import sample_data


@pytest.fixture
def films(filled_database) -> FilmRepository:
    return FilmRepository(filled_database)


def qids(found):
    return [film.qid for film in found[0]]


def test_get_returns_film_with_all_fields(films):
    film = films.get("Q1")
    assert film == sample_data.FILMS[0]
    assert film.year == 2014


def test_get_unknown_film_returns_none(films):
    assert films.get("Q999") is None


def test_search_without_conditions_sorts_by_year_descending(films):
    found = films.search("", FilmFilters())
    assert qids(found) == ["Q6", "Q2", "Q5", "Q4", "Q1", "Q3", "Q7"]
    assert found[1] == 7


def test_search_sorts_by_title_in_ukrainian_alphabet(films):
    found = films.search("", FilmFilters(), sort="title")
    titles = [film.title for film in found[0]]
    assert titles == [
        "Атлантида",
        "Відблиск",
        "Земля блакитна, ніби апельсин",
        "Їжак",
        "Мамай",
        "Плем'я",
        "Поводир",
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("плем'я", ["Q1"]),
        ("ЗЕМЛЯ", ["Q2"]),
        ("пов", ["Q4"]),
        ("блакитна апельсин", ["Q2"]),
        ("блакитна мамай", []),
        ("   ", ["Q6", "Q2", "Q5", "Q4", "Q1", "Q3", "Q7"]),
    ],
)
def test_search_by_title(films, text, expected):
    assert qids(films.search(text, FilmFilters())) == expected


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        (FilmFilters(year_from=2019), ["Q6", "Q2", "Q5"]),
        (FilmFilters(year_to=2003), ["Q3", "Q7"]),
        (FilmFilters(year_from=2014, year_to=2019), ["Q5", "Q4", "Q1"]),
        (FilmFilters(period="1991-2013"), ["Q3", "Q7"]),
        (FilmFilters(period="2014-now"), ["Q6", "Q2", "Q5", "Q4", "Q1"]),
        (FilmFilters(genre="Q17013749"), ["Q4", "Q3"]),
        (FilmFilters(director="Q12"), ["Q6", "Q5"]),
        (FilmFilters(director="Q14"), []),
        (FilmFilters(has_cast=True), ["Q6", "Q5", "Q1"]),
    ],
)
def test_search_by_each_filter(films, filters, expected):
    assert qids(films.search("", filters)) == expected


def test_filters_combine(films):
    filters = FilmFilters(period="2014-now", genre="Q130232", has_cast=True, year_to=2020)
    assert qids(films.search("", filters)) == ["Q5", "Q1"]


def test_text_and_filters_combine(films):
    assert qids(films.search("атлантида", FilmFilters(director="Q12"))) == ["Q5"]
    assert qids(films.search("атлантида", FilmFilters(director="Q11"))) == []


def test_search_paginates_and_counts_all_results(films):
    first = films.search("", FilmFilters(), page=1, page_size=3)
    third = films.search("", FilmFilters(), page=3, page_size=3)
    assert qids(first) == ["Q6", "Q2", "Q5"]
    assert qids(third) == ["Q7"]
    assert first[1] == third[1] == 7


def test_search_without_page_size_returns_everything(films):
    assert len(films.search("", FilmFilters(), page_size=None)[0]) == 7


def test_fts_query_quotes_words_as_prefixes():
    assert fts_query('Плем\'я "OR" *') == '"плем"* "я"* "or"*'
    assert fts_query("  ") == ""


def test_related_orders_by_shared_people_then_genres_then_year(films):
    related = films.related("Q4")
    assert [(film.qid, people, genres) for film, people, genres in related] == [
        ("Q3", 2, 2),
        ("Q6", 0, 1),
        ("Q5", 0, 1),
        ("Q1", 0, 1),
    ]


def test_related_respects_limit_and_excludes_film_itself(films):
    related = films.related("Q5", limit=2)
    assert [film.qid for film, _, _ in related] == ["Q6", "Q4"]


def test_related_is_empty_without_people_and_genres(films):
    assert films.related("Q7") == []


def test_genres_and_awards_of_film(films):
    assert [genre.name for genre in films.genres_of("Q3")] == ["драма", "історичний фільм"]
    assert [award.qid for award in films.awards_of("Q5")] == ["Q101"]
    assert films.awards_of("Q7") == []


def test_genres_by_film_for_several_films(films):
    genres = films.genres_by_film(["Q3", "Q7"])
    assert [genre.name for genre in genres["Q3"]] == ["драма", "історичний фільм"]
    assert genres["Q7"] == []


def test_all_genres_sorted_by_name(films):
    assert [genre.name for genre in films.all_genres()] == [
        "документальний фільм",
        "драма",
        "історичний фільм",
    ]


def test_replace_all_counts_added_films(database):
    added, changed = FilmRepository(database).replace_all(
        sample_data.FILMS, sample_data.GENRES, sample_data.AWARDS
    )
    assert (added, changed) == (7, 0)


def test_replace_all_counts_changed_and_replaces_data(films):
    renamed = [replace(sample_data.FILMS[0], title="Плем'я (2014)"), *sample_data.FILMS[1:6]]
    new_film = Film("Q8", "Носоріг", date(2021, 9, 5))
    genres = {**sample_data.GENRES, "Q2": [Genre("Q130232", "драма")]}
    awards = {"Q2": sample_data.AWARDS["Q2"], "Q5": [Award("Q102", "Інша нагорода")]}
    added, changed = films.replace_all([*renamed, new_film], genres, awards)
    assert (added, changed) == (1, 3)
    assert films.get("Q7") is None
    assert qids(films.search("плем'я 2014", FilmFilters())) == ["Q1"]
    assert qids(films.search("носоріг", FilmFilters())) == ["Q8"]
    assert [award.qid for award in films.awards_of("Q5")] == ["Q102"]


def test_replace_all_with_same_data_changes_nothing(films):
    result = films.replace_all(sample_data.FILMS, sample_data.GENRES, sample_data.AWARDS)
    assert result == (0, 0)
