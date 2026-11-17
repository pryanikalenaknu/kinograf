"""Статистика каталогу й показники якості даних."""

from kinograf.models import Role
from kinograf.repositories import LogRepository, StatsRepository
from kinograf.services.dto import RankedPerson, Stats

TOP_LIMIT = 10


class StatsService:
    """Збирає показники для сторінок статистики й якості даних.

    Args:
        stats: Сховище статистичних показників.
        logs: Журнал оновлень.
    """

    def __init__(self, stats: StatsRepository, logs: LogRepository) -> None:
        self._stats = stats
        self._logs = logs

    def overview(self) -> Stats:
        """Повертає всі показники разом.

        Returns:
            Статистика, повнота даних і час останнього успішного оновлення.
        """
        last_success = self._logs.last_success()
        return Stats(
            totals=self._stats.totals(),
            films_by_year=self._stats.films_by_year(),
            genres_by_period=self._stats.genres_by_period(),
            top_directors=self._top(Role.DIRECTOR),
            top_actors=self._top(Role.CAST),
            completeness=self._stats.completeness(),
            completeness_by_year=self._stats.completeness_by_year(),
            last_updated=last_success.finished_at if last_success else None,
        )

    def _top(self, role: Role) -> list[RankedPerson]:
        """Повертає рейтинг персоналій у даній ролі."""
        return [
            RankedPerson(person=person, films=films)
            for person, films in self._stats.top_people(role, TOP_LIMIT)
        ]
