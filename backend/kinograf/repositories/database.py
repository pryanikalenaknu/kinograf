"""Підключення до бази даних SQLite і створення її схеми."""

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

BUSY_TIMEOUT = 30.0

UKRAINIAN_ALPHABET = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"

SCHEMA = """
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS films (
    qid TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    release_date TEXT NOT NULL,
    year INTEGER NOT NULL,
    duration_min INTEGER,
    image_url TEXT
);
CREATE TABLE IF NOT EXISTS people (
    qid TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS participations (
    film_qid TEXT,
    person_qid TEXT,
    role TEXT,
    PRIMARY KEY (film_qid, person_qid, role)
);
CREATE TABLE IF NOT EXISTS genres (
    qid TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS film_genres (
    film_qid TEXT,
    genre_qid TEXT,
    PRIMARY KEY (film_qid, genre_qid)
);
CREATE TABLE IF NOT EXISTS awards (
    qid TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS film_awards (
    film_qid TEXT,
    award_qid TEXT,
    PRIMARY KEY (film_qid, award_qid)
);
CREATE TABLE IF NOT EXISTS update_log (
    id INTEGER PRIMARY KEY,
    started_at TEXT,
    finished_at TEXT,
    status TEXT,
    films_added INTEGER,
    films_changed INTEGER,
    message TEXT,
    stage TEXT
);
CREATE INDEX IF NOT EXISTS films_year ON films (year);
CREATE INDEX IF NOT EXISTS participations_person ON participations (person_qid, role);
CREATE INDEX IF NOT EXISTS film_genres_genre ON film_genres (genre_qid);
CREATE VIRTUAL TABLE IF NOT EXISTS films_fts USING fts5 (
    qid UNINDEXED,
    title,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""


def ukrainian_key(text: str) -> tuple:
    """Будує ключ сортування рядка за українською абеткою без урахування регістру.

    Args:
        text: Рядок для сортування.

    Returns:
        Ключ, що впорядковує українські літери за абеткою, а решту символів — за кодом.
    """
    return tuple(
        (0, UKRAINIAN_ALPHABET.index(char)) if char in UKRAINIAN_ALPHABET else (1, ord(char))
        for char in text.casefold()
    )


def compare_ukrainian(left: str, right: str) -> int:
    """Порівнює два рядки за українською абеткою; використовується як правило сортування SQLite.

    Args:
        left: Перший рядок.
        right: Другий рядок.

    Returns:
        Від'ємне число, нуль або додатне число, як вимагає SQLite.
    """
    left_key, right_key = ukrainian_key(left), ukrainian_key(right)
    return (left_key > right_key) - (left_key < right_key)


class Database:
    """База даних SQLite застосунку.

    Кожна транзакція відкриває окреме підключення, тому об'єкт можна використовувати
    з кількох потоків. Вкладені транзакції в одному потоці використовують зовнішню,
    що дає змогу кільком репозиторіям записувати дані атомарно.

    Args:
        path: Шлях до файлу бази даних; батьківська тека створюється за потреби.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._local = threading.local()

    def create_schema(self) -> None:
        """Створює таблиці, індекси й таблицю повнотекстового пошуку, якщо їх ще немає."""
        with self.transaction() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Відкриває транзакцію: фіксує зміни після успішного блоку й скасовує після помилки.

        Yields:
            Підключення з доступом до стовпців за назвою й правилом сортування ``uk``.
        """
        active = getattr(self._local, "connection", None)
        if active is not None:
            yield active
            return
        connection = self._connect()
        self._local.connection = connection
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            self._local.connection = None
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        """Відкриває нове підключення до файлу бази даних."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=BUSY_TIMEOUT)
        connection.row_factory = sqlite3.Row
        connection.create_collation("uk", compare_ukrainian)
        return connection
