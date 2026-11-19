"""Тести завантажувача: перетворення рядків Wikidata на моделі."""

from datetime import date

import pytest

from kinograf.models import ExternalLinks, Role, wikidata_url, wikipedia_path
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


def test_fetch_links_merges_films_and_people(fake_client):
    links = WikidataLoader(fake_client, 1991).fetch_links()
    assert set(links) == {"Q1", "Q2", "Q10"}
    assert links["Q1"].imdb_id == "tt3904770"
    assert links["Q2"].imdb_id is None
    assert links["Q10"].enwiki == "Myroslav Slaboshpytskyi"


def test_external_link_addresses():
    film = ExternalLinks("Q1", "tt3904770", "Плем'я (фільм)", "The Tribe (2014 film)")
    assert film.imdb_url == "https://www.imdb.com/title/tt3904770/"
    assert film.ukwiki_url == (
        "https://uk.wikipedia.org/wiki/%D0%9F%D0%BB%D0%B5%D0%BC'%D1%8F_(%D1%84%D1%96%D0%BB%D1%8C%D0%BC)"
    )
    assert film.dbpedia_uri == "http://dbpedia.org/resource/The_Tribe_(2014_film)"
    person = ExternalLinks("Q10", "nm5752123", enwiki="Myroslav Slaboshpytskyi")
    assert person.imdb_url == "https://www.imdb.com/name/nm5752123/"
    assert person.ukwiki_url is None


@pytest.mark.parametrize(
    ("title", "path"),
    [
        ("Land Is Blue as an Orange", "Land_Is_Blue_as_an_Orange"),
        ("Rhino (2021 film)", "Rhino_(2021_film)"),
        ("Iron's Will, Inc.", "Iron's_Will,_Inc."),
        ("Mr. Jones/Stories", "Mr._Jones%2FStories"),
        (
            "Земля блакитна",
            "%D0%97%D0%B5%D0%BC%D0%BB%D1%8F_%D0%B1%D0%BB%D0%B0%D0%BA%D0%B8%D1%82%D0%BD%D0%B0",
        ),
    ],
)
def test_wikipedia_path(title, path):
    assert wikipedia_path(title) == path


def test_unknown_imdb_id_gives_no_address():
    assert ExternalLinks("Q1", imdb_id="co0012345").imdb_url is None
    assert ExternalLinks("Q1").imdb_url is None
