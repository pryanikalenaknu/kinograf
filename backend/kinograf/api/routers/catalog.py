"""Каталог, картка фільму, сторінка персоналії й списки для фільтрів."""

from fastapi import APIRouter, HTTPException, status

from kinograf.api.dependencies import FiltersDep, PageParam, ServicesDep, SortParam, TextParam
from kinograf.api.schemas import EntityOut, FilmDetailsOut, PageOut, PersonOut, PersonProfileOut

router = APIRouter(tags=["каталог"])


@router.get("/films", response_model=PageOut)
def search_films(
    services: ServicesDep,
    filters: FiltersDep,
    q: TextParam = "",
    sort: SortParam = "year",
    page: PageParam = 1,
) -> PageOut:
    """Шукає фільми за назвою й фільтрами, по 12 на сторінці."""
    return PageOut.model_validate(services.catalog.search(q, filters, sort, page))


@router.get("/films/{qid}", response_model=FilmDetailsOut)
def film_details(qid: str, services: ServicesDep) -> FilmDetailsOut:
    """Повертає картку фільму."""
    details = services.films.details(qid)
    if details is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "фільм не знайдено")
    return FilmDetailsOut.model_validate(details)


@router.get("/people/{qid}", response_model=PersonProfileOut)
def person_profile(qid: str, services: ServicesDep) -> PersonProfileOut:
    """Повертає сторінку персоналії."""
    profile = services.people.profile(qid)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "персоналію не знайдено")
    return PersonProfileOut.model_validate(profile)


@router.get("/genres", response_model=list[EntityOut])
def genres(services: ServicesDep) -> list[EntityOut]:
    """Повертає жанри для фільтра каталогу."""
    return [EntityOut.model_validate(genre) for genre in services.catalog.genres()]


@router.get("/directors", response_model=list[PersonOut])
def directors(services: ServicesDep) -> list[PersonOut]:
    """Повертає режисерів для фільтра каталогу."""
    return [PersonOut.model_validate(person) for person in services.catalog.directors()]
