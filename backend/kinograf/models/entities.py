"""Сутності предметної області: фільми, персоналії, їхні ролі, жанри й нагороди."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/"


def wikidata_url(qid: str) -> str:
    """Повертає адресу сторінки сутності у Wikidata.

    Args:
        qid: Ідентифікатор сутності, наприклад ``Q25188``.

    Returns:
        Повна адреса сторінки сутності.
    """
    return WIKIDATA_ENTITY_URL + qid


class Role(StrEnum):
    """Роль персоналії у створенні фільму."""

    DIRECTOR = "director"
    SCREENWRITER = "screenwriter"
    COMPOSER = "composer"
    CAST = "cast"


@dataclass(frozen=True)
class Film:
    """Фільм з Wikidata.

    Attributes:
        qid: Ідентифікатор фільму у Wikidata.
        title: Назва українською, а за її відсутності англійською.
        release_date: Найраніша дата виходу.
        duration_min: Тривалість у хвилинах, якщо вказана.
        image_url: Адреса зображення у Wikimedia Commons, якщо вказане.
    """

    qid: str
    title: str
    release_date: date
    duration_min: int | None = None
    image_url: str | None = None

    @property
    def year(self) -> int:
        """Рік виходу фільму."""
        return self.release_date.year

    @property
    def wikidata_url(self) -> str:
        """Адреса сторінки фільму у Wikidata."""
        return wikidata_url(self.qid)


@dataclass(frozen=True)
class Person:
    """Персоналія, що брала участь у створенні фільмів.

    Attributes:
        qid: Ідентифікатор персоналії у Wikidata.
        name: Ім'я українською, а за його відсутності англійською.
    """

    qid: str
    name: str

    @property
    def wikidata_url(self) -> str:
        """Адреса сторінки персоналії у Wikidata."""
        return wikidata_url(self.qid)


@dataclass(frozen=True)
class Participation:
    """Участь персоналії у фільмі в певній ролі.

    Attributes:
        film_qid: Ідентифікатор фільму.
        person_qid: Ідентифікатор персоналії.
        role: Роль персоналії у фільмі.
    """

    film_qid: str
    person_qid: str
    role: Role


@dataclass(frozen=True)
class Genre:
    """Жанр фільму.

    Attributes:
        qid: Ідентифікатор жанру у Wikidata.
        name: Назва жанру.
    """

    qid: str
    name: str


@dataclass(frozen=True)
class Award:
    """Нагорода, отримана фільмом.

    Attributes:
        qid: Ідентифікатор нагороди у Wikidata.
        name: Назва нагороди.
    """

    qid: str
    name: str


@dataclass
class UpdateLog:
    """Запис журналу оновлень даних з Wikidata.

    Attributes:
        started_at: Час початку оновлення.
        status: Стан оновлення: ``running``, ``success`` або ``error``.
        finished_at: Час завершення оновлення.
        films_added: Кількість нових фільмів.
        films_changed: Кількість змінених фільмів.
        message: Опис помилки, якщо оновлення не вдалося.
        stage: Поточний етап оновлення, а після завершення — останній розпочатий.
        id: Ідентифікатор запису в базі даних.
    """

    started_at: datetime
    status: str = "running"
    finished_at: datetime | None = None
    films_added: int = 0
    films_changed: int = 0
    message: str = ""
    stage: str = ""
    id: int | None = None
