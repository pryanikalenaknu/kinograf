"""Спільна основа RDF-сховищ: завантаження з файлу, атомарна заміна й безпечні SPARQL-запити."""

import ctypes
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.plugins.sparql.sparql import Query


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
    """Результат запиту ``SELECT`` або ``ASK``.

    Attributes:
        columns: Назви змінних запиту в порядку їх оголошення.
        rows: Рядки результату; змінні без значення в рядку відсутні.
        truncated: Результат обрізано до найбільшої дозволеної кількості рядків.
        boolean: Відповідь на запит ``ASK``; для ``SELECT`` — ``None``.
        bindings: Ті самі рядки з типами значень у форматі SPARQL 1.1 Query Results JSON.
    """

    columns: list[str]
    rows: list[dict[str, str]]
    truncated: bool = False
    boolean: bool | None = None
    bindings: list[dict[str, dict[str, str]]] = field(default_factory=list)


def binding(term: object) -> dict[str, str]:
    """Описує значення результату запиту у форматі SPARQL 1.1 Query Results JSON.

    Args:
        term: Термін rdflib.

    Returns:
        Словник із типом (``uri``, ``literal``, ``bnode``), значенням і, за наявності,
        типом даних або мовою.
    """
    if isinstance(term, Literal):
        result = {"type": "literal", "value": str(term)}
        if term.language:
            result["xml:lang"] = term.language
        elif term.datatype:
            result["datatype"] = str(term.datatype)
        return result
    if isinstance(term, BNode):
        return {"type": "bnode", "value": str(term)}
    return {"type": "uri", "value": str(term)}


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


class GraphStore:
    """Базовий клас RDF-графа, збереженого у файлі Turtle, з обмеженими SPARQL-запитами.

    Окремо не використовується: підкласи задають префікси ``NAMESPACES``, дозволені
    форми запитів ``QUERY_FORMS`` і спосіб побудови графа.

    Граф замінюється цілком і атомарно; якщо файл змінив інший процес, граф
    перечитується під час наступного звернення.

    Args:
        path: Шлях до файлу Turtle.
        timeout: Найбільший час виконання SPARQL-запиту в секундах.
        max_rows: Найбільша кількість рядків результату запиту.
        max_concurrent: Найбільша кількість SPARQL-запитів, що виконуються одночасно.
    """

    NAMESPACES: dict[str, Namespace] = {}
    QUERY_FORMS: dict[str, str] = {"SelectQuery": "SELECT"}

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
        return len(self.graph())

    def load(self) -> None:
        """Завантажує граф із файлу, якщо файл існує."""
        if self.path.exists():
            version = self.path.stat().st_mtime_ns
            graph = self._empty_graph()
            graph.parse(self.path, format="turtle")
            self._graph = graph
            self._loaded_version = version

    def graph(self) -> Graph:
        """Повертає поточний граф, перечитавши файл, якщо його змінив інший процес.

        Так API бачить дані, записані командою ``python -m kinograf.update``, без перезапуску.

        Returns:
            Граф RDF.
        """
        if self.path.exists() and self.path.stat().st_mtime_ns != self._loaded_version:
            with self._reload_lock:
                if self.path.stat().st_mtime_ns != self._loaded_version:
                    self.load()
        return self._graph

    def query(self, sparql: str) -> SparqlResult:
        """Виконує дозволений запит з обмеженням часу й кількості рядків.

        Префікси з ``NAMESPACES`` оголошувати не обов'язково.

        Args:
            sparql: Текст запиту.

        Returns:
            Назви змінних і рядки результату або відповідь на ``ASK``.

        Raises:
            SparqlError: Якщо запит містить помилку, має недозволену форму або звертається
                до зовнішніх джерел через ``SERVICE`` чи ``FROM``.
            SparqlTimeoutError: Якщо запит не завершився за ``timeout`` секунд; його
                обчислення переривається.
            SparqlBusyError: Якщо вже виконується ``max_concurrent`` запитів.
        """
        prepared = self._prepare(sparql)
        graph = self.graph()
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

    def _replace(self, graph: Graph) -> None:
        """Атомарно записує новий граф у файл і робить його поточним."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        graph.serialize(temporary, format="turtle")
        os.replace(temporary, self.path)
        self._graph = graph
        self._loaded_version = self.path.stat().st_mtime_ns

    def _prepare(self, sparql: str) -> Query:
        """Розбирає запит і перевіряє, що він дозволений."""
        try:
            prepared = prepareQuery(sparql, initNs=self.NAMESPACES)
        except Exception as error:
            raise SparqlError(f"синтаксична помилка: {error}") from error
        if prepared.algebra.name not in self.QUERY_FORMS:
            forms = " і ".join(self.QUERY_FORMS.values())
            raise SparqlError(f"дозволено лише запити {forms}")
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
            if prepared.algebra.name == "AskQuery":
                outcome["result"] = SparqlResult([], [], boolean=bool(result.askAnswer))
                return
            columns = ordered_columns(sparql, result.vars)
            rows, bindings = [], []
            for row in result:
                if time.monotonic() > deadline:
                    raise SparqlTimeoutError
                if len(rows) == self.max_rows:
                    outcome["result"] = SparqlResult(columns, rows, True, bindings=bindings)
                    return
                values = {str(var): row[var] for var in result.vars if row[var] is not None}
                rows.append({name: str(value) for name, value in values.items()})
                bindings.append({name: binding(value) for name, value in values.items()})
            outcome["result"] = SparqlResult(columns, rows, bindings=bindings)
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

    @classmethod
    def _empty_graph(cls) -> Graph:
        """Створює порожній граф з оголошеними префіксами ``NAMESPACES``."""
        graph = Graph(bind_namespaces="core")
        for prefix, namespace in cls.NAMESPACES.items():
            graph.bind(prefix, namespace)
        return graph
