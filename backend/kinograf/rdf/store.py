"""Локальний RDF-граф фільмів і персоналій у термінах Wikidata: побудова, обхід і експорт."""

from rdflib import RDFS, XSD, Graph, Literal, Namespace, URIRef

from kinograf.models import Award, ExternalLinks, Film, Genre, Participation, Person, Role
from kinograf.rdf.base import (
    GraphStore,
    SparqlBusyError,
    SparqlError,
    SparqlResult,
    SparqlTimeoutError,
    interrupt,
    ordered_columns,
)

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


def entity(uri: URIRef) -> str:
    """Повертає ідентифікатор сутності Wikidata з її URI.

    Args:
        uri: URI сутності.

    Returns:
        Ідентифікатор, наприклад ``Q25188``.
    """
    return str(uri).removeprefix(str(WD))


class RdfStore(GraphStore):
    """Зберігає дані каталогу як RDF-граф у термінах Wikidata і файлі Turtle.

    Цей граф — робоча копія даних Wikidata для SPARQL-консолі, графа зв'язків
    і перевірки SHACL.

    Args:
        path: Шлях до файлу ``graph.ttl``.
        timeout: Найбільший час виконання SPARQL-запиту в секундах.
        max_rows: Найбільша кількість рядків результату запиту.
        max_concurrent: Найбільша кількість SPARQL-запитів, що виконуються одночасно.
    """

    NAMESPACES = NAMESPACES

    def rebuild(
        self,
        films: list[Film],
        people: list[Person],
        participations: list[Participation],
        genres: dict[str, list[Genre]],
        awards: dict[str, list[Award]],
        links: dict[str, ExternalLinks] | None = None,
    ) -> None:
        """Будує граф заново з даних каталогу й зберігає його у файл.

        Args:
            films: Фільми.
            people: Персоналії.
            participations: Участь персоналій у фільмах.
            genres: Жанри за ідентифікаторами фільмів.
            awards: Нагороди за ідентифікаторами фільмів.
            links: Посилання на інші набори; з них у граф потрапляє ідентифікатор IMDb ``P345``.
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
        for item in (links or {}).values():
            if item.imdb_id:
                graph.add((WD[item.qid], WDT.P345, Literal(item.imdb_id)))
        self._replace(graph)

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
        graph = self.graph()
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
        graph = self.graph()
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
        graph = self.graph()
        if qids is None:
            return graph.serialize(format="turtle")
        part = self._empty_graph()
        for qid in qids:
            for _, prop, value in graph.triples((WD[qid], None, None)):
                part.add((WD[qid], prop, value))
                for label in graph.objects(value, RDFS.label):
                    part.add((value, RDFS.label, label))
        return part.serialize(format="turtle")

    @staticmethod
    def _links(graph: Graph, qid: str) -> list[tuple[str, str, str]]:
        """Повертає всі ребра «фільм — роль — персоналія», що торкаються сутності."""
        node = WD[qid]
        links = []
        for role, prop in ROLE_PROPERTIES.items():
            links += [(qid, role.value, entity(person)) for person in graph.objects(node, prop)]
            links += [(entity(film), role.value, qid) for film in graph.subjects(prop, node)]
        return sorted(links)


__all__ = [
    "NAMESPACES",
    "WD",
    "WDT",
    "RdfStore",
    "SparqlBusyError",
    "SparqlError",
    "SparqlResult",
    "SparqlTimeoutError",
    "entity",
    "interrupt",
    "ordered_columns",
]
