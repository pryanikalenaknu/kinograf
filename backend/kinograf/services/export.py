"""Експорт результатів каталогу й SPARQL-запитів у CSV, JSON і Turtle."""

import csv
import io
import json

from kinograf.models import Film
from kinograf.rdf import WD, RdfStore
from kinograf.repositories import FilmFilters, FilmRepository

FORMATS = ("csv", "json", "ttl")

FILM_COLUMNS = (
    "qid",
    "title",
    "year",
    "release_date",
    "duration_min",
    "image_url",
    "wikidata_url",
)


FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: object) -> object:
    """Захищає комірку CSV від виконання як формули в табличному редакторі.

    Назви з Wikidata може редагувати будь-хто; значення, що починається з ``=``, ``+``,
    ``-``, ``@`` або табуляції, Excel сприйняв би як формулу, тому перед ним ставиться ``'``.

    Args:
        value: Значення комірки.

    Returns:
        Безпечне значення.
    """
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def film_record(film: Film) -> dict:
    """Перетворює фільм на запис для експорту.

    Args:
        film: Фільм.

    Returns:
        Значення стовпців ``FILM_COLUMNS``.
    """
    return {
        "qid": film.qid,
        "title": film.title,
        "year": film.year,
        "release_date": film.release_date.isoformat(),
        "duration_min": film.duration_min,
        "image_url": film.image_url,
        "wikidata_url": film.wikidata_url,
    }


class ExportService:
    """Готує файли для завантаження з результатами каталогу й SPARQL-запитів.

    CSV записується в UTF-8 з позначкою порядку байтів, щоб кирилиця правильно
    відкривалася в табличних редакторах, а значення, схожі на формули, екрануються.
    Turtle містить трійки всіх сутностей Wikidata, що є в результаті.

    Args:
        films: Сховище фільмів.
        rdf: Локальний RDF-граф.
    """

    def __init__(self, films: FilmRepository, rdf: RdfStore) -> None:
        self._films = films
        self._rdf = rdf

    def export_films(self, fmt: str, text: str, filters: FilmFilters, sort: str = "year") -> bytes:
        """Експортує всі фільми каталогу, що відповідають пошуку й фільтрам.

        Args:
            fmt: Формат: ``csv``, ``json`` або ``ttl``.
            text: Слова з назви фільму.
            filters: Умови відбору.
            sort: Порядок: ``year`` або ``title``.

        Returns:
            Вміст файлу.

        Raises:
            ValueError: Якщо формат не підтримується.
        """
        self._check(fmt)
        films, _ = self._films.search(text, filters, sort, page_size=None)
        if fmt == "ttl":
            return self._rdf.export_turtle([film.qid for film in films]).encode()
        return self._table(fmt, list(FILM_COLUMNS), [film_record(film) for film in films])

    def export_sparql(self, fmt: str, query: str) -> bytes:
        """Виконує SPARQL-запит і експортує його результат.

        Args:
            fmt: Формат: ``csv``, ``json`` або ``ttl``.
            query: Текст запиту ``SELECT``.

        Returns:
            Вміст файлу.

        Raises:
            ValueError: Якщо формат не підтримується.
            SparqlError: Якщо запит неправильний, заборонений або виконується задовго.
        """
        self._check(fmt)
        result = self._rdf.query(query)
        if fmt == "ttl":
            qids = sorted(
                {
                    value.removeprefix(str(WD))
                    for row in result.rows
                    for value in row.values()
                    if value.startswith(str(WD))
                }
            )
            return self._rdf.export_turtle(qids).encode()
        return self._table(fmt, result.columns, result.rows)

    def _table(self, fmt: str, columns: list[str], records: list[dict]) -> bytes:
        """Записує таблицю у формат CSV або JSON."""
        if fmt == "json":
            return json.dumps(records, ensure_ascii=False, indent=2).encode()
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=columns)
        writer.writeheader()
        writer.writerows(
            {name: safe_cell(value) for name, value in record.items()} for record in records
        )
        return buffer.getvalue().encode("utf-8-sig")

    @staticmethod
    def _check(fmt: str) -> None:
        """Перевіряє, що формат підтримується."""
        if fmt not in FORMATS:
            raise ValueError(f"непідтримуваний формат: {fmt}")
