"""Перевірка якості записів за правилами SHACL."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from kinograf.api.dependencies import PageParam, ServicesDep
from kinograf.api.schemas import QualityPageOut, QualityReportOut
from kinograf.models import Severity

router = APIRouter(prefix="/quality", tags=["якість даних"])

TURTLE = "text/turtle; charset=utf-8"


@router.get("/rules", response_model=QualityReportOut)
def rules(services: ServicesDep) -> QualityReportOut:
    """Повертає зведення останньої перевірки: правила, рівні й кількість фільмів."""
    return QualityReportOut.model_validate(services.quality.report())


@router.get("/issues", response_model=QualityPageOut)
def issues(
    services: ServicesDep,
    rule: Annotated[str | None, Query(max_length=40)] = None,
    severity: Severity | None = None,
    page: PageParam = 1,
) -> QualityPageOut:
    """Повертає фільми із зауваженнями за правилом і рівнем, по 12 на сторінці."""
    if rule is not None and rule not in services.quality.rule_ids():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "невідоме правило")
    return QualityPageOut.model_validate(services.quality.issues(rule, severity, page))


@router.get("/shapes.ttl")
def shapes(services: ServicesDep) -> Response:
    """Повертає правила SHACL у Turtle."""
    return Response(
        services.quality.shapes_turtle(),
        media_type=TURTLE,
        headers={"Content-Disposition": 'attachment; filename="kinograf-shapes.ttl"'},
    )


@router.get("/report.ttl")
def report(services: ServicesDep) -> Response:
    """Повертає звіт останньої перевірки SHACL у Turtle."""
    content = services.quality.report_turtle()
    if content is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "перевірки ще не було")
    return Response(
        content,
        media_type=TURTLE,
        headers={"Content-Disposition": 'attachment; filename="kinograf-shacl-report.ttl"'},
    )
