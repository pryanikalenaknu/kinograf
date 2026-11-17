"""Створення застосунку FastAPI.

Запуск: ``uvicorn kinograf.api.app:create_app --factory``.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from kinograf import __version__
from kinograf.api.routers import admin, analysis, catalog, export
from kinograf.config import load_settings
from kinograf.services import Services, SparqlBusyError, SparqlError, SparqlTimeoutError


async def sparql_error(request: Request, error: SparqlError) -> JSONResponse:
    """Перетворює помилку SPARQL-запиту на відповідь з кодом стану.

    Неправильний запит — 400, перевищення часу — 408, зайнята консоль — 429.

    Args:
        request: HTTP-запит, під час якого сталася помилка.
        error: Помилка запиту.

    Returns:
        JSON-відповідь з описом помилки.
    """
    if isinstance(error, SparqlBusyError):
        return JSONResponse(
            {"detail": str(error)},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": "5"},
        )
    code = (
        status.HTTP_408_REQUEST_TIMEOUT
        if isinstance(error, SparqlTimeoutError)
        else status.HTTP_400_BAD_REQUEST
    )
    return JSONResponse({"detail": str(error)}, status_code=code)


def create_app(services: Services | None = None) -> FastAPI:
    """Створює застосунок з усіма маршрутами під префіксом ``/api``.

    Args:
        services: Сервіси застосунку; за замовчуванням створюються з налаштувань середовища.

    Returns:
        Застосунок FastAPI з документацією OpenAPI за адресою ``/api/docs``.
    """
    app = FastAPI(
        title="КіноГраф API",
        version=__version__,
        description="Довідник українських фільмів на основі відкритих даних Wikidata.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.services = services or Services.create(load_settings())
    app.add_exception_handler(SparqlError, sparql_error)
    for router in (catalog.router, analysis.router, export.router, admin.router):
        app.include_router(router, prefix="/api")
    return app
