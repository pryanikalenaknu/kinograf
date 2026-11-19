"""Зв'язані відкриті дані: постійні адреси, документи, опис набору й точка SPARQL.

Маршрути ``router`` підключаються без префікса ``/api``; усі їхні відповіді, зокрема
помилки, мають заголовки ``Vary: Accept`` і ``Access-Control-Allow-Origin: *``.
"""

import re
from collections.abc import Callable, Coroutine
from typing import Annotated, Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse
from fastapi.routing import APIRoute

from kinograf.api.dependencies import ServicesDep
from kinograf.api.schemas import OpenDataOut
from kinograf.rdf.linked import FORMATS
from kinograf.services import SparqlBusyError, SparqlError, SparqlTimeoutError
from kinograf.services.linkeddata import MEDIA_TYPES

QID = re.compile(r"Q[1-9][0-9]{0,11}")
MAX_QUERY = 20_000
MAX_BODY = 64 * 1024
LINKED_HEADERS = {"Vary": "Accept", "Access-Control-Allow-Origin": "*"}

AcceptHeader = Annotated[str | None, Header()]


class LinkedDataRoute(APIRoute):
    """Маршрут, що додає до кожної відповіді заголовки зв'язаних даних.

    Помилки повертаються простим текстом із тими самими заголовками, щоб їх могли
    прочитати й сторонні сайти.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """Обгортає обробник маршруту."""
        handler = super().get_route_handler()

        async def route(request: Request) -> Response:
            try:
                response = await handler(request)
            except HTTPException as error:
                response = PlainTextResponse(
                    str(error.detail), error.status_code, headers=error.headers
                )
            except SparqlError as error:
                response = sparql_failure(error)
            response.headers.update(LINKED_HEADERS)
            return response

        return route


def sparql_failure(error: SparqlError) -> PlainTextResponse:
    """Описує помилку SPARQL-запиту: зайнято — 429, перевищено час — 408, інше — 400.

    Args:
        error: Помилка запиту.

    Returns:
        Відповідь простим текстом.
    """
    if isinstance(error, SparqlBusyError):
        return PlainTextResponse(str(error), 429, headers={"Retry-After": "5"})
    code = 408 if isinstance(error, SparqlTimeoutError) else 400
    return PlainTextResponse(str(error), code)


def not_found() -> HTTPException:
    """Повертає помилку 404 для невідомої сутності."""
    return HTTPException(status.HTTP_404_NOT_FOUND, "сутність не знайдено в опублікованому наборі")


router = APIRouter(tags=["зв'язані дані"], route_class=LinkedDataRoute)
api = APIRouter(tags=["зв'язані дані"])


@router.get("/id/{kind}/{qid}", status_code=303)
@router.head("/id/{kind}/{qid}", include_in_schema=False)
def resource(kind: str, qid: str, services: ServicesDep, accept: AcceptHeader = None) -> Response:
    """Перенаправляє з постійної адреси на документ RDF або сторінку за заголовком ``Accept``.

    ``text/turtle`` — документ Turtle, ``application/ld+json`` — JSON-LD, інше — сторінка.
    """
    location = services.linked.negotiate(kind, qid, accept) if QID.fullmatch(qid) else None
    if location is None:
        raise not_found()
    return Response(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": location})


@router.get("/data/kinograf.ttl")
@router.head("/data/kinograf.ttl", include_in_schema=False)
def dump(services: ServicesDep) -> Response:
    """Повертає весь опублікований граф у Turtle."""
    return Response(services.linked.dump(), media_type=MEDIA_TYPES["ttl"])


@router.options("/data/sparql", include_in_schema=False)
def sparql_options() -> Response:
    """Відповідає на попередній запит CORS до точки SPARQL."""
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Accept, Content-Type",
            "Access-Control-Max-Age": "86400",
        },
    )


@router.get("/data/sparql")
@router.post("/data/sparql")
async def sparql(request: Request, services: ServicesDep, accept: AcceptHeader = None) -> Response:
    """Точка доступу SPARQL 1.1 до опублікованого графа.

    Запит передається як ``GET ?query=``, форма ``query=`` у ``POST`` або тіло
    ``application/sparql-query``. Дозволено ``SELECT`` і ``ASK`` до 10 с і 1 000 рядків;
    результат — ``application/sparql-results+json`` або ``text/csv`` за заголовком ``Accept``.
    """
    if request.method == "GET":
        parameters = {name: request.query_params.getlist(name) for name in request.query_params}
    else:
        parameters = await body_parameters(request)
    if "default-graph-uri" in parameters or "named-graph-uri" in parameters:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "вибір графів запиту не підтримується")
    queries = parameters.get("query", [])
    if len(queries) != 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "потрібен рівно один параметр query")
    if len(queries[0]) > MAX_QUERY:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, f"запит довший за {MAX_QUERY} символів"
        )
    content, media_type = await run_in_threadpool(services.linked.query, queries[0], accept)
    return Response(content, media_type=media_type)


async def body_parameters(request: Request) -> dict[str, list[str]]:
    """Читає параметри запиту SPARQL з тіла ``POST``.

    Форма розбирається ``urllib.parse.parse_qs``; тіло ``application/sparql-query``
    вважається текстом запиту.

    Args:
        request: HTTP-запит.

    Returns:
        Значення параметрів за назвами.

    Raises:
        HTTPException: 413 — тіло більше 64 КіБ; 415 — інший тип вмісту;
            400 — тіло не в UTF-8.
    """
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BODY:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "завелике тіло запиту")
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    try:
        text = bytes(body).decode("utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "тіло запиту не в UTF-8") from error
    if content_type == "application/x-www-form-urlencoded":
        return parse_qs(text, keep_blank_values=True, max_num_fields=20)
    if content_type == "application/sparql-query":
        return {"query": [text]}
    raise HTTPException(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        "очікується application/x-www-form-urlencoded або application/sparql-query",
    )


@router.get("/data/{kind}/{qid}.{fmt}")
@router.head("/data/{kind}/{qid}.{fmt}", include_in_schema=False)
def document(kind: str, qid: str, fmt: str, services: ServicesDep) -> Response:
    """Повертає документ про фільм або персоналію в Turtle (``.ttl``) чи JSON-LD (``.jsonld``)."""
    content = None
    if QID.fullmatch(qid) and fmt in FORMATS:
        content = services.linked.document(kind, qid, fmt)
    if content is None:
        raise not_found()
    return Response(content, media_type=MEDIA_TYPES[fmt])


@router.get("/.well-known/void")
@router.head("/.well-known/void", include_in_schema=False)
def void(services: ServicesDep, accept: AcceptHeader = None) -> Response:
    """Повертає опис набору у VoID: Turtle типово, JSON-LD за ``Accept: application/ld+json``."""
    fmt = services.linked.dataset_format(accept)
    return Response(services.linked.dataset(fmt), media_type=MEDIA_TYPES[fmt])


@api.get("/opendata", response_model=OpenDataOut)
def opendata(services: ServicesDep) -> OpenDataOut:
    """Повертає опис опублікованого набору для екрана «Відкриті дані»."""
    return OpenDataOut.model_validate(services.linked.overview())
