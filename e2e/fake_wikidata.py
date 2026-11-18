"""Підставна SPARQL-точка доступу Wikidata з незмінним набором фільмів для приймальних тестів.

Відповідає на чотири запити завантажувача (фільми, учасники, жанри, нагороди) у форматі
SPARQL JSON, тож оновлення даних проходить увесь шлях без звернення до справжньої Wikidata.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ENTITY = "http://www.wikidata.org/entity/"

FILMS = [
    ("Q1001", "Плем'я", "2014-05-21", 132),
    ("Q1002", "Земля блакитна, ніби апельсин", "2020-01-25", 74),
    ("Q1003", "Мамай", "2003-01-01", 80),
    ("Q1004", "Поводир", "2014-11-13", 122),
    ("Q1005", "Атлантида", "2019-09-04", 108),
    ("Q1006", "Відблиск", "2021-09-01", 127),
    ("Q1007", "Їжак", "1995-03-01", None),
    ("Q1008", "Кіборги", "2017-12-07", 113),
    ("Q1009", "Додому", "2019-05-20", 97),
    ("Q1010", "Мої думки тихі", "2019-11-01", 104),
    ("Q1011", "Памфір", "2022-05-20", 102),
    ("Q1012", "Клондайк", "2022-01-20", 100),
    ("Q1013", "Носоріг", "2021-09-05", 101),
    ("Q1014", "Толока", "2020-07-15", 98),
]

PEOPLE = {
    "Q2001": "Мирослав Слабошпицький",
    "Q2002": "Олесь Санін",
    "Q2003": "Валентин Васянович",
    "Q2004": "Андрій Римарук",
    "Q2005": "Алла Загайкевич",
    "Q2006": "Ірина Цілик",
    "Q2007": "Ахтем Сеітаблаєв",
    "Q2008": "Нариман Алієв",
    "Q2009": "Антоніо Лукіч",
    "Q2010": "Дмитро Сухолиткий-Собчук",
    "Q2011": "Марина Ер Горбач",
    "Q2012": "Олег Сенцов",
    "Q2013": "Михайло Іллєнко",
    "Q2014": "Яна Новікова",
}

PARTICIPATIONS = [
    ("Q1001", "Q2001", "director"),
    ("Q1001", "Q2001", "screenwriter"),
    ("Q1001", "Q2014", "cast"),
    ("Q1002", "Q2006", "director"),
    ("Q1003", "Q2002", "director"),
    ("Q1003", "Q2002", "screenwriter"),
    ("Q1003", "Q2005", "composer"),
    ("Q1004", "Q2002", "director"),
    ("Q1004", "Q2002", "screenwriter"),
    ("Q1004", "Q2005", "composer"),
    ("Q1005", "Q2003", "director"),
    ("Q1005", "Q2003", "screenwriter"),
    ("Q1005", "Q2004", "cast"),
    ("Q1006", "Q2003", "director"),
    ("Q1006", "Q2004", "cast"),
    ("Q1008", "Q2007", "director"),
    ("Q1009", "Q2008", "director"),
    ("Q1009", "Q2007", "cast"),
    ("Q1010", "Q2009", "director"),
    ("Q1011", "Q2010", "director"),
    ("Q1012", "Q2011", "director"),
    ("Q1013", "Q2012", "director"),
    ("Q1014", "Q2013", "director"),
]

GENRES = {
    "Q130232": ("драма", ["Q1001", "Q1003", "Q1004", "Q1005", "Q1006", "Q1008", "Q1009",
                          "Q1011", "Q1012", "Q1013", "Q1014"]),
    "Q93204": ("документальний фільм", ["Q1002"]),
    "Q17013749": ("історичний фільм", ["Q1003", "Q1004"]),
    "Q157443": ("комедія", ["Q1010"]),
    "Q369747": ("воєнний фільм", ["Q1008", "Q1012"]),
}  # fmt: skip

AWARDS = {
    "Q100": ("Премія «Сандерс»", ["Q1002"]),
    "Q101": ("Венеційський кінофестиваль — найкращий фільм програми «Горизонти»", ["Q1005"]),
    "Q102": ("Кінопремія «Золота дзиґа»", ["Q1004"]),
}


def uri(qid: str) -> dict:
    """Повертає значення-URI сутності у форматі SPARQL JSON."""
    return {"type": "uri", "value": ENTITY + qid}


def literal(value: str) -> dict:
    """Повертає літерал у форматі SPARQL JSON."""
    return {"type": "literal", "value": value}


def film_rows() -> list[dict]:
    """Рядки відповіді на запит основних даних фільмів."""
    rows = []
    for qid, title, released, duration in FILMS:
        row = {"film": uri(qid), "filmLabel": literal(title), "released": literal(released)}
        if duration:
            row["duration"] = literal(str(duration))
        rows.append(row)
    return rows


def participation_rows() -> list[dict]:
    """Рядки відповіді на запит учасників."""
    return [
        {
            "film": uri(film),
            "person": uri(person),
            "personLabel": literal(PEOPLE[person]),
            "role": literal(role),
        }
        for film, person, role in PARTICIPATIONS
    ]


def linked_rows(items: dict, name: str) -> list[dict]:
    """Рядки відповіді на запит жанрів або нагород."""
    return [
        {"film": uri(film), name: uri(qid), f"{name}Label": literal(label)}
        for qid, (label, films) in items.items()
        for film in films
    ]


def answer(query: str) -> list[dict]:
    """Обирає відповідь за характерним фрагментом запиту завантажувача."""
    if "(MIN(?date) AS ?released)" in query:
        return film_rows()
    if "?personLabel" in query:
        return participation_rows()
    if "?genreLabel" in query:
        return linked_rows(GENRES, "genre")
    if "?awardLabel" in query:
        return linked_rows(AWARDS, "award")
    return []


class Handler(BaseHTTPRequestHandler):
    """Обробляє SPARQL-запити методами GET і POST."""

    def do_GET(self) -> None:  # noqa: N802
        """Відповідає на запит, переданий у рядку адреси."""
        self._respond(parse_qs(urlparse(self.path).query).get("query", [""])[0])

    def do_POST(self) -> None:  # noqa: N802
        """Відповідає на запит, переданий у тілі."""
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        self._respond(parse_qs(body).get("query", [""])[0])

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        """Не друкує журнал запитів."""

    def _respond(self, query: str) -> None:
        """Надсилає результат запиту у форматі SPARQL JSON."""
        payload = json.dumps({"head": {"vars": []}, "results": {"bindings": answer(query)}})
        self.send_response(200)
        self.send_header("Content-Type", "application/sparql-results+json; charset=utf-8")
        self.end_headers()
        self.wfile.write(payload.encode())


def start(port: int) -> ThreadingHTTPServer:
    """Запускає підставну точку доступу у фоновому потоці.

    Args:
        port: Порт на 127.0.0.1.

    Returns:
        Запущений сервер.
    """
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
