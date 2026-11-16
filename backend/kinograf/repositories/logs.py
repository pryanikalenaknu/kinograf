"""Сховище журналу оновлень даних."""

import sqlite3
from datetime import UTC, datetime

from kinograf.models import UpdateLog
from kinograf.repositories.database import Database


def log_from_row(row: sqlite3.Row) -> UpdateLog:
    """Створює запис журналу з рядка таблиці ``update_log``.

    Args:
        row: Рядок зі стовпцями таблиці ``update_log``.

    Returns:
        Запис журналу.
    """
    finished_at = row["finished_at"]
    return UpdateLog(
        id=row["id"],
        started_at=datetime.fromisoformat(row["started_at"]),
        finished_at=datetime.fromisoformat(finished_at) if finished_at else None,
        status=row["status"],
        films_added=row["films_added"],
        films_changed=row["films_changed"],
        message=row["message"],
        stage=row["stage"],
    )


class LogRepository:
    """Веде журнал оновлень даних.

    Args:
        database: База даних застосунку.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    def start(self) -> UpdateLog:
        """Створює запис про початок оновлення зі статусом ``running``.

        Returns:
            Збережений запис з ідентифікатором.
        """
        log = UpdateLog(started_at=datetime.now(UTC))
        with self._database.transaction() as connection:
            cursor = connection.execute(
                """INSERT INTO update_log
                   (started_at, status, films_added, films_changed, message, stage)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    log.started_at.isoformat(),
                    log.status,
                    log.films_added,
                    log.films_changed,
                    log.message,
                    log.stage,
                ),
            )
        log.id = cursor.lastrowid
        return log

    def set_stage(self, log: UpdateLog, stage: str) -> None:
        """Запам'ятовує поточний етап оновлення.

        Args:
            log: Запис журналу.
            stage: Назва етапу.
        """
        log.stage = stage
        with self._database.transaction() as connection:
            connection.execute("UPDATE update_log SET stage = ? WHERE id = ?", (stage, log.id))

    def finish(self, log: UpdateLog) -> None:
        """Зберігає підсумок оновлення й час завершення.

        Args:
            log: Запис журналу з остаточним статусом, лічильниками й повідомленням.
        """
        log.finished_at = datetime.now(UTC)
        with self._database.transaction() as connection:
            connection.execute(
                """UPDATE update_log
                   SET finished_at = ?, status = ?, films_added = ?, films_changed = ?,
                       message = ?, stage = ?
                   WHERE id = ?""",
                (
                    log.finished_at.isoformat(),
                    log.status,
                    log.films_added,
                    log.films_changed,
                    log.message,
                    log.stage,
                    log.id,
                ),
            )

    def fail_running(self, message: str) -> int:
        """Позначає всі незавершені записи як помилкові.

        Args:
            message: Пояснення для журналу.

        Returns:
            Кількість змінених записів.
        """
        with self._database.transaction() as connection:
            cursor = connection.execute(
                """UPDATE update_log SET status = 'error', message = ?, finished_at = ?
                   WHERE status = 'running'""",
                (message, datetime.now(UTC).isoformat()),
            )
        return cursor.rowcount

    def get(self, log_id: int) -> UpdateLog | None:
        """Повертає запис журналу за ідентифікатором.

        Args:
            log_id: Ідентифікатор запису.

        Returns:
            Запис або ``None``, якщо його немає.
        """
        with self._database.transaction() as connection:
            row = connection.execute("SELECT * FROM update_log WHERE id = ?", (log_id,)).fetchone()
        return log_from_row(row) if row else None

    def recent(self, limit: int = 20) -> list[UpdateLog]:
        """Повертає останні записи журналу, від новіших до старіших.

        Args:
            limit: Найбільша кількість записів.

        Returns:
            Записи журналу.
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM update_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [log_from_row(row) for row in rows]

    def last_success(self) -> UpdateLog | None:
        """Повертає останнє успішне оновлення.

        Returns:
            Запис журналу або ``None``, якщо успішних оновлень ще не було.
        """
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM update_log WHERE status = 'success' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return log_from_row(row) if row else None
