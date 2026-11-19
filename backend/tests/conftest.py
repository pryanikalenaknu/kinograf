"""Спільні тестові дані: підставний клієнт Wikidata з заготовленими відповідями."""

import pytest

from kinograf.opendata import queries
from kinograf.rdf import LinkedDataStore, RdfStore
from kinograf.repositories import Database, FilmRepository, PersonRepository
from tests import sample_data

FILM = "http://www.wikidata.org/entity/"


class FakeClient:
    """Клієнт, що повертає заготовлені рядки залежно від типу запиту."""

    def __init__(self, responses: dict[str, list[dict[str, str]]]) -> None:
        self.responses = responses
        self.queries: list[str] = []

    def run(self, query: str) -> list[dict[str, str]]:
        """Запам'ятовує запит і повертає рядки для його типу."""
        self.queries.append(query)
        for marker, rows in self.responses.items():
            if marker in query:
                return rows
        return []


@pytest.fixture
def fake_client() -> FakeClient:
    """Клієнт із відповідями на всі чотири запити завантажувача."""
    return FakeClient(
        {
            "(MIN(?date) AS ?released)": [
                {
                    "film": FILM + "Q2",
                    "filmLabel": "Земля блакитна, ніби апельсин",
                    "released": "2020-01-25T00:00:00Z",
                    "duration": "74",
                },
                {
                    "film": FILM + "Q1",
                    "filmLabel": "Плем'я",
                    "released": "2014-05-21T00:00:00Z",
                    "duration": "132.0",
                    "poster": "http://commons.wikimedia.org/wiki/Special:FilePath/Plemya.jpg",
                },
            ],
            "?personLabel": [
                {
                    "film": FILM + "Q1",
                    "person": FILM + "Q10",
                    "personLabel": "Мирослав Слабошпицький",
                    "role": "director",
                },
                {
                    "film": FILM + "Q1",
                    "person": FILM + "Q10",
                    "personLabel": "Мирослав Слабошпицький",
                    "role": "screenwriter",
                },
                {
                    "film": FILM + "Q1",
                    "person": FILM + "Q10",
                    "personLabel": "Мирослав Слабошпицький",
                    "role": "director",
                },
                {
                    "film": FILM + "Q2",
                    "person": FILM + "Q20",
                    "personLabel": "Ірина Цілик",
                    "role": "director",
                },
            ],
            "?genreLabel": [
                {"film": FILM + "Q1", "genre": FILM + "Q130232", "genreLabel": "драма"},
                {
                    "film": FILM + "Q2",
                    "genre": FILM + "Q93204",
                    "genreLabel": "документальний фільм",
                },
            ],
            "?awardLabel": [
                {"film": FILM + "Q2", "award": FILM + "Q100", "awardLabel": "Премія «Сандерс»"},
            ],
            "GROUP BY ?person": [
                {
                    "person": FILM + "Q10",
                    "imdb": "nm5752123",
                    "ukwiki": "Мирослав Слабошпицький",
                    "enwiki": "Myroslav Slaboshpytskyi",
                },
                {"person": FILM + "Q20"},
            ],
            "AS ?ukwiki": [
                {
                    "film": FILM + "Q1",
                    "imdb": "tt3904770",
                    "ukwiki": "Плем'я (фільм)",
                    "enwiki": "The Tribe (2014 film)",
                },
                {"film": FILM + "Q2", "ukwiki": "Земля блакитна, ніби апельсин"},
            ],
        }
    )


@pytest.fixture
def all_queries() -> list[str]:
    """Усі чотири запити з межею 1991 року."""
    return [
        queries.films_query(1991),
        queries.participations_query(1991),
        queries.genres_query(1991),
        queries.awards_query(1991),
    ]


@pytest.fixture
def database(tmp_path) -> Database:
    """Порожня база даних у тимчасовій теці."""
    database = Database(tmp_path / "kinograf.db")
    database.create_schema()
    return database


@pytest.fixture
def filled_database(database) -> Database:
    """База даних із тестовим набором з ``sample_data``."""
    FilmRepository(database).replace_all(sample_data.FILMS, sample_data.GENRES, sample_data.AWARDS)
    PersonRepository(database).replace_all(
        list(sample_data.PEOPLE.values()), sample_data.PARTICIPATIONS
    )
    return database


@pytest.fixture
def rdf_store(tmp_path) -> RdfStore:
    """RDF-граф, побудований з тестового набору й збережений у тимчасовій теці."""
    store = RdfStore(tmp_path / "graph.ttl")
    store.rebuild(
        sample_data.FILMS,
        list(sample_data.PEOPLE.values()),
        sample_data.PARTICIPATIONS,
        sample_data.GENRES,
        sample_data.AWARDS,
    )
    return store


@pytest.fixture
def linked_store(tmp_path) -> LinkedDataStore:
    """Опублікований граф тестового набору з базовою адресою ``http://kino.test``."""
    store = LinkedDataStore(tmp_path / "linked.ttl", "http://kino.test/")
    store.publish(
        sample_data.FILMS,
        list(sample_data.PEOPLE.values()),
        sample_data.PARTICIPATIONS,
        sample_data.GENRES,
        sample_data.AWARDS,
        sample_data.LINKS,
    )
    return store
