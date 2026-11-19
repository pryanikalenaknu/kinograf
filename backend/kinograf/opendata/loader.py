"""Завантаження даних з Wikidata та перетворення їх на моделі предметної області."""

from dataclasses import dataclass
from datetime import date

from kinograf.models import Award, ExternalLinks, Film, Genre, Participation, Person, Role
from kinograf.opendata import queries
from kinograf.opendata.client import WikidataClient

ENTITY_PREFIX = "http://www.wikidata.org/entity/"


def entity_id(uri: str) -> str:
    """Виділяє ідентифікатор сутності з її адреси.

    Args:
        uri: Адреса сутності, наприклад ``http://www.wikidata.org/entity/Q25188``.

    Returns:
        Ідентифікатор сутності, наприклад ``Q25188``.
    """
    return uri.removeprefix(ENTITY_PREFIX)


def parse_date(value: str) -> date:
    """Перетворює дату Wikidata на об'єкт дати.

    Wikidata подає дати як ``2014-05-20T00:00:00Z``; якщо відомий лише рік,
    місяць і день дорівнюють нулю, і тоді береться 1 січня.

    Args:
        value: Значення дати з результату запиту.

    Returns:
        Дата виходу.
    """
    year, month, day = value.split("T")[0].lstrip("+").split("-")[:3]
    return date(int(year), max(int(month), 1), max(int(day), 1))


@dataclass
class LoadedParticipations:
    """Результат завантаження учасників фільмів.

    Attributes:
        people: Персоналії за ідентифікаторами.
        participations: Участь персоналій у фільмах з ролями.
    """

    people: dict[str, Person]
    participations: list[Participation]


class WikidataLoader:
    """Завантажує фільми, учасників, жанри й нагороди з Wikidata.

    Args:
        client: Клієнт SPARQL-точки доступу.
        min_year: Перший рік випуску фільмів у вибірці.
    """

    def __init__(self, client: WikidataClient, min_year: int) -> None:
        self.client = client
        self.min_year = min_year

    def fetch_films(self) -> list[Film]:
        """Завантажує основні дані фільмів.

        Returns:
            Фільми, впорядковані за датою виходу.
        """
        films = []
        for row in self.client.run(queries.films_query(self.min_year)):
            duration = row.get("duration")
            films.append(
                Film(
                    qid=entity_id(row["film"]),
                    title=row["filmLabel"],
                    release_date=parse_date(row["released"]),
                    duration_min=round(float(duration)) if duration else None,
                    image_url=row.get("poster"),
                )
            )
        return sorted(films, key=lambda film: (film.release_date, film.title))

    def fetch_participations(self) -> LoadedParticipations:
        """Завантажує персоналій і їхню участь у фільмах.

        Returns:
            Персоналії та записи участі без повторів.
        """
        people: dict[str, Person] = {}
        participations: set[Participation] = set()
        for row in self.client.run(queries.participations_query(self.min_year)):
            person_qid = entity_id(row["person"])
            people[person_qid] = Person(qid=person_qid, name=row["personLabel"])
            participations.add(
                Participation(
                    film_qid=entity_id(row["film"]),
                    person_qid=person_qid,
                    role=Role(row["role"]),
                )
            )
        ordered = sorted(participations, key=lambda p: (p.film_qid, p.role.value, p.person_qid))
        return LoadedParticipations(people=people, participations=ordered)

    def fetch_genres(self) -> dict[str, list[Genre]]:
        """Завантажує жанри фільмів.

        Returns:
            Жанри за ідентифікаторами фільмів.
        """
        genres: dict[str, list[Genre]] = {}
        for row in self.client.run(queries.genres_query(self.min_year)):
            genre = Genre(qid=entity_id(row["genre"]), name=row["genreLabel"])
            genres.setdefault(entity_id(row["film"]), []).append(genre)
        return genres

    def fetch_awards(self) -> dict[str, list[Award]]:
        """Завантажує нагороди фільмів.

        Returns:
            Нагороди за ідентифікаторами фільмів.
        """
        awards: dict[str, list[Award]] = {}
        for row in self.client.run(queries.awards_query(self.min_year)):
            award = Award(qid=entity_id(row["award"]), name=row["awardLabel"])
            awards.setdefault(entity_id(row["film"]), []).append(award)
        return awards

    def fetch_links(self) -> dict[str, ExternalLinks]:
        """Завантажує посилання фільмів і їхніх учасників на IMDb і Вікіпедію.

        Returns:
            Посилання за ідентифікаторами фільмів і персоналій; сутності без жодного
            посилання не включаються.
        """
        links: dict[str, ExternalLinks] = {}
        for query, subject in (
            (queries.film_links_query, "film"),
            (queries.person_links_query, "person"),
        ):
            for row in self.client.run(query(self.min_year)):
                if not any(row.get(name) for name in ("imdb", "ukwiki", "enwiki")):
                    continue
                qid = entity_id(row[subject])
                links[qid] = ExternalLinks(
                    qid=qid,
                    imdb_id=row.get("imdb"),
                    ukwiki=row.get("ukwiki"),
                    enwiki=row.get("enwiki"),
                )
        return links
