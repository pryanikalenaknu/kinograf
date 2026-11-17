"""SPARQL-консоль до локального RDF-графа."""

import time

from kinograf.rdf import RdfStore
from kinograf.services.dto import QueryResult


class SparqlService:
    """Виконує запити користувача до локального RDF-графа.

    Args:
        rdf: Локальний RDF-граф.
    """

    def __init__(self, rdf: RdfStore) -> None:
        self._rdf = rdf

    def execute(self, query: str) -> QueryResult:
        """Виконує запит ``SELECT`` і вимірює час виконання.

        Args:
            query: Текст запиту.

        Returns:
            Назви змінних, рядки результату й час виконання.

        Raises:
            SparqlError: Якщо запит неправильний, заборонений або виконується задовго.
        """
        started = time.perf_counter()
        result = self._rdf.query(query)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return QueryResult(
            columns=result.columns,
            rows=result.rows,
            truncated=result.truncated,
            elapsed_ms=elapsed_ms,
        )
