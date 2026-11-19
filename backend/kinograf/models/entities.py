"""Сутності предметної області: фільми, персоналії, ролі, жанри, нагороди, посилання, зауваження."""

import builtins
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from urllib.parse import quote

WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/"
WIKIPEDIA_SAFE = "()_,'!*"


def wikidata_url(qid: str) -> str:
    """Повертає адресу сторінки сутності у Wikidata.

    Args:
        qid: Ідентифікатор сутності, наприклад ``Q25188``.

    Returns:
        Повна адреса сторінки сутності.
    """
    return WIKIDATA_ENTITY_URL + qid


def wikipedia_path(title: str) -> str:
    """Перетворює назву статті Вікіпедії на частину адреси, як це робить сама Вікіпедія.

    Args:
        title: Назва статті, наприклад ``Поводир (фільм)``.

    Returns:
        Назва з підкресленнями замість пробілів, закодована для адреси.
    """
    return quote(title.replace(" ", "_"), safe=WIKIPEDIA_SAFE)


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


@dataclass(frozen=True)
class ExternalLinks:
    """Посилання фільму або персоналії на інші набори даних.

    Attributes:
        qid: Ідентифікатор фільму або персоналії у Wikidata.
        imdb_id: Ідентифікатор IMDb (``tt…`` для фільму, ``nm…`` для персоналії).
        ukwiki: Назва статті української Вікіпедії.
        enwiki: Назва статті англійської Вікіпедії.
    """

    qid: str
    imdb_id: str | None = None
    ukwiki: str | None = None
    enwiki: str | None = None

    @property
    def imdb_url(self) -> str | None:
        """Адреса сторінки на IMDb або ``None`` для відсутнього чи невідомого ідентифікатора."""
        if not self.imdb_id:
            return None
        kind = {"tt": "title", "nm": "name"}.get(self.imdb_id[:2])
        return f"https://www.imdb.com/{kind}/{self.imdb_id}/" if kind else None

    @property
    def ukwiki_url(self) -> str | None:
        """Адреса статті української Вікіпедії."""
        return (
            f"https://uk.wikipedia.org/wiki/{wikipedia_path(self.ukwiki)}" if self.ukwiki else None
        )

    @property
    def dbpedia_uri(self) -> str | None:
        """URI ресурсу DBpedia, утвореного зі статті англійської Вікіпедії."""
        return f"http://dbpedia.org/resource/{wikipedia_path(self.enwiki)}" if self.enwiki else None


class Severity(StrEnum):
    """Рівень зауваження перевірки SHACL, від найсерйознішого."""

    VIOLATION = "violation"
    WARNING = "warning"
    INFO = "info"

    @property
    def rank(self) -> int:
        """Повертає місце рівня: 0 — помилка, 1 — попередження, 2 — підказка."""
        return list(Severity).index(self)


@dataclass(frozen=True)
class QualityIssue:
    """Зауваження до запису фільму у Wikidata за одним правилом SHACL.

    Attributes:
        film_qid: Ідентифікатор фільму.
        rule: Ідентифікатор правила, наприклад ``director``.
        severity: Рівень зауваження.
        message: Повідомлення правила.
        property: Властивість Wikidata, яку треба виправити, наприклад ``P57``; для назви —
            ``None``.
        value: Значення, що порушує правило, наприклад тривалість ``5345``.
    """

    film_qid: str
    rule: str
    severity: Severity
    message: str
    property: str | None = None
    value: str | None = None

    @builtins.property
    def fix_url(self) -> str:
        """Адреса запису у Wikidata з якорем властивості, яку треба виправити."""
        anchor = f"#{self.property}" if self.property else ""
        return wikidata_url(self.film_qid) + anchor
