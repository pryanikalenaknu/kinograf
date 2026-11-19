"""Публікація зв'язаних даних: узгодження формату, документи, опис набору й точка SPARQL."""

import csv
import io
import json
from datetime import datetime

from kinograf.rdf import CC0, FORMATS, LinkedDataStore
from kinograf.repositories import LogRepository
from kinograf.services.dto import OpenDataOverview

HTML = "text/html"
TURTLE = "text/turtle"
JSONLD = "application/ld+json"
SPARQL_JSON = "application/sparql-results+json"
CSV = "text/csv"

MEDIA_TYPES = {"ttl": f"{TURTLE}; charset=utf-8", "jsonld": JSONLD}
PAGES = {"film": "films", "person": "people"}
SOURCE = "https://www.wikidata.org/"


def parse_accept(accept: str) -> list[tuple[str, float]]:
    """Розбирає заголовок ``Accept`` на діапазони типів із вагами ``q``.

    Args:
        accept: Значення заголовка.

    Returns:
        Пари «діапазон типів у нижньому регістрі, вага від 0 до 1»; неправильна вага — 0.
    """
    ranges = []
    for part in accept.split(","):
        fields = [field.strip() for field in part.split(";")]
        media = fields[0].lower()
        if not media:
            continue
        weight = 1.0
        for parameter in fields[1:]:
            name, _, value = parameter.partition("=")
            if name.strip().lower() == "q":
                try:
                    weight = min(max(float(value), 0.0), 1.0)
                except ValueError:
                    weight = 0.0
        ranges.append((media, weight))
    return ranges


def negotiate_media(accept: str | None, offers: list[str]) -> str | None:
    """Обирає з запропонованих типів той, якому клієнт віддає перевагу.

    Для кожного типу береться вага найконкретнішого діапазону, що йому відповідає
    (``text/turtle``, потім ``text/*``, потім ``*/*``). Перемагає більша вага, за
    рівної — конкретніший діапазон, далі — порядок ``offers``.

    Args:
        accept: Значення заголовка ``Accept``; порожнє або ``None`` — приймається будь-що.
        offers: Типи, які може віддати сервер, у порядку переваги сервера.

    Returns:
        Обраний тип або ``None``, якщо жоден тип не прийнятний.
    """
    if not accept or not accept.strip():
        return offers[0]
    ranges = parse_accept(accept)
    best, best_score = None, None
    for index, offer in enumerate(offers):
        family = offer.split("/")[0]
        specificity, weight = -1, 0.0
        for media, q in ranges:
            level = {offer: 2, f"{family}/*": 1, "*/*": 0}.get(media, -1)
            if level > specificity:
                specificity, weight = level, q
        score = (weight, specificity, -index)
        if specificity >= 0 and weight > 0 and (best_score is None or score > best_score):
            best, best_score = offer, score
    return best


class LinkedDataService:
    """Віддає опубліковані дані за принципами зв'язаних даних.

    Args:
        store: Опублікований граф.
        logs: Журнал оновлень, з якого береться час останнього успішного оновлення.
    """

    def __init__(self, store: LinkedDataStore, logs: LogRepository) -> None:
        self._store = store
        self._logs = logs
        self.base_url = store.base_url

    def negotiate(self, kind: str, qid: str, accept: str | None) -> str | None:
        """Обирає, куди перенаправити запит до постійної адреси сутності.

        Args:
            kind: Вид сутності: ``film`` або ``person``.
            qid: Ідентифікатор у Wikidata.
            accept: Заголовок ``Accept`` запиту.

        Returns:
            Шлях документа Turtle чи JSON-LD або сторінки застосунку; ``None``, якщо
            сутність не опубліковано.
        """
        if kind not in PAGES or not self._store.contains(kind, qid):
            return None
        media = negotiate_media(accept, [HTML, TURTLE, JSONLD])
        if media == TURTLE:
            return f"/data/{kind}/{qid}.ttl"
        if media == JSONLD:
            return f"/data/{kind}/{qid}.jsonld"
        return f"/{PAGES[kind]}/{qid}"

    def document(self, kind: str, qid: str, fmt: str) -> bytes | None:
        """Серіалізує документ про сутність.

        Args:
            kind: Вид сутності: ``film`` або ``person``.
            qid: Ідентифікатор у Wikidata.
            fmt: Формат: ``ttl`` або ``jsonld``.

        Returns:
            Вміст документа або ``None``, якщо сутності чи формату немає.
        """
        if fmt not in FORMATS or not self._store.contains(kind, qid):
            return None
        return self._store.serialize(self._store.describe(kind, qid), fmt)

    def dataset_format(self, accept: str | None) -> str:
        """Обирає формат опису набору: JSON-LD, якщо клієнт віддає йому перевагу, інакше Turtle.

        Args:
            accept: Заголовок ``Accept`` запиту.

        Returns:
            ``ttl`` або ``jsonld``.
        """
        return "jsonld" if negotiate_media(accept, [TURTLE, JSONLD]) == JSONLD else "ttl"

    def dataset(self, fmt: str) -> bytes:
        """Серіалізує опис набору у VoID.

        Args:
            fmt: Формат: ``ttl`` або ``jsonld``.

        Returns:
            Вміст опису.
        """
        return self._store.serialize(self._store.void(self._modified()), fmt)

    def dump(self) -> bytes:
        """Повертає весь опублікований граф у Turtle.

        Returns:
            Вміст файлу ``linked.ttl`` або порожній граф, якщо набір ще не опубліковано.
        """
        graph = self._store.graph()
        if self._store.path.exists():
            return self._store.path.read_bytes()
        return self._store.serialize(graph, "ttl")

    def query(self, sparql: str, accept: str | None) -> tuple[bytes, str]:
        """Виконує запит до опублікованого графа за протоколом SPARQL 1.1.

        Args:
            sparql: Текст запиту ``SELECT`` або ``ASK``.
            accept: Заголовок ``Accept``: ``text/csv`` — таблиця CSV, інакше
                SPARQL 1.1 Query Results JSON.

        Returns:
            Вміст відповіді та її тип.

        Raises:
            SparqlError: Якщо запит неправильний, заборонений, триває довше 10 с або
                одночасно виконується забагато запитів.
        """
        result = self._store.query(sparql)
        if negotiate_media(accept, [SPARQL_JSON, "application/json", CSV]) == CSV:
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\r\n")
            if result.boolean is not None:
                writer.writerows([["boolean"], [str(result.boolean).lower()]])
            else:
                writer.writerow(result.columns)
                for row in result.bindings:
                    writer.writerow([csv_value(row.get(column)) for column in result.columns])
            return buffer.getvalue().encode(), f"{CSV}; charset=utf-8"
        if result.boolean is not None:
            body = {"head": {}, "boolean": result.boolean}
        else:
            body = {"head": {"vars": result.columns}, "results": {"bindings": result.bindings}}
        return json.dumps(body, ensure_ascii=False).encode(), SPARQL_JSON

    def overview(self) -> OpenDataOverview:
        """Збирає опис набору для екрана «Відкриті дані».

        Returns:
            Обсяг, ліцензія, набори зв'язків і адреси доступу до даних.
        """
        counts = self._store.entity_counts()
        return OpenDataOverview(
            base_url=self.base_url,
            license=str(CC0),
            source=SOURCE,
            modified=self._modified(),
            triples=len(self._store),
            films=counts["film"],
            people=counts["person"],
            linksets=self._store.linkset_counts(),
            endpoints={
                "void": f"{self.base_url}/.well-known/void",
                "dump": f"{self.base_url}/data/kinograf.ttl",
                "sparql": f"{self.base_url}/data/sparql",
            },
            example_film=self._store.example_film(),
        )

    def _modified(self) -> datetime | None:
        """Повертає час останнього успішного оновлення або ``None``."""
        last = self._logs.last_success()
        return last.finished_at if last else None


def csv_value(value: dict[str, str] | None) -> str:
    """Записує значення результату для таблиці SPARQL 1.1 CSV.

    Args:
        value: Значення у форматі SPARQL 1.1 Query Results JSON або ``None``.

    Returns:
        Текст комірки; порожній вузол — з префіксом ``_:``.
    """
    if value is None:
        return ""
    return f"_:{value['value']}" if value["type"] == "bnode" else value["value"]
