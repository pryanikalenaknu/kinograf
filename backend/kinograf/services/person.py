"""Сторінка персоналії."""

from kinograf.repositories import PersonRepository
from kinograf.services.dto import FilmographyEntry, PersonProfile, RankedPerson

COLLABORATORS_LIMIT = 8


class PersonService:
    """Збирає дані для сторінки персоналії.

    Args:
        people: Сховище персоналій.
    """

    def __init__(self, people: PersonRepository) -> None:
        self._people = people

    def profile(self, qid: str) -> PersonProfile | None:
        """Повертає персоналію з фільмографією й постійними співробітниками.

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
        )
