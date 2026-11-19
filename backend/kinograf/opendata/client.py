"""Клієнт SPARQL-точки доступу Wikidata з повторними спробами."""

import time
import urllib.error
from collections.abc import Callable

from SPARQLWrapper import JSON, POST, URLENCODED, SPARQLWrapper


class WikidataError(Exception):
    """Запит до Wikidata не вдалося виконати за дозволену кількість спроб."""


def retry_after(error: Exception) -> float:
    """Повертає паузу із заголовка ``Retry-After`` відповіді з помилкою.

    Wikidata надсилає цей заголовок разом із кодом 429, коли обмежує частоту запитів.

    Args:
        error: Помилка, з якою завершилася спроба.

    Returns:
        Пауза в секундах або 0, якщо заголовка немає чи він не є числом секунд.
    """
    if not isinstance(error, urllib.error.HTTPError) or error.headers is None:
        return 0.0
    try:
        return max(0.0, float(error.headers.get("Retry-After", "")))
    except ValueError:
        return 0.0


class WikidataClient:
    """Виконує SPARQL-запити до Wikidata й повертає результати як список словників.

    Args:
        endpoint: Адреса SPARQL-точки доступу.
        user_agent: Ідентифікатор клієнта для заголовка ``User-Agent``.
        max_attempts: Найбільша кількість спроб виконання одного запиту.
        retry_delay: Пауза в секундах перед другою спробою; далі вона подвоюється.
            Типові 60 с відповідають обмеженню Wikidata в один запит на хвилину;
            якщо сервер вимагає довшої паузи в ``Retry-After``, береться вона.
        sleep: Функція очікування; підміняється в тестах.
    """

    def __init__(
        self,
        endpoint: str,
        user_agent: str,
        max_attempts: int = 3,
        retry_delay: float = 60.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.endpoint = endpoint
        self.user_agent = user_agent
        self.max_attempts = max_attempts
        self.retry_delay = retry_delay
        self._sleep = sleep

    def run(self, query: str) -> list[dict[str, str]]:
        """Виконує запит і повертає рядки результату.

        Кожен рядок — словник «змінна запиту → значення». Змінні без значення
        в рядку відсутні.

        Args:
            query: Текст SPARQL-запиту.

        Returns:
            Рядки результату запиту.

        Raises:
            WikidataError: Якщо всі спроби завершилися помилкою.
        """
        delay = self.retry_delay
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self._execute(query)
                return [
                    {name: cell["value"] for name, cell in binding.items()}
                    for binding in response["results"]["bindings"]
                ]
            except Exception as error:
                last_error = error
                if attempt < self.max_attempts:
                    self._sleep(max(delay, retry_after(error)))
                    delay *= 2
        raise WikidataError(
            f"запит не виконано за {self.max_attempts} спроби: {last_error}"
        ) from last_error

    def _execute(self, query: str) -> dict:
        """Надсилає запит до точки доступу й повертає розібраний JSON-результат."""
        return self.prepare(query).queryAndConvert()

    def prepare(self, query: str) -> SPARQLWrapper:
        """Готує запит у формі, яку приймає Wikidata навіть під час обмежень.

        Запит надсилається методом ``POST`` як форма ``query=…``, а формат результату
        задається лише заголовком ``Accept``. Запити ``GET`` з додатковими параметрами
        ``format``, ``output`` і ``results``, які SPARQLWrapper додає типово, Wikidata
        під час збою 2026 року відхиляла з кодом 429 і паузою 1 000 с.

        Args:
            query: Текст SPARQL-запиту.

        Returns:
            Налаштований запит SPARQLWrapper.
        """
        sparql = SPARQLWrapper(self.endpoint, agent=self.user_agent)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        sparql.setMethod(POST)
        sparql.setRequestMethod(URLENCODED)
        sparql.setOnlyConneg(True)
        sparql.setTimeout(60)
        return sparql
