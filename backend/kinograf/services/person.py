"""Сторінка персоналії."""

from kinograf.repositories import LinkRepository, PersonRepository
from kinograf.services.dto import EntityLinks, FilmographyEntry, PersonProfile, RankedPerson

COLLABORATORS_LIMIT = 8


class PersonService:
    """Збирає дані для сторінки персоналії.

    Args:
        people: Сховище персоналій.
        links: Сховище посилань на інші набори.
        base_url: Базова адреса застосунку для постійних адрес.
    """

    def __init__(self, people: PersonRepository, links: LinkRepository, base_url: str) -> None:
        self._people = people
        self._links = links
        self._base_url = base_url

    def profile(self, qid: str) -> PersonProfile | None:
        """Повертає персоналію з фільмографією, постійними співробітниками й посиланнями.

        Ролі в одному фільмі об'єднуються в один рядок фільмографії.

        Args:
            qid: Ідентифікатор персоналії.

        Returns:
            Дані сторінки або ``None``, якщо персоналії немає.
        """
        person = self._people.get(qid)
        if person is None:
            return None
        entries: dict[str, FilmographyEntry] = {}
        for film, role in self._people.filmography(qid):
            entries.setdefault(film.qid, FilmographyEntry(film=film, roles=[])).roles.append(role)
        return PersonProfile(
            person=person,
            filmography=list(entries.values()),
            collaborators=[
                RankedPerson(person=collaborator, films=films)
                for collaborator, films in self._people.collaborators(qid, COLLABORATORS_LIMIT)
            ],
            links=EntityLinks.build(self._base_url, "person", qid, self._links.get(qid)),
        )
