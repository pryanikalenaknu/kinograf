"""Оновлення даних з Wikidata: завантаження, запис у SQLite й RDF-граф, журнал."""

import fcntl
import threading
from pathlib import Path
from typing import TextIO

from kinograf.models import UpdateLog
from kinograf.opendata import WikidataLoader
from kinograf.rdf import RdfStore
from kinograf.repositories import Database, FilmRepository, LogRepository, PersonRepository

STAGES = ("films", "participations", "genres", "awards", "storage")


class UpdateInProgressError(Exception):
    """Нове оновлення неможливо почати, доки виконується попереднє."""


class UpdateService:
    """Виконує оновлення даних і веде його журнал.

    Одночасно може виконуватися лише одне оновлення. Метод :meth:`start` створює
    запис журналу, а :meth:`run` виконує оновлення, тож їх можна викликати
    в різних потоках. Якщо задано ``lock_path``, файлове блокування не дає почати
    оновлення й в іншому процесі, наприклад командою ``python -m kinograf.update``
    під час оновлення з панелі адміністрування.

    Args:
        loader: Завантажувач даних з Wikidata.
        database: База даних, у транзакції якої замінюються дані.
        films: Сховище фільмів.
        people: Сховище персоналій.
        logs: Журнал оновлень.
        rdf: Локальний RDF-граф.
        lock_path: Файл блокування оновлень між процесами.
    """

    def __init__(
        self,
        loader: WikidataLoader,
        database: Database,
        films: FilmRepository,
        people: PersonRepository,
        logs: LogRepository,
        rdf: RdfStore,
        lock_path: Path | None = None,
    ) -> None:
        self._loader = loader
        self._database = database
        self._films = films
        self._people = people
        self._logs = logs
        self._rdf = rdf
        self._lock = threading.Lock()
        self._lock_path = lock_path
        self._lock_file: TextIO | None = None

    @property
    def running(self) -> bool:
        """Чи виконується зараз оновлення."""
        return self._lock.locked()

    def history(self, limit: int = 20) -> list[UpdateLog]:
        """Повертає останні записи журналу оновлень.

        Args:
            limit: Найбільша кількість записів.

        Returns:
            Записи від новіших до старіших.
        """
        return self._logs.recent(limit)

    def log(self, log_id: int) -> UpdateLog | None:
        """Повертає запис журналу з поточним етапом оновлення.

        Args:
            log_id: Ідентифікатор запису.

        Returns:
            Запис або ``None``, якщо його немає.
        """
        return self._logs.get(log_id)

    def start(self) -> UpdateLog:
        """Резервує право на оновлення й створює запис журналу зі статусом ``running``.

        Returns:
            Запис журналу, який треба передати в :meth:`run`.

        Raises:
            UpdateInProgressError: Якщо попереднє оновлення ще не завершилося.
        """
        if not self._acquire():
            raise UpdateInProgressError("оновлення вже виконується")
        try:
            return self._logs.start()
        except Exception:
            self._release()
            raise

    def recover_interrupted(self) -> int:
        """Закриває записи журналу зі статусом ``running``, що лишилися після аварійної зупинки.

        Нічого не робить, якщо оновлення саме виконується в цьому або іншому процесі.

        Returns:
            Кількість закритих записів.
        """
        if not self._acquire():
            return 0
        try:
            return self._logs.fail_running("оновлення перервано: процес зупинився до завершення")
        finally:
            self._release()

    def run(self, log: UpdateLog) -> UpdateLog:
        """Виконує оновлення за етапами ``STAGES`` і записує підсумок у журнал.

        Дані в SQLite замінюються в одній транзакції разом із перебудовою RDF-графа;
        після помилки на будь-якому етапі попередні дані залишаються без змін.

        Args:
            log: Запис журналу, отриманий від :meth:`start`.

        Returns:
            Запис журналу зі статусом ``success`` або ``error``.
        """
        try:
            self._logs.set_stage(log, "films")
            films = self._loader.fetch_films()
            self._logs.set_stage(log, "participations")
            loaded = self._loader.fetch_participations()
            self._logs.set_stage(log, "genres")
            genres = self._loader.fetch_genres()
            self._logs.set_stage(log, "awards")
            awards = self._loader.fetch_awards()
            self._logs.set_stage(log, "storage")
            people = list(loaded.people.values())
            with self._database.transaction():
                log.films_added, log.films_changed = self._films.replace_all(films, genres, awards)
                self._people.replace_all(people, loaded.participations)
                self._rdf.rebuild(films, people, loaded.participations, genres, awards)
            log.status = "success"
        except Exception as error:
            log.status = "error"
            log.message = str(error)
        finally:
            try:
                self._logs.finish(log)
            finally:
                self._release()
        return log

    def _acquire(self) -> bool:
        """Займає блокування оновлення в процесі й, якщо задано файл, між процесами."""
        if not self._lock.acquire(blocking=False):
            return False
        if self._lock_path is None:
            return True
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._lock_path.open("w")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            self._lock.release()
            return False
        self._lock_file = handle
        return True

    def _release(self) -> None:
        """Звільняє блокування оновлення."""
        if self._lock_file is not None:
            fcntl.flock(self._lock_file, fcntl.LOCK_UN)
            self._lock_file.close()
            self._lock_file = None
        self._lock.release()
