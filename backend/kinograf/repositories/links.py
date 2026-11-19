"""Сховище посилань фільмів і персоналій на інші набори даних."""

import sqlite3

from kinograf.models import ExternalLinks
from kinograf.repositories.database import Database


def links_from_row(row: sqlite3.Row) -> ExternalLinks:
    """Створює посилання з рядка таблиці ``external_links``.

    Args:
        row: Рядок зі стовпцями таблиці ``external_links``.

    Returns:
        Посилання сутності.
    """
    return ExternalLinks(
        qid=row["qid"], imdb_id=row["imdb_id"], ukwiki=row["ukwiki"], enwiki=row["enwiki"]
    )


class LinkRepository:
    """Читає й записує посилання на IMDb і Вікіпедію; таблиця спільна для фільмів і персоналій.

    Args:
        database: База даних застосунку.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    def replace_all(self, links: dict[str, ExternalLinks]) -> None:
        """Замінює всі посилання.

        Args:
            links: Посилання за ідентифікаторами сутностей.
        """
        with self._database.transaction() as connection:
            connection.execute("DELETE FROM external_links")
            connection.executemany(
                "INSERT INTO external_links VALUES (?, ?, ?, ?)",
                [(item.qid, item.imdb_id, item.ukwiki, item.enwiki) for item in links.values()],
            )

    def get(self, qid: str) -> ExternalLinks | None:
        """Повертає посилання сутності.

        Args:
            qid: Ідентифікатор фільму або персоналії.

        Returns:
            Посилання або ``None``, якщо їх немає.
        """
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM external_links WHERE qid = ?", (qid,)
            ).fetchone()
        return links_from_row(row) if row else None

    def all(self) -> dict[str, ExternalLinks]:
        """Повертає всі посилання.

        Returns:
            Посилання за ідентифікаторами сутностей.
        """
        with self._database.transaction() as connection:
            rows = connection.execute("SELECT * FROM external_links").fetchall()
        return {row["qid"]: links_from_row(row) for row in rows}
