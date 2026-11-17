"""Картка фільму."""

from kinograf.repositories import FilmRepository, PersonRepository
from kinograf.services.dto import FilmDetails, RelatedFilm

RELATED_LIMIT = 8


class FilmService:
    """Збирає дані для картки фільму.

    Args:
        films: Сховище фільмів.
        people: Сховище персоналій.
    """

    def __init__(self, films: FilmRepository, people: PersonRepository) -> None:
        self._films = films
        self._people = people

    def details(self, qid: str) -> FilmDetails | None:
        """Повертає фільм з учасниками, жанрами, нагородами й пов'язаними фільмами.

        Args:
            qid: Ідентифікатор фільму.

        Returns:
            Дані картки або ``None``, якщо фільму немає.
        """
        film = self._films.get(qid)
        if film is None:
            return None
        return FilmDetails(
            film=film,
            participants=self._people.participants(qid),
            genres=self._films.genres_of(qid),
            awards=self._films.awards_of(qid),
            related=[
                RelatedFilm(film=related, shared_people=people, shared_genres=genres)
                for related, people, genres in self._films.related(qid, RELATED_LIMIT)
            ],
        )
