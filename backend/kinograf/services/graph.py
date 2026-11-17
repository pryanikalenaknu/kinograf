"""Граф зв'язків між фільмами й персоналіями."""

from kinograf.rdf import RdfStore
from kinograf.services.dto import GraphData

MAX_NODES = 150


class GraphService:
    """Будує граф зв'язків навколо фільму або персоналії.

    Args:
        rdf: Локальний RDF-граф.
    """

    def __init__(self, rdf: RdfStore) -> None:
        self._rdf = rdf

    def neighbourhood(self, qid: str, depth: int) -> GraphData | None:
        """Повертає вузли й ребра навколо сутності, не більше ``MAX_NODES`` вузлів.

        Кілька ролей персоналії в одному фільмі об'єднуються в одне ребро.

        Args:
            qid: Ідентифікатор фільму або персоналії в центрі.
            depth: Глибина: 1 або 2.

        Returns:
            Граф для vis-network або ``None``, якщо сутності немає в графі.
        """
        if qid not in self._rdf.entities([qid]):
            return None
        roles: dict[tuple[str, str], list[str]] = {}
        for film, role, person in self._rdf.neighbours(qid, depth, MAX_NODES):
            roles.setdefault((film, person), []).append(role)
        nearest = {
            film if person == qid else person for film, person in roles if qid in (film, person)
        }
        qids = sorted({qid} | {node for pair in roles for node in pair})
        nodes = [
            {
                "id": node,
                "label": label,
                "type": kind,
                "level": 0 if node == qid else 1 if node in nearest else 2,
            }
            for node, (kind, label) in self._rdf.entities(qids).items()
        ]
        edges = [
            {"from": film, "to": person, "roles": film_roles}
            for (film, person), film_roles in roles.items()
        ]
        return GraphData(nodes=nodes, edges=edges)
