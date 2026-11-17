"""Об'єкти передачі даних між сервісами й рівнем REST API."""

from dataclasses import dataclass
from datetime import datetime

from kinograf.models import Award, Film, Genre, Person, Role


@dataclass
class CatalogFilm:
    """Фільм у каталозі з режисерами й жанрами для картки.

    Attributes:
        film: Фільм.
        directors: Режисери.
        genres: Жанри.
    """

    film: Film
    directors: list[Person]
    genres: list[Genre]


@dataclass
class Page:
    """Сторінка результатів каталогу.

    Attributes:
        items: Фільми сторінки з режисерами й жанрами.
        total: Кількість усіх знайдених фільмів.
        page: Номер сторінки, починаючи з 1.
    """

    items: list[CatalogFilm]
    total: int
    page: int


@dataclass
class RelatedFilm:
    """Фільм, пов'язаний з іншим спільними учасниками або жанрами.

    Attributes:
        film: Пов'язаний фільм.
        shared_people: Кількість спільних учасників.
        shared_genres: Кількість спільних жанрів.
    """

    film: Film
    shared_people: int
    shared_genres: int


@dataclass
class FilmDetails:
    """Дані для картки фільму.

    Attributes:
        film: Фільм.
        participants: Учасники за ролями; роль без учасників має порожній список.
        genres: Жанри.
        awards: Нагороди.
        related: До 8 пов'язаних фільмів.
    """

    film: Film
    participants: dict[Role, list[Person]]
    genres: list[Genre]
    awards: list[Award]
    related: list[RelatedFilm]


@dataclass
class FilmographyEntry:
    """Рядок фільмографії персоналії.

    Attributes:
        film: Фільм.
        roles: Ролі персоналії в цьому фільмі.
    """

    film: Film
    roles: list[Role]


@dataclass
class RankedPerson:
    """Персоналія з кількістю фільмів для рейтингів і списку співробітників.

    Attributes:
        person: Персоналія.
        films: Кількість фільмів.
    """

    person: Person
    films: int


@dataclass
class PersonProfile:
    """Дані для сторінки персоналії.

    Attributes:
        person: Персоналія.
        filmography: Фільми від новіших до старіших.
        collaborators: До 8 постійних співробітників із кількістю спільних фільмів.
    """

    person: Person
    filmography: list[FilmographyEntry]
    collaborators: list[RankedPerson]


@dataclass
class Stats:
    """Дані для сторінок статистики й якості даних.

    Attributes:
        totals: Загальна кількість фільмів і персоналій (ключі ``films`` і ``people``).
        films_by_year: Кількість фільмів за роками.
        genres_by_period: Кількість фільмів за жанрами в періодах ``1991-2013`` і ``2014-now``.
        top_directors: Десять режисерів із найбільшою кількістю фільмів.
        top_actors: Десять акторів із найбільшою кількістю фільмів.
        completeness: Частка фільмів із режисером, акторами, жанром і постером.
        completeness_by_year: Ті самі частки за роками.
        last_updated: Час завершення останнього успішного оновлення.
    """

    totals: dict[str, int]
    films_by_year: dict[int, int]
    genres_by_period: dict[str, dict[str, int]]
    top_directors: list[RankedPerson]
    top_actors: list[RankedPerson]
    completeness: dict[str, float]
    completeness_by_year: dict[int, dict[str, float]]
    last_updated: datetime | None


@dataclass
class GraphData:
    """Вузли й ребра графа зв'язків для vis-network.

    Attributes:
        nodes: Вузли зі стовпцями ``id``, ``label``, ``type`` (``film`` або ``person``)
            і ``level`` (0 — центр, 1 або 2 — глибина).
        edges: Ребра зі стовпцями ``from`` (фільм), ``to`` (персоналія) і ``roles``.
    """

    nodes: list[dict]
    edges: list[dict]


@dataclass
class QueryResult:
    """Результат SPARQL-запиту для консолі.

    Attributes:
        columns: Назви змінних запиту.
        rows: Рядки результату.
        truncated: Результат обрізано до 1 000 рядків.
        elapsed_ms: Час виконання в мілісекундах.
    """

    columns: list[str]
    rows: list[dict[str, str]]
    truncated: bool
    elapsed_ms: int
