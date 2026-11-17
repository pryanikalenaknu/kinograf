"""Експорт результатів каталогу й SPARQL-запитів у файли."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response

from kinograf.api.dependencies import FiltersDep, ServicesDep, SortParam, TextParam
from kinograf.api.schemas import SparqlExportRequest

router = APIRouter(prefix="/export", tags=["експорт"])

MEDIA_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "json": "application/json",
    "ttl": "text/turtle; charset=utf-8",
}


def attachment(content: bytes, name: str, fmt: str) -> Response:
    """Створює відповідь із файлом для завантаження.

    Args:
        content: Вміст файлу.
        name: Назва файлу без розширення.
        fmt: Формат, він же розширення файлу.

    Returns:
        HTTP-відповідь із заголовком ``Content-Disposition``.
    """
    return Response(
        content,
        media_type=MEDIA_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="{name}.{fmt}"'},
    )


@router.get("/films", response_class=Response)
def export_films(
    services: ServicesDep,
    filters: FiltersDep,
    fmt: Annotated[Literal["csv", "json", "ttl"], Query(alias="format")],
    q: TextParam = "",
    sort: SortParam = "year",
) -> Response:
    """Експортує всі знайдені фільми каталогу."""
    return attachment(services.export.export_films(fmt, q, filters, sort), "films", fmt)


@router.post("/sparql", response_class=Response)
def export_sparql(request: SparqlExportRequest, services: ServicesDep) -> Response:
    """Виконує SPARQL-запит і експортує його результат."""
    content = services.export.export_sparql(request.format, request.query)
    return attachment(content, "sparql", request.format)
