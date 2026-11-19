"""Налаштування застосунку, що читаються зі змінних середовища."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Параметри роботи застосунку.

    Attributes:
        sparql_endpoint: Адреса SPARQL-точки доступу Wikidata.
        user_agent: Ідентифікатор клієнта, якого вимагають правила Wikidata.
        min_year: Перший рік випуску фільмів, що потрапляють до вибірки.
        retry_delay: Пауза в секундах перед повторним запитом до Wikidata.
        database_path: Шлях до файлу бази даних SQLite.
        graph_path: Шлях до файлу локального RDF-графа у форматі Turtle.
        linked_path: Шлях до файлу опублікованого графа зв'язаних даних.
        report_path: Шлях до звіту останньої перевірки SHACL у форматі Turtle.
        base_url: Базова адреса застосунку, від якої будуються постійні адреси сутностей.
        admin_key: Ключ доступу до адміністративних дій.
    """

    sparql_endpoint: str = "https://query.wikidata.org/sparql"
    user_agent: str = "KinoGraf/0.1 (educational project, KNU)"
    min_year: int = 1991
    retry_delay: float = 60.0
    database_path: str = "data/kinograf.db"
    graph_path: str = "data/graph.ttl"
    linked_path: str = "data/linked.ttl"
    report_path: str = "data/shacl-report.ttl"
    base_url: str = "http://localhost:8080"
    admin_key: str = ""


def load_settings() -> Settings:
    """Створює налаштування зі змінних середовища.

    Змінні, яких немає в середовищі, отримують значення за замовчуванням.

    Returns:
        Заповнений об'єкт налаштувань.
    """
    defaults = Settings()
    return Settings(
        sparql_endpoint=os.getenv("KINOGRAF_SPARQL_ENDPOINT", defaults.sparql_endpoint),
        user_agent=os.getenv("KINOGRAF_USER_AGENT", defaults.user_agent),
        min_year=int(os.getenv("KINOGRAF_MIN_YEAR", defaults.min_year)),
        retry_delay=float(os.getenv("KINOGRAF_RETRY_DELAY", defaults.retry_delay)),
        database_path=os.getenv("KINOGRAF_DATABASE_PATH", defaults.database_path),
        graph_path=os.getenv("KINOGRAF_GRAPH_PATH", defaults.graph_path),
        linked_path=os.getenv("KINOGRAF_LINKED_PATH", defaults.linked_path),
        report_path=os.getenv("KINOGRAF_REPORT_PATH", defaults.report_path),
        base_url=os.getenv("KINOGRAF_BASE_URL", defaults.base_url),
        admin_key=os.getenv("KINOGRAF_ADMIN_KEY", defaults.admin_key),
    )
