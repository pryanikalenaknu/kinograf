"""Каталог фільмів: пошук, фільтри й списки значень для фільтрів."""

from kinograf.models import Genre, Person
from kinograf.repositories import FilmFilters, FilmRepository, PersonRepository
from kinograf.services.dto import CatalogFilm, Page

PAGE_SIZE = 12


class CatalogService:
    """Шукає фільми для каталогу.

    Args:
        films: Сховище фільмів.
        people: Сховище персоналій.
    """

    def __init__(self, films: FilmRepository, people: PersonRepository) -> None:
        self._films = films
        self._people = people

    def search(self, text: str, filters: FilmFilters, sort: str = "year", page: int = 1) -> Page:
        """Повертає сторінку каталогу по ``PAGE_SIZE`` фільмів із режисерами й жанрами.

        Args:
            text: Слова з назви фільму.
            filters: Умови відбору.
            sort: Порядок: ``year`` або ``title``.
            page: Номер сторінки, починаючи з 1.

        Returns:
            Сторінка результатів.
        """
        films, total = self._films.search(text, filters, sort, page, PAGE_SIZE)
        qids = [film.qid for film in films]
        directors = self._people.directors_by_film(qids)
        genres = self._films.genres_by_film(qids)
        items = [
            CatalogFilm(film=film, directors=directors[film.qid], genres=genres[film.qid])
            for film in films
        ]
        return Page(items=items, total=total, page=page)

    def genres(self) -> list[Genre]:
        """Повертає жанри для фільтра каталогу.

        Returns:
            Жанри за абеткою.
        """
        return self._films.all_genres()

    def directors(self) -> list[Person]:
        """Повертає режисерів для фільтра каталогу.

        Returns:
            Режисери за абеткою.
        """
        return self._people.directors()
