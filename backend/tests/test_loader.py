"""Тести завантажувача: перетворення рядків Wikidata на моделі."""

from datetime import date

from kinograf.models import Role, wikidata_url
from kinograf.opendata import WikidataLoader
from kinograf.opendata.loader import entity_id, parse_date


def test_entity_id_strips_prefix():
    assert entity_id("http://www.wikidata.org/entity/Q212") == "Q212"


def test_parse_date_full():
    assert parse_date("2014-05-21T00:00:00Z") == date(2014, 5, 21)


def test_parse_date_with_unknown_month_and_day():
    assert parse_date("1995-00-00T00:00:00Z") == date(1995, 1, 1)


def test_fetch_films_builds_sorted_films(fake_client):
    films = WikidataLoader(fake_client, 1991).fetch_films()
    assert [film.qid for film in films] == ["Q1", "Q2"]
    tribe = films[0]
    assert tribe.title == "Плем'я"
    assert tribe.year == 2014
    assert tribe.duration_min == 132
    assert tribe.image_url.endswith("Plemya.jpg")
    assert films[1].image_url is None


def test_fetch_participations_removes_duplicates_and_keeps_roles(fake_client):
    loaded = WikidataLoader(fake_client, 1991).fetch_participations()
    assert set(loaded.people) == {"Q10", "Q20"}
    roles_q1 = {p.role for p in loaded.participations if p.film_qid == "Q1"}
    assert roles_q1 == {Role.DIRECTOR, Role.SCREENWRITER}
    assert len(loaded.participations) == 3


def test_fetch_genres_and_awards_group_by_film(fake_client):
    loader = WikidataLoader(fake_client, 1991)
    genres = loader.fetch_genres()
    awards = loader.fetch_awards()
    assert [g.name for g in genres["Q1"]] == ["драма"]
    assert list(awards) == ["Q2"]


def test_loader_passes_minimal_year_to_queries(fake_client):
    WikidataLoader(fake_client, 2014).fetch_films()
    assert "FILTER(YEAR(?date) >= 2014)" in fake_client.queries[0]


def test_wikidata_url():
    assert wikidata_url("Q1") == "https://www.wikidata.org/wiki/Q1"


def test_film_and_person_link_to_wikidata(fake_client):
    loader = WikidataLoader(fake_client, 1991)
    film = loader.fetch_films()[0]
    person = loader.fetch_participations().people["Q10"]
    assert film.wikidata_url == "https://www.wikidata.org/wiki/Q1"
    assert person.wikidata_url == "https://www.wikidata.org/wiki/Q10"
