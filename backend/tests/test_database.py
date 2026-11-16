"""Тести схеми бази даних і транзакцій."""

import pytest

from kinograf.repositories import Database
from kinograf.repositories.database import ukrainian_key

TABLES = {
    "films",
    "people",
    "participations",
    "genres",
    "film_genres",
    "awards",
    "film_awards",
    "update_log",
    "films_fts",
}


def table_names(database):
    with database.transaction() as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        return {row["name"] for row in rows}


def test_create_schema_creates_all_tables(tmp_path):
    database = Database(tmp_path / "nested" / "kinograf.db")
    database.create_schema()
    assert database.path.exists()
    assert TABLES <= table_names(database)


def test_create_schema_is_repeatable(tmp_path):
    database = Database(tmp_path / "kinograf.db")
    database.create_schema()
    database.create_schema()
    assert TABLES <= table_names(database)


def test_films_fts_finds_cyrillic_words_case_insensitive(tmp_path):
    database = Database(tmp_path / "kinograf.db")
    database.create_schema()
    with database.transaction() as connection:
        connection.execute("INSERT INTO films_fts (qid, title) VALUES ('Q1', 'Плем''я')")
        found = connection.execute(
            "SELECT qid FROM films_fts WHERE films_fts MATCH ?", ('"ПЛЕМ"*',)
        ).fetchall()
    assert [row["qid"] for row in found] == ["Q1"]


def test_transaction_rolls_back_on_error(tmp_path):
    database = Database(tmp_path / "kinograf.db")
    database.create_schema()
    with pytest.raises(RuntimeError), database.transaction() as connection:
        connection.execute("INSERT INTO people VALUES ('Q1', 'Ірина Цілик')")
        raise RuntimeError
    with database.transaction() as connection:
        assert connection.execute("SELECT COUNT(*) FROM people").fetchone()[0] == 0


def test_nested_transaction_shares_connection(tmp_path):
    database = Database(tmp_path / "kinograf.db")
    database.create_schema()
    with database.transaction() as outer, database.transaction() as inner:
        assert inner is outer


def test_ukrainian_collation_orders_by_alphabet(tmp_path):
    database = Database(tmp_path / "kinograf.db")
    database.create_schema()
    with database.transaction() as connection:
        connection.executemany(
            "INSERT INTO people VALUES (?, ?)",
            [("Q1", "Їжак"), ("Q2", "Ґанок"), ("Q3", "Іра"), ("Q4", "Атлантида"), ("Q5", "Єва")],
        )
        rows = connection.execute("SELECT name FROM people ORDER BY name COLLATE uk").fetchall()
    assert [row["name"] for row in rows] == ["Атлантида", "Ґанок", "Єва", "Іра", "Їжак"]


def test_ukrainian_key_ignores_case():
    assert ukrainian_key("Мамай") == ukrainian_key("мамай")
