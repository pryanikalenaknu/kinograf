"""Спільні залежності маршрутизаторів: сервіси, фільтри каталогу, перевірка ключа."""

import secrets
from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException, Query, Request, status

from kinograf.services import FilmFilters, Services

MIN_YEAR = 1800
MAX_YEAR = 2200


def get_services(request: Request) -> Services:
    """Повертає сервіси, створені під час запуску застосунку.

    Args:
        request: Поточний HTTP-запит.

    Returns:
        Сервіси застосунку.
    """
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services)]


YearParam = Annotated[int | None, Query(ge=MIN_YEAR, le=MAX_YEAR)]
EntityParam = Annotated[str | None, Query(max_length=32)]
TextParam = Annotated[str, Query(max_length=200)]
PageParam = Annotated[int, Query(ge=1, le=10_000)]


def film_filters(
    year_from: YearParam = None,
    year_to: YearParam = None,
    period: Literal["1991-2013", "2014-now"] | None = None,
    genre: EntityParam = None,
    director: EntityParam = None,
    has_cast: bool = False,
) -> FilmFilters:
    """Збирає фільтри каталогу з параметрів запиту.

    Args:
        year_from: Найменший рік виходу.
        year_to: Найбільший рік виходу.
        period: Період ``1991-2013`` або ``2014-now``.
        genre: Ідентифікатор жанру.
        director: Ідентифікатор режисера.
        has_cast: Лише фільми з акторами.

    Returns:
        Фільтри каталогу.
    """
    return FilmFilters(
        year_from=year_from,
        year_to=year_to,
        period=period,
        genre=genre,
        director=director,
        has_cast=has_cast,
    )


FiltersDep = Annotated[FilmFilters, Depends(film_filters)]
SortParam = Annotated[Literal["year", "title"], Query()]


def require_admin(
    services: ServicesDep,
    x_admin_key: Annotated[str | None, Header()] = None,
) -> None:
    """Пропускає запит лише з правильним ключем адміністратора в заголовку ``X-Admin-Key``.

    Якщо ключ у налаштуваннях не задано, адміністративні дії недоступні.

    Args:
        services: Сервіси застосунку з налаштуваннями.
        x_admin_key: Значення заголовка ``X-Admin-Key``.

    Raises:
        HTTPException: 401, якщо ключ відсутній або неправильний.
    """
    expected = services.settings.admin_key.encode()
    given = (x_admin_key or "").encode()
    if not expected or not given or not secrets.compare_digest(given, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "неправильний ключ адміністратора")
