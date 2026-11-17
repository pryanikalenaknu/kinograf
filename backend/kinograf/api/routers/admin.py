"""Адміністрування: запуск оновлення даних і журнал."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from kinograf.api.dependencies import ServicesDep, require_admin
from kinograf.api.schemas import UpdateLogOut
from kinograf.services import UpdateInProgressError

router = APIRouter(prefix="/admin", tags=["адміністрування"], dependencies=[Depends(require_admin)])


@router.get("/log", response_model=list[UpdateLogOut])
def update_log(services: ServicesDep) -> list[UpdateLogOut]:
    """Повертає останні записи журналу оновлень."""
    return [UpdateLogOut.model_validate(log) for log in services.update.history()]


@router.post("/update", response_model=UpdateLogOut, status_code=status.HTTP_202_ACCEPTED)
def start_update(services: ServicesDep, background: BackgroundTasks) -> UpdateLogOut:
    """Запускає оновлення даних у фоні; 409, якщо попереднє ще виконується."""
    try:
        log = services.update.start()
    except UpdateInProgressError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    response = UpdateLogOut.model_validate(log)
    background.add_task(services.update.run, log)
    return response


@router.get("/update/{log_id}", response_model=UpdateLogOut)
def update_status(log_id: int, services: ServicesDep) -> UpdateLogOut:
    """Повертає стан оновлення з поточним етапом."""
    log = services.update.log(log_id)
    if log is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "запис журналу не знайдено")
    return UpdateLogOut.model_validate(log)
