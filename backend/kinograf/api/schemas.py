"""Схеми відповідей і запитів REST API; описують дані для документації OpenAPI."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Schema(BaseModel):
    """Базова схема, що читає значення з атрибутів об'єктів передачі даних."""

    model_config = ConfigDict(from_attributes=True)


class FilmOut(Schema):
    """Фільм."""

    qid: str
    title: str
    release_date: date
    year: int
    duration_min: int | None
    image_url: str | None
    wikidata_url: str


class PersonOut(Schema):
    """Персоналія."""

    qid: str
    name: str
    wikidata_url: str


class EntityOut(Schema):
    """Жанр або нагорода."""

    qid: str
    name: str


class CatalogFilmOut(Schema):
    """Фільм у каталозі з режисерами й жанрами."""

    film: FilmOut
    directors: list[PersonOut]
    genres: list[EntityOut]


class PageOut(Schema):
    """Сторінка каталогу."""

    items: list[CatalogFilmOut]
    total: int
    page: int


class RelatedFilmOut(Schema):
    """Пов'язаний фільм із кількістю спільних учасників і жанрів."""

    film: FilmOut
    shared_people: int
    shared_genres: int


class EntityLinksOut(Schema):
    """Постійна адреса сутності, її дані й відповідники в інших наборах.

    Відсутні набори мають значення ``null``.
    """

    uri: str
    wikidata: str
    imdb: str | None
    wikipedia: str | None
    dbpedia: str | None
    turtle: str
    jsonld: str


class FilmDetailsOut(Schema):
    """Картка фільму.

    Учасники згруповані за ролями ``director``, ``screenwriter``, ``composer`` і ``cast``.
    """

    film: FilmOut
    participants: dict[str, list[PersonOut]]
    genres: list[EntityOut]
    awards: list[EntityOut]
    related: list[RelatedFilmOut]
    links: EntityLinksOut


class FilmographyEntryOut(Schema):
    """Рядок фільмографії."""

    film: FilmOut
    roles: list[str]


class RankedPersonOut(Schema):
    """Персоналія з кількістю фільмів."""

    person: PersonOut
    films: int


class PersonProfileOut(Schema):
    """Сторінка персоналії."""

    person: PersonOut
    filmography: list[FilmographyEntryOut]
    collaborators: list[RankedPersonOut]
    links: EntityLinksOut


class StatsOut(Schema):
    """Статистика й показники якості даних."""

    totals: dict[str, int]
    films_by_year: dict[int, int]
    genres_by_period: dict[str, dict[str, int]]
    top_directors: list[RankedPersonOut]
    top_actors: list[RankedPersonOut]
    completeness: dict[str, float]
    completeness_by_year: dict[int, dict[str, float]]
    last_updated: datetime | None


class GraphOut(Schema):
    """Граф зв'язків для vis-network."""

    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class SparqlRequest(BaseModel):
    """Запит до SPARQL-консолі."""

    query: str = Field(max_length=20_000)


class SparqlExportRequest(SparqlRequest):
    """Запит на експорт результату SPARQL-запиту."""

    format: Literal["csv", "json", "ttl"]


class QueryResultOut(Schema):
    """Результат SPARQL-запиту."""

    columns: list[str]
    rows: list[dict[str, str]]
    truncated: bool
    elapsed_ms: int


class UpdateLogOut(Schema):
    """Запис журналу оновлень."""

    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    films_added: int
    films_changed: int
    message: str
    stage: str


class LinksetOut(Schema):
    """Скільки фільмів і персоналій мають відповідник в іншому наборі."""

    target: str
    homepage: str
    predicate: str
    films: int
    people: int


class OpenDataOut(Schema):
    """Опис опублікованого набору для екрана «Відкриті дані».

    ``endpoints`` містить адреси ``void``, ``dump`` і ``sparql``.
    """

    base_url: str
    license: str
    source: str
    modified: datetime | None
    triples: int
    films: int
    people: int
    linksets: list[LinksetOut]
    endpoints: dict[str, str]
    example_film: str | None


class QualityRuleOut(Schema):
    """Правило перевірки SHACL."""

    rule: str
    name: str
    severity: Literal["violation", "warning", "info"]
    message: str
    property: str | None
    order: int


class RuleSummaryOut(Schema):
    """Правило з кількістю фільмів, що його порушують."""

    rule: QualityRuleOut
    films: int


class QualityReportOut(Schema):
    """Зведення останньої перевірки за правилами SHACL.

    ``by_severity`` — фільми за найсерйознішим зауваженням (``violation``, ``warning``,
    ``info``); ``checked_at`` — ``null``, якщо перевірки ще не було.
    """

    checked_at: datetime | None
    films_checked: int
    films_with_issues: int
    by_severity: dict[str, int]
    rules: list[RuleSummaryOut]


class QualityIssueOut(Schema):
    """Зауваження до запису фільму з посиланням на виправлення у Wikidata."""

    rule: str
    severity: Literal["violation", "warning", "info"]
    message: str
    property: str | None
    value: str | None
    fix_url: str


class FilmIssuesOut(Schema):
    """Фільм з усіма його зауваженнями."""

    film: FilmOut
    issues: list[QualityIssueOut]


class QualityPageOut(Schema):
    """Сторінка фільмів із зауваженнями, по 12 на сторінці."""

    items: list[FilmIssuesOut]
    total: int
    page: int
