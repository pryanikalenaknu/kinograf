"""Сховище персоналій: фільмографія, співробітники, учасники фільмів."""

from kinograf.models import Film, Participation, Person, Role
from kinograf.repositories.database import Database
from kinograf.repositories.films import film_from_row

ROLE_ORDER = (
    "CASE role "
    + " ".join(f"WHEN '{role.value}' THEN {index}" for index, role in enumerate(Role))
    + " END"
)


class PersonRepository:
    """Читає й записує персоналій та їхню участь у фільмах.

    Args:
        database: База даних застосунку.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self, qid: str) -> Person | None:
        """Повертає персоналію за ідентифікатором.

        Args:
            qid: Ідентифікатор персоналії.

        Returns:
            Персоналія або ``None``, якщо її немає в базі.
        """
        with self._database.transaction() as connection:
            row = connection.execute("SELECT * FROM people WHERE qid = ?", (qid,)).fetchone()
        return Person(qid=row["qid"], name=row["name"]) if row else None

    def filmography(self, qid: str) -> list[tuple[Film, Role]]:
        """Повертає фільми персоналії з ролями, від новіших до старіших.

        Args:
            qid: Ідентифікатор персоналії.

        Returns:
            Пари «фільм — роль»; фільм повторюється для кожної ролі.
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                f"""SELECT films.*, role FROM participations
                    JOIN films ON films.qid = film_qid
                    WHERE person_qid = ?
                    ORDER BY release_date DESC, title COLLATE uk, {ROLE_ORDER}""",
                (qid,),
            ).fetchall()
        return [(film_from_row(row), Role(row["role"])) for row in rows]

    def collaborators(self, qid: str, limit: int = 8) -> list[tuple[Person, int]]:
        """Повертає персоналій, з якими дана працювала найчастіше.

        Args:
            qid: Ідентифікатор персоналії.
            limit: Найбільша кількість співробітників.

        Returns:
            Співробітник і кількість спільних фільмів, від більшої кількості до меншої.
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                """SELECT people.*, COUNT(DISTINCT other.film_qid) AS films
                   FROM participations own
                   JOIN participations other
                     ON other.film_qid = own.film_qid AND other.person_qid <> own.person_qid
                   JOIN people ON people.qid = other.person_qid
                   WHERE own.person_qid = ?
                   GROUP BY people.qid
                   ORDER BY films DESC, name COLLATE uk
                   LIMIT ?""",
                (qid, limit),
            ).fetchall()
        return [(Person(qid=row["qid"], name=row["name"]), row["films"]) for row in rows]

    def participants(self, film_qid: str) -> dict[Role, list[Person]]:
        """Повертає учасників фільму, згрупованих за ролями.

        Args:
            film_qid: Ідентифікатор фільму.

        Returns:
            Персоналії для кожної ролі; роль без учасників має порожній список.
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                """SELECT people.*, role FROM participations
                   JOIN people ON people.qid = person_qid
                   WHERE film_qid = ?
                   ORDER BY name COLLATE uk""",
                (film_qid,),
            ).fetchall()
        participants: dict[Role, list[Person]] = {role: [] for role in Role}
        for row in rows:
            participants[Role(row["role"])].append(Person(qid=row["qid"], name=row["name"]))
        return participants

    def directors_by_film(self, film_qids: list[str]) -> dict[str, list[Person]]:
        """Повертає режисерів кількох фільмів одним запитом.

        Args:
            film_qids: Ідентифікатори фільмів.

        Returns:
            Режисери за абеткою для кожного фільму; фільм без режисера має порожній список.
        """
        placeholders = ", ".join("?" * len(film_qids))
        with self._database.transaction() as connection:
            rows = connection.execute(
                f"""SELECT film_qid, people.* FROM participations
                    JOIN people ON people.qid = person_qid
                    WHERE role = ? AND film_qid IN ({placeholders})
                    ORDER BY name COLLATE uk""",
                [Role.DIRECTOR.value, *film_qids],
            ).fetchall()
        directors: dict[str, list[Person]] = {qid: [] for qid in film_qids}
        for row in rows:
            directors[row["film_qid"]].append(Person(qid=row["qid"], name=row["name"]))
        return directors

    def directors(self) -> list[Person]:
        """Повертає всіх режисерів за абеткою.

        Returns:
            Режисери для фільтра каталогу.
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                """SELECT * FROM people
                   WHERE qid IN (SELECT person_qid FROM participations WHERE role = ?)
                   ORDER BY name COLLATE uk""",
                (Role.DIRECTOR.value,),
            ).fetchall()
        return [Person(qid=row["qid"], name=row["name"]) for row in rows]

    def replace_all(self, people: list[Person], participations: list[Participation]) -> None:
        """Замінює всіх персоналій і записи про їхню участь у фільмах.

        Args:
            people: Нові персоналії.
            participations: Нові записи участі.
        """
        with self._database.transaction() as connection:
            connection.execute("DELETE FROM people")
            connection.execute("DELETE FROM participations")
            connection.executemany(
                "INSERT OR REPLACE INTO people VALUES (?, ?)",
                [(person.qid, person.name) for person in people],
            )
            connection.executemany(
                "INSERT OR IGNORE INTO participations VALUES (?, ?, ?)",
                [(p.film_qid, p.person_qid, p.role.value) for p in participations],
            )
