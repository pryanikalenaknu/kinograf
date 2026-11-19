"""Об'єкти передачі даних між сервісами й рівнем REST API."""

from dataclasses import dataclass
from datetime import datetime

from kinograf.models import Award, ExternalLinks, Film, Genre, Person, QualityIssue, Role
from kinograf.rdf import Linkset, QualityRule


@dataclass
class EntityLinks:
    """Постійна адреса сутності, її дані й відповідники в інших наборах.

    Attributes:
        uri: Постійна адреса ``{base}/id/{kind}/{qid}``.
        wikidata: Сторінка сутності у Wikidata.
        imdb: Сторінка на IMDb, якщо відома.
        wikipedia: Стаття української Вікіпедії, якщо є.
        dbpedia: Ресурс DBpedia, якщо є стаття англійської Вікіпедії.
        turtle: Документ про сутність у Turtle.
        jsonld: Документ про сутність у JSON-LD.
    """

    uri: str
    wikidata: str
    imdb: str | None
    wikipedia: str | None
    dbpedia: str | None
    turtle: str
    jsonld: str

    @staticmethod
    def build(base_url: str, kind: str, qid: str, links: ExternalLinks | None) -> "EntityLinks":
        """Будує посилання сутності від базової адреси застосунку.

        Args:
            base_url: Базова адреса застосунку.
            kind: Вид сутності: ``film`` або ``person``.
            qid: Ідентифікатор у Wikidata.
            links: Посилання на інші набори або ``None``, якщо їх немає.

        Returns:
            Посилання; відсутні набори мають значення ``None``.
        """
        base = base_url.rstrip("/")
        links = links or ExternalLinks(qid)
        return EntityLinks(
            uri=f"{base}/id/{kind}/{qid}",
            wikidata=f"https://www.wikidata.org/wiki/{qid}",
            imdb=links.imdb_url,
            wikipedia=links.ukwiki_url,
            dbpedia=links.dbpedia_uri,
            turtle=f"{base}/data/{kind}/{qid}.ttl",
            jsonld=f"{base}/data/{kind}/{qid}.jsonld",
        )


@dataclass
class OpenDataOverview:
    """Опис опублікованого набору для екрана «Відкриті дані».

    Attributes:
        base_url: Базова адреса застосунку.
        license: Адреса ліцензії CC0 1.0.
        source: Головна сторінка джерела даних.
        modified: Час останнього успішного оновлення.
        triples: Кількість трійок в опублікованому графі.
        films: Кількість опублікованих фільмів.
        people: Кількість опублікованих персоналій.
        linksets: Набори зв'язків у порядку Wikidata, Вікіпедія, IMDb, DBpedia.
        endpoints: Адреси опису набору (``void``), повного набору (``dump``)
            і точки SPARQL (``sparql``).
        example_film: Ідентифікатор фільму для прикладів або ``None``, якщо набір порожній.
    """

    base_url: str
    license: str
    source: str
    modified: datetime | None
    triples: int
    films: int
    people: int
    linksets: list[Linkset]
    endpoints: dict[str, str]
    example_film: str | None


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
        links: Постійна адреса й відповідники в інших наборах.
    """

    film: Film
    participants: dict[Role, list[Person]]
    genres: list[Genre]
    awards: list[Award]
    related: list[RelatedFilm]
    links: EntityLinks


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
        links: Постійна адреса й відповідники в інших наборах.
    """

    person: Person
    filmography: list[FilmographyEntry]
    collaborators: list[RankedPerson]
    links: EntityLinks


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


@dataclass
class RuleSummary:
    """Правило перевірки з кількістю фільмів, що його порушують.

    Attributes:
        rule: Правило.
        films: Кількість фільмів із зауваженням за цим правилом.
    """

    rule: QualityRule
    films: int


@dataclass
class QualityReport:
    """Зведення останньої перевірки за правилами SHACL.

    Attributes:
        checked_at: Час перевірки або ``None``, якщо перевірки ще не було.
        films_checked: Кількість перевірених фільмів.
        films_with_issues: Кількість фільмів хоча б з одним зауваженням.
        by_severity: Фільми за найсерйознішим зауваженням: ``violation``, ``warning``, ``info``.
        rules: Правила в порядку ``sh:order`` з кількістю фільмів.
    """

    checked_at: datetime | None
    films_checked: int
    films_with_issues: int
    by_severity: dict[str, int]
    rules: list[RuleSummary]


@dataclass
class FilmIssues:
    """Фільм з усіма його зауваженнями.

    Attributes:
        film: Фільм.
        issues: Зауваження від найсерйознішого, у порядку правил.
    """

    film: Film
    issues: list[QualityIssue]


@dataclass
class QualityPage:
    """Сторінка фільмів із зауваженнями.

    Attributes:
        items: Фільми сторінки.
        total: Кількість усіх відібраних фільмів.
        page: Номер сторінки, починаючи з 1.
    """

    items: list[FilmIssues]
    total: int
    page: int
