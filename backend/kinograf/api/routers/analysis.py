"""Граф зв'язків, статистика й SPARQL-консоль."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from kinograf.api.dependencies import ServicesDep
from kinograf.api.schemas import GraphOut, QueryResultOut, SparqlRequest, StatsOut

router = APIRouter(tags=["аналіз"])


@router.get("/graph/{qid}", response_model=GraphOut)
def graph(
    qid: str,
    services: ServicesDep,
    depth: Annotated[int, Query(ge=1, le=2)] = 1,
) -> GraphOut:
    """Повертає граф зв'язків навколо фільму або персоналії, до 150 вузлів."""
    data = services.graph.neighbourhood(qid, depth)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "сутність не знайдено в графі")
    return GraphOut.model_validate(data)


@router.get("/stats", response_model=StatsOut)
def stats(services: ServicesDep) -> StatsOut:
    """Повертає статистику каталогу й показники якості даних."""
    return StatsOut.model_validate(services.stats.overview())


@router.post("/sparql", response_model=QueryResultOut)
def sparql(request: SparqlRequest, services: ServicesDep) -> QueryResultOut:
    """Виконує запит SELECT до локального RDF-графа: до 10 с і 1 000 рядків."""
    return QueryResultOut.model_validate(services.sparql.execute(request.query))
