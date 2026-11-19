"""Картка фільму."""

from kinograf.repositories import FilmRepository, LinkRepository, PersonRepository
from kinograf.services.dto import EntityLinks, FilmDetails, RelatedFilm

RELATED_LIMIT = 8


class FilmService:
    """Збирає дані для картки фільму.

    Args:
        films: Сховище фільмів.
        people: Сховище персоналій.
        links: Сховище посилань на інші набори.
        base_url: Базова адреса застосунку для постійних адрес.
    """

    def __init__(
        self,
        films: FilmRepository,
        people: PersonRepository,
        links: LinkRepository,
        base_url: str,
    ) -> None:
        self._films = films
        self._people = people
        self._links = links
        self._base_url = base_url

    def details(self, qid: str) -> FilmDetails | None:
        """Повертає фільм з учасниками, жанрами, нагородами, пов'язаними фільмами й посиланнями.

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
            links=EntityLinks.build(self._base_url, "film", qid, self._links.get(qid)),
        )
