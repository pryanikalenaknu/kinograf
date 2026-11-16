"""Локальний RDF-граф фільмів і персоналій: побудова, SPARQL-запити, обхід і експорт."""

import ctypes
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from rdflib import RDFS, XSD, Graph, Literal, Namespace, URIRef
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.plugins.sparql.sparql import Query

from kinograf.models import Award, Film, Genre, Participation, Person, Role

WD = Namespace("http://www.wikidata.org/entity/")
WDT = Namespace("http://www.wikidata.org/prop/direct/")

NAMESPACES = {"wd": WD, "wdt": WDT, "rdfs": RDFS, "xsd": XSD}

ROLE_PROPERTIES = {
    Role.DIRECTOR: WDT.P57,
    Role.SCREENWRITER: WDT.P58,
    Role.COMPOSER: WDT.P86,
    Role.CAST: WDT.P161,
}

FILM_CLASS = WD.Q11424
HUMAN_CLASS = WD.Q5
UKRAINE = WD.Q212
LANGUAGE = "uk"


class SparqlError(Exception):
    """SPARQL-запит неправильний або заборонений."""


class SparqlTimeoutError(SparqlError):
    """SPARQL-запит не завершився за відведений час."""


class SparqlBusyError(SparqlError):
    """Одночасно виконується найбільша дозволена кількість SPARQL-запитів."""


def interrupt(thread: threading.Thread) -> None:
    """Перериває потік, піднявши в ньому ``SparqlTimeoutError`` на найближчій інструкції Python.

    Потоки Python не можна зупинити ззовні; так обчислення rdflib, яке ще триває після
    перевищення часу, завершується й звільняє процесор.

    Args:
        thread: Потік виконання запиту.
    """
    ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_ulong(thread.ident), ctypes.py_object(SparqlTimeoutError)
    )


@dataclass
class SparqlResult:
    """Результат запиту ``SELECT``.

    Attributes:
        columns: Назви змінних запиту в порядку їх оголошення.
        rows: Рядки результату; змінні без значення в рядку відсутні.
        truncated: Результат обрізано до найбільшої дозволеної кількості рядків.
    """

    columns: list[str]
    rows: list[dict[str, str]]
    truncated: bool = False


def ordered_columns(sparql: str, variables: list) -> list[str]:
    """Впорядковує змінні результату за першою появою в тексті запиту.

    Для ``SELECT *`` rdflib повертає змінні в довільному порядку; так стовпці
    йдуть у тому порядку, у якому їх написав користувач.

    Args:
        sparql: Текст запиту.
        variables: Змінні результату.

    Returns:
        Назви змінних.
    """
    positions = {}
    for var in variables:
        found = re.search(rf"[?$]{re.escape(str(var))}\b", sparql)
        positions[str(var)] = found.start() if found else len(sparql)
    return sorted(positions, key=positions.__getitem__)


def entity(uri: URIRef) -> str:
    """Повертає ідентифікатор сутності Wikidata з її URI.

    Args:
        uri: URI сутності.

    Returns:
        Ідентифікатор, наприклад ``Q25188``.
    """
    return str(uri).removeprefix(str(WD))


class RdfStore:
    """Зберігає дані каталогу як RDF-граф у термінах Wikidata і файлі Turtle.

    Args:
        path: Шлях до файлу ``graph.ttl``.
        timeout: Найбільший час виконання SPARQL-запиту в секундах.
        max_rows: Найбільша кількість рядків результату запиту.
        max_concurrent: Найбільша кількість SPARQL-запитів, що виконуються одночасно.
    """

    def __init__(
        self,
        path: str | Path,
        timeout: float = 10.0,
        max_rows: int = 1000,
        max_concurrent: int = 2,
    ) -> None:
        self.path = Path(path)
        self.timeout = timeout
        self.max_rows = max_rows
        self._graph = self._empty_graph()
        self._loaded_version: int | None = None
        self._reload_lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(max_concurrent)

    def __len__(self) -> int:
        """Повертає кількість трійок у графі."""
        return len(self._current())

    def load(self) -> None:
        """Завантажує граф із файлу, якщо файл існує."""
        if self.path.exists():
            version = self.path.stat().st_mtime_ns
            graph = self._empty_graph()
            graph.parse(self.path, format="turtle")
            self._graph = graph
            self._loaded_version = version

    def rebuild(
        self,
        films: list[Film],
        people: list[Person],
        participations: list[Participation],
        genres: dict[str, list[Genre]],
        awards: dict[str, list[Award]],
    ) -> None:
        """Будує граф заново з даних каталогу й зберігає його у файл.

        Args:
            films: Фільми.
            people: Персоналії.
            participations: Участь персоналій у фільмах.
            genres: Жанри за ідентифікаторами фільмів.
            awards: Нагороди за ідентифікаторами фільмів.
        """
        graph = self._empty_graph()
        for film in films:
            node = WD[film.qid]
            graph.add((node, WDT.P31, FILM_CLASS))
            graph.add((node, WDT.P495, UKRAINE))
            graph.add((node, RDFS.label, Literal(film.title, lang=LANGUAGE)))
            graph.add((node, WDT.P577, Literal(film.release_date, datatype=XSD.date)))
            if film.duration_min is not None:
                graph.add((node, WDT.P2047, Literal(film.duration_min, datatype=XSD.integer)))
            if film.image_url:
                graph.add((node, WDT.P18, URIRef(film.image_url)))
        for person in people:
            graph.add((WD[person.qid], WDT.P31, HUMAN_CLASS))
            graph.add((WD[person.qid], RDFS.label, Literal(person.name, lang=LANGUAGE)))
        for participation in participations:
            graph.add(
                (
                    WD[participation.film_qid],
                    ROLE_PROPERTIES[participation.role],
                    WD[participation.person_qid],
                )
            )
        for prop, items in ((WDT.P136, genres), (WDT.P166, awards)):
            for film_qid, film_items in items.items():
                for item in film_items:
                    graph.add((WD[film_qid], prop, WD[item.qid]))
                    graph.add((WD[item.qid], RDFS.label, Literal(item.name, lang=LANGUAGE)))
        self._save(graph)
        self._graph = graph
        self._loaded_version = self.path.stat().st_mtime_ns

    def query(self, sparql: str) -> SparqlResult:
        """Виконує запит ``SELECT`` з обмеженням часу й кількості рядків.

        Префікси ``wd``, ``wdt``, ``rdfs`` і ``xsd`` оголошувати не обов'язково.

        Args:
            sparql: Текст запиту.

        Returns:
            Назви змінних і рядки результату.

        Raises:
            SparqlError: Якщо запит містить помилку, не є ``SELECT`` або звертається
                до зовнішніх джерел через ``SERVICE`` чи ``FROM``.
            SparqlTimeoutError: Якщо запит не завершився за ``timeout`` секунд; його
                обчислення переривається.
            SparqlBusyError: Якщо вже виконується ``max_concurrent`` запитів.
        """
        prepared = self._prepare(sparql)
        graph = self._current()
        if not self._slots.acquire(blocking=False):
            raise SparqlBusyError("консоль зайнята іншими запитами, спробуйте за кілька секунд")
        deadline = time.monotonic() + self.timeout
        outcome: dict = {}
        worker = threading.Thread(
            target=self._collect,
            args=(graph, sparql, prepared, deadline, outcome),
            name="sparql-query",
            daemon=True,
        )
        worker.start()
        worker.join(self.timeout)
        if worker.is_alive():
            interrupt(worker)
        if worker.is_alive() or isinstance(outcome.get("error"), SparqlTimeoutError):
            raise SparqlTimeoutError(f"запит виконувався довше {self.timeout:g} с")
        if "error" in outcome:
            raise SparqlError(f"помилка виконання запиту: {outcome['error']}")
        return outcome["result"]

    def neighbours(self, qid: str, depth: int, limit: int = 150) -> list[tuple[str, str, str]]:
        """Знаходить зв'язки «фільм — персоналія» навколо сутності.

        Обхід іде в ширину; коли кількість вузлів досягає ``limit``, нові вузли не додаються.

        Args:
            qid: Ідентифікатор фільму або персоналії в центрі.
            depth: Глибина обходу: 1 — безпосередні сусіди, 2 — сусіди сусідів.
            limit: Найбільша кількість вузлів разом із центральним.

        Returns:
            Ребра як трійки «ідентифікатор фільму, роль, ідентифікатор персоналії».
        """
        graph = self._current()
        visited = {qid}
        frontier = [qid]
        edges: set[tuple[str, str, str]] = set()
        for _ in range(depth):
            next_frontier = []
            for node in frontier:
                for edge in self._links(graph, node):
                    other = edge[2] if edge[0] == node else edge[0]
                    if other not in visited and len(visited) < limit:
                        visited.add(other)
                        next_frontier.append(other)
                    edges.add(edge)
            frontier = next_frontier
        return sorted(edge for edge in edges if edge[0] in visited and edge[2] in visited)

    def entities(self, qids: list[str]) -> dict[str, tuple[str, str]]:
        """Повертає вид і назву фільмів та персоналій.

        Args:
            qids: Ідентифікатори сутностей.

        Returns:
            Для кожної відомої сутності — вид (``film`` або ``person``) і назва.
        """
        graph = self._current()
        found = {}
        for qid in qids:
            node = WD[qid]
            label = graph.value(node, RDFS.label)
            if (node, WDT.P31, FILM_CLASS) in graph:
                found[qid] = ("film", str(label))
            elif (node, WDT.P31, HUMAN_CLASS) in graph:
                found[qid] = ("person", str(label))
        return found

    def export_turtle(self, qids: list[str] | None = None) -> str:
        """Серіалізує граф або його частину у формат Turtle.

        Args:
            qids: Сутності, які треба описати; ``None`` — увесь граф. Для кожної
                сутності беруться всі її трійки й назви пов'язаних сутностей.

        Returns:
            Текст у форматі Turtle.
        """
        graph = self._current()
        if qids is None:
            return graph.serialize(format="turtle")
        part = self._empty_graph()
        for qid in qids:
            for _, prop, value in graph.triples((WD[qid], None, None)):
                part.add((WD[qid], prop, value))
                for label in graph.objects(value, RDFS.label):
                    part.add((value, RDFS.label, label))
        return part.serialize(format="turtle")

    def _current(self) -> Graph:
        """Повертає граф, перечитавши файл, якщо його змінив інший процес.

        Так API бачить дані, записані командою ``python -m kinograf.update``, без перезапуску.
        """
        if self.path.exists() and self.path.stat().st_mtime_ns != self._loaded_version:
            with self._reload_lock:
                if self.path.stat().st_mtime_ns != self._loaded_version:
                    self.load()
        return self._graph

    def _save(self, graph: Graph) -> None:
        """Атомарно записує граф у файл Turtle."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        graph.serialize(temporary, format="turtle")
        os.replace(temporary, self.path)

    def _prepare(self, sparql: str) -> Query:
        """Розбирає запит і перевіряє, що він дозволений."""
        try:
            prepared = prepareQuery(sparql, initNs=NAMESPACES)
        except Exception as error:
            raise SparqlError(f"синтаксична помилка: {error}") from error
        if prepared.algebra.name != "SelectQuery":
            raise SparqlError("дозволено лише запити SELECT")
        if prepared.algebra.get("datasetClause") or self._contains(
            prepared.algebra, "ServiceGraphPattern"
        ):
            raise SparqlError("звернення до зовнішніх джерел (FROM, SERVICE) заборонено")
        return prepared

    def _collect(
        self, graph: Graph, sparql: str, prepared: Query, deadline: float, outcome: dict
    ) -> None:
        """Виконує розібраний запит і кладе в ``outcome`` результат або помилку.

        Рядки збираються, доки не мине час або не буде досягнуто ліміту рядків. Після
        завершення звільняє місце для наступного запиту.
        """
        try:
            result = graph.query(prepared)
            columns = ordered_columns(sparql, result.vars)
            rows = []
            for row in result:
                if time.monotonic() > deadline:
                    raise SparqlTimeoutError
                if len(rows) == self.max_rows:
                    outcome["result"] = SparqlResult(columns, rows, truncated=True)
                    return
                rows.append(
                    {str(var): str(row[var]) for var in result.vars if row[var] is not None}
                )
            outcome["result"] = SparqlResult(columns, rows)
        except Exception as error:
            outcome["error"] = error
        finally:
            self._slots.release()

    @classmethod
    def _contains(cls, node: object, name: str) -> bool:
        """Перевіряє, чи містить дерево алгебри запиту вузол із даною назвою."""
        if isinstance(node, CompValue):
            return node.name == name or any(cls._contains(value, name) for value in node.values())
        if isinstance(node, list):
            return any(cls._contains(value, name) for value in node)
        return False

    @staticmethod
    def _links(graph: Graph, qid: str) -> list[tuple[str, str, str]]:
        """Повертає всі ребра «фільм — роль — персоналія», що торкаються сутності."""
        node = WD[qid]
        links = []
        for role, prop in ROLE_PROPERTIES.items():
            links += [(qid, role.value, entity(person)) for person in graph.objects(node, prop)]
            links += [(entity(film), role.value, qid) for film in graph.subjects(prop, node)]
        return sorted(links)

    @staticmethod
    def _empty_graph() -> Graph:
        """Створює порожній граф з оголошеними префіксами."""
        graph = Graph()
        for prefix, namespace in NAMESPACES.items():
            graph.bind(prefix, namespace)
        return graph
