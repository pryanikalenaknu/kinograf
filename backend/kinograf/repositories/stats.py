"""Сховище статистичних показників і показників повноти даних."""

from kinograf.models import Person, Role
from kinograf.repositories.database import Database
from kinograf.repositories.films import PERIODS

COMPLETENESS_FIELDS = ("director", "cast", "genre", "poster")


class StatsRepository:
    """Обчислює зведені показники каталогу засобами SQL.

    Args:
        database: База даних застосунку.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    def totals(self) -> dict[str, int]:
        """Повертає загальну кількість фільмів і персоналій.

        Returns:
            Кількість за ключами ``films`` і ``people``.
        """
        with self._database.transaction() as connection:
            films = connection.execute("SELECT COUNT(*) FROM films").fetchone()[0]
            people = connection.execute("SELECT COUNT(*) FROM people").fetchone()[0]
        return {"films": films, "people": people}

    def films_by_year(self) -> dict[int, int]:
        """Повертає кількість фільмів за роками виходу.

        Returns:
            Кількість фільмів для кожного року, у порядку зростання років.
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                "SELECT year, COUNT(*) AS films FROM films GROUP BY year ORDER BY year"
            ).fetchall()
        return {row["year"]: row["films"] for row in rows}

    def genres_by_period(self) -> dict[str, dict[str, int]]:
        """Повертає кількість фільмів кожного жанру в періодах ``PERIODS``.

        Returns:
            Для кожного періоду — кількість фільмів за назвами жанрів, від більшої до меншої.
        """
        result = {}
        with self._database.transaction() as connection:
            for period, (year_from, year_to) in PERIODS.items():
                rows = connection.execute(
                    """SELECT genres.name, COUNT(DISTINCT films.qid) AS films
                       FROM genres
                       JOIN film_genres ON genre_qid = genres.qid
                       JOIN films ON films.qid = film_qid
                       WHERE films.year >= ? AND films.year <= COALESCE(?, films.year)
                       GROUP BY genres.qid
                       ORDER BY films DESC, genres.name COLLATE uk""",
                    (year_from, year_to),
                ).fetchall()
                result[period] = {row["name"]: row["films"] for row in rows}
        return result

    def top_people(self, role: Role, limit: int = 10) -> list[tuple[Person, int]]:
        """Повертає персоналій із найбільшою кількістю фільмів у даній ролі.

        Args:
            role: Роль у фільмі.
            limit: Найбільша кількість персоналій.

        Returns:
            Персоналія й кількість фільмів, від більшої кількості до меншої.
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                """SELECT people.*, COUNT(DISTINCT film_qid) AS films
                   FROM participations JOIN people ON people.qid = person_qid
                   WHERE role = ?
                   GROUP BY people.qid
                   ORDER BY films DESC, name COLLATE uk
                   LIMIT ?""",
                (role.value, limit),
            ).fetchall()
        return [(Person(qid=row["qid"], name=row["name"]), row["films"]) for row in rows]

    def completeness(self) -> dict[str, float]:
        """Повертає частку фільмів, для яких вказано режисера, акторів, жанр і постер.

        Returns:
            Частка від 0 до 1 для кожного поля з ``COMPLETENESS_FIELDS``.
        """
        flags = [flags for _, flags in self._film_flags()]
        return self._shares(flags)

    def completeness_by_year(self) -> dict[int, dict[str, float]]:
        """Повертає показники повноти окремо для кожного року виходу.

        Returns:
            Частки заповнення полів з ``COMPLETENESS_FIELDS`` за роками, у порядку зростання.
        """
        by_year: dict[int, list[tuple]] = {}
        for year, flags in self._film_flags():
            by_year.setdefault(year, []).append(flags)
        return {year: self._shares(flags) for year, flags in sorted(by_year.items())}

    def _film_flags(self) -> list[tuple[int, tuple]]:
        """Повертає рік кожного фільму й ознаки заповнення полів з ``COMPLETENESS_FIELDS``."""
        with self._database.transaction() as connection:
            rows = connection.execute(
                """SELECT year,
                          EXISTS (SELECT 1 FROM participations
                                  WHERE film_qid = qid AND role = ?) AS director,
                          EXISTS (SELECT 1 FROM participations
                                  WHERE film_qid = qid AND role = ?) AS "cast",
                          EXISTS (SELECT 1 FROM film_genres WHERE film_qid = qid) AS genre,
                          image_url IS NOT NULL AS poster
                   FROM films""",
                (Role.DIRECTOR.value, Role.CAST.value),
            ).fetchall()
        return [(row["year"], tuple(row[field] for field in COMPLETENESS_FIELDS)) for row in rows]

    @staticmethod
    def _shares(flags: list[tuple]) -> dict[str, float]:
        """Обчислює частку фільмів із заповненим полем для кожного поля."""
        total = len(flags)
        return {
            field: sum(film[index] for film in flags) / total if total else 0.0
            for index, field in enumerate(COMPLETENESS_FIELDS)
        }
