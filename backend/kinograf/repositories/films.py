"""Сховище фільмів: каталог, пошук, пов'язані фільми й заміна даних після оновлення."""

import re
import sqlite3
from dataclasses import dataclass
from datetime import date

from kinograf.models import Award, Film, Genre, Role
from kinograf.repositories.database import Database

PERIODS = {"1991-2013": (1991, 2013), "2014-now": (2014, None)}

SORT_ORDERS = {
    "year": "year DESC, release_date DESC, title COLLATE uk",
    "title": "title COLLATE uk, year DESC",
}


@dataclass(frozen=True)
class FilmFilters:
    """Умови відбору фільмів у каталозі; незадані умови не обмежують вибірку.

    Attributes:
        year_from: Найменший рік виходу.
        year_to: Найбільший рік виходу.
        period: Період з ``PERIODS``: ``1991-2013`` або ``2014-now``.
        genre: Ідентифікатор жанру.
        director: Ідентифікатор режисера.
        has_cast: Лише фільми, для яких вказано акторів.
    """

    year_from: int | None = None
    year_to: int | None = None
    period: str | None = None
    genre: str | None = None
    director: str | None = None
    has_cast: bool = False


def film_from_row(row: sqlite3.Row) -> Film:
    """Створює фільм з рядка таблиці ``films``.

    Args:
        row: Рядок зі стовпцями таблиці ``films``.

    Returns:
        Фільм.
    """
    return Film(
        qid=row["qid"],
        title=row["title"],
        release_date=date.fromisoformat(row["release_date"]),
        duration_min=row["duration_min"],
        image_url=row["image_url"],
    )


def fts_query(text: str) -> str:
    """Перетворює текст пошуку на запит FTS5: кожне слово шукається як початок слова назви.

    Args:
        text: Текст, введений користувачем.

    Returns:
        Вираз для ``MATCH`` або порожній рядок, якщо в тексті немає слів.
    """
    return " ".join(f'"{word}"*' for word in re.findall(r"\w+", text.casefold()))


class FilmRepository:
    """Читає й записує фільми, їхні жанри й нагороди.

    Args:
        database: База даних застосунку.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self, qid: str) -> Film | None:
        """Повертає фільм за ідентифікатором.

        Args:
            qid: Ідентифікатор фільму.

        Returns:
            Фільм або ``None``, якщо його немає в базі.
        """
        with self._database.transaction() as connection:
            row = connection.execute("SELECT * FROM films WHERE qid = ?", (qid,)).fetchone()
        return film_from_row(row) if row else None

    def search(
        self,
        text: str,
        filters: FilmFilters,
        sort: str = "year",
        page: int = 1,
        page_size: int | None = 12,
    ) -> tuple[list[Film], int]:
        """Шукає фільми за назвою й фільтрами та повертає одну сторінку результатів.

        Args:
            text: Слова з назви фільму; порожній рядок не обмежує пошук.
            filters: Умови відбору.
            sort: Порядок: ``year`` — від новіших, ``title`` — за абеткою.
            page: Номер сторінки, починаючи з 1.
            page_size: Кількість фільмів на сторінці; ``None`` — усі фільми однією сторінкою.

        Returns:
            Фільми сторінки й загальна кількість знайдених фільмів.
        """
        conditions, params = self._conditions(text, filters)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit, page_params = "", []
        if page_size is not None:
            limit, page_params = "LIMIT ? OFFSET ?", [page_size, (page - 1) * page_size]
        with self._database.transaction() as connection:
            if not connection.in_transaction:
                connection.execute("BEGIN")
            total = connection.execute(f"SELECT COUNT(*) FROM films {where}", params).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM films {where} ORDER BY {SORT_ORDERS[sort]} {limit}",
                [*params, *page_params],
            ).fetchall()
        return [film_from_row(row) for row in rows], total

    def related(self, qid: str, limit: int = 8) -> list[tuple[Film, int, int]]:
        """Повертає фільми, пов'язані з даним спільними учасниками або жанрами.

        Спершу йдуть фільми з більшою кількістю спільних учасників, далі — з більшою
        кількістю спільних жанрів, далі — новіші.

        Args:
            qid: Ідентифікатор фільму.
            limit: Найбільша кількість фільмів.

        Returns:
            Фільм, кількість спільних учасників і кількість спільних жанрів.
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                """
                WITH shared_people AS (
                    SELECT other.film_qid AS qid, COUNT(DISTINCT other.person_qid) AS n
                    FROM participations own
                    JOIN participations other
                      ON other.person_qid = own.person_qid AND other.film_qid <> own.film_qid
                    WHERE own.film_qid = :qid
                    GROUP BY other.film_qid
                ), shared_genres AS (
                    SELECT other.film_qid AS qid, COUNT(DISTINCT other.genre_qid) AS n
                    FROM film_genres own
                    JOIN film_genres other
                      ON other.genre_qid = own.genre_qid AND other.film_qid <> own.film_qid
                    WHERE own.film_qid = :qid
                    GROUP BY other.film_qid
                )
                SELECT films.*,
                       COALESCE(shared_people.n, 0) AS people,
                       COALESCE(shared_genres.n, 0) AS genres
                FROM films
                LEFT JOIN shared_people ON shared_people.qid = films.qid
                LEFT JOIN shared_genres ON shared_genres.qid = films.qid
                WHERE shared_people.n IS NOT NULL OR shared_genres.n IS NOT NULL
                ORDER BY people DESC, genres DESC, release_date DESC, title COLLATE uk
                LIMIT :limit
                """,
                {"qid": qid, "limit": limit},
            ).fetchall()
        return [(film_from_row(row), row["people"], row["genres"]) for row in rows]

    def genres_of(self, qid: str) -> list[Genre]:
        """Повертає жанри фільму за абеткою.

        Args:
            qid: Ідентифікатор фільму.

        Returns:
            Жанри фільму.
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                """SELECT genres.* FROM genres JOIN film_genres ON genre_qid = qid
                   WHERE film_qid = ? ORDER BY name COLLATE uk""",
                (qid,),
            ).fetchall()
        return [Genre(qid=row["qid"], name=row["name"]) for row in rows]

    def awards_of(self, qid: str) -> list[Award]:
        """Повертає нагороди фільму за абеткою.

        Args:
            qid: Ідентифікатор фільму.

        Returns:
            Нагороди фільму.
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                """SELECT awards.* FROM awards JOIN film_awards ON award_qid = qid
                   WHERE film_qid = ? ORDER BY name COLLATE uk""",
                (qid,),
            ).fetchall()
        return [Award(qid=row["qid"], name=row["name"]) for row in rows]

    def genres_by_film(self, qids: list[str]) -> dict[str, list[Genre]]:
        """Повертає жанри кількох фільмів одним запитом.

        Args:
            qids: Ідентифікатори фільмів.

        Returns:
            Жанри за абеткою для кожного фільму; фільм без жанрів має порожній список.
        """
        placeholders = ", ".join("?" * len(qids))
        with self._database.transaction() as connection:
            rows = connection.execute(
                f"""SELECT film_qid, genres.* FROM genres JOIN film_genres ON genre_qid = qid
                    WHERE film_qid IN ({placeholders}) ORDER BY name COLLATE uk""",
                qids,
            ).fetchall()
        genres: dict[str, list[Genre]] = {qid: [] for qid in qids}
        for row in rows:
            genres[row["film_qid"]].append(Genre(qid=row["qid"], name=row["name"]))
        return genres

    def all_genres(self) -> list[Genre]:
        """Повертає всі жанри, що мають хоча б один фільм, за абеткою.

        Returns:
            Жанри для фільтра каталогу.
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                """SELECT * FROM genres
                   WHERE qid IN (SELECT genre_qid FROM film_genres)
                   ORDER BY name COLLATE uk"""
            ).fetchall()
        return [Genre(qid=row["qid"], name=row["name"]) for row in rows]

    def replace_all(
        self,
        films: list[Film],
        genres: dict[str, list[Genre]],
        awards: dict[str, list[Award]],
    ) -> tuple[int, int]:
        """Замінює всі фільми, жанри й нагороди та перебудовує індекс пошуку.

        Фільм вважається зміненим, якщо змінилися його основні дані, жанри або нагороди.

        Args:
            films: Нові фільми.
            genres: Жанри за ідентифікаторами фільмів.
            awards: Нагороди за ідентифікаторами фільмів.

        Returns:
            Кількість доданих і кількість змінених фільмів.
        """
        with self._database.transaction() as connection:
            previous = self._state(connection)
            for table in ("films", "genres", "film_genres", "awards", "film_awards", "films_fts"):
                connection.execute(f"DELETE FROM {table}")
            connection.executemany(
                "INSERT INTO films VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        f.qid,
                        f.title,
                        f.release_date.isoformat(),
                        f.year,
                        f.duration_min,
                        f.image_url,
                    )
                    for f in films
                ],
            )
            connection.executemany(
                "INSERT INTO films_fts (qid, title) VALUES (?, ?)",
                [(film.qid, film.title) for film in films],
            )
            self._insert_links(connection, "genres", "film_genres", genres)
            self._insert_links(connection, "awards", "film_awards", awards)
            current = self._state(connection)
        added = sum(1 for qid in current if qid not in previous)
        changed = sum(
            1 for qid, state in current.items() if qid in previous and previous[qid] != state
        )
        return added, changed

    @staticmethod
    def _insert_links(
        connection: sqlite3.Connection,
        table: str,
        link_table: str,
        items: dict[str, list[Genre]] | dict[str, list[Award]],
    ) -> None:
        """Записує довідник жанрів або нагород і його зв'язки з фільмами."""
        connection.executemany(
            f"INSERT OR REPLACE INTO {table} VALUES (?, ?)",
            [(item.qid, item.name) for film_items in items.values() for item in film_items],
        )
        connection.executemany(
            f"INSERT OR IGNORE INTO {link_table} VALUES (?, ?)",
            [(film_qid, item.qid) for film_qid, film_items in items.items() for item in film_items],
        )

    @staticmethod
    def _state(connection: sqlite3.Connection) -> dict[str, tuple]:
        """Повертає знімок фільмів для порівняння до й після оновлення."""
        rows = connection.execute(
            """
            SELECT films.*,
                   (SELECT group_concat(genre_qid) FROM
                      (SELECT genre_qid FROM film_genres
                       WHERE film_qid = films.qid ORDER BY genre_qid)) AS genre_qids,
                   (SELECT group_concat(award_qid) FROM
                      (SELECT award_qid FROM film_awards
                       WHERE film_qid = films.qid ORDER BY award_qid)) AS award_qids
            FROM films
            """
        ).fetchall()
        return {row["qid"]: tuple(row) for row in rows}

    @staticmethod
    def _conditions(text: str, filters: FilmFilters) -> tuple[list[str], list]:
        """Будує умови SQL і їхні параметри для пошуку й фільтрів каталогу."""
        conditions: list[str] = []
        params: list = []
        match = fts_query(text)
        if match:
            conditions.append("qid IN (SELECT qid FROM films_fts WHERE films_fts MATCH ?)")
            params.append(match)
        year_from, year_to = PERIODS.get(filters.period, (None, None))
        for bound, condition in (
            (year_from, "year >= ?"),
            (year_to, "year <= ?"),
            (filters.year_from, "year >= ?"),
            (filters.year_to, "year <= ?"),
        ):
            if bound is not None:
                conditions.append(condition)
                params.append(bound)
        if filters.genre:
            conditions.append("qid IN (SELECT film_qid FROM film_genres WHERE genre_qid = ?)")
            params.append(filters.genre)
        if filters.director:
            conditions.append(
                "qid IN (SELECT film_qid FROM participations WHERE person_qid = ? AND role = ?)"
            )
            params.extend([filters.director, Role.DIRECTOR.value])
        if filters.has_cast:
            conditions.append("qid IN (SELECT film_qid FROM participations WHERE role = ?)")
            params.append(Role.CAST.value)
        return conditions, params
