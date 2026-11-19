"""Перевірка якості записів за правилами SHACL: зведення, зауваження й файли правил і звіту."""

from kinograf.models import Severity
from kinograf.rdf import ShaclValidator
from kinograf.repositories import LogRepository, QualityRepository, StatsRepository
from kinograf.services.dto import FilmIssues, QualityPage, QualityReport, RuleSummary

ISSUES_PAGE_SIZE = 12


class QualityService:
    """Віддає результати останньої перевірки за правилами SHACL.

    Перевірка триває кілька секунд, тому виконується під час оновлення даних, а сервіс
    лише читає збережені зауваження.

    Args:
        validator: Перевірка SHACL з правилами й шляхом до звіту.
        quality: Сховище зауважень.
        stats: Сховище показників, з якого береться кількість фільмів.
        logs: Журнал оновлень.
    """

    def __init__(
        self,
        validator: ShaclValidator,
        quality: QualityRepository,
        stats: StatsRepository,
        logs: LogRepository,
    ) -> None:
        self._validator = validator
        self._quality = quality
        self._stats = stats
        self._logs = logs

    def report(self) -> QualityReport:
        """Збирає зведення за правилами.

        Returns:
            Час перевірки, кількість перевірених фільмів і фільмів із зауваженнями,
            розподіл за рівнями й правила з кількістю фільмів.
        """
        by_rule = self._quality.films_by_rule()
        by_severity = self._quality.films_by_severity()
        last = self._logs.last_success()
        checked = self._validator.report_path.exists() and last is not None
        return QualityReport(
            checked_at=last.finished_at if checked else None,
            films_checked=self._stats.totals()["films"],
            films_with_issues=sum(by_severity.values()),
            by_severity=by_severity,
            rules=[
                RuleSummary(rule=rule, films=by_rule.get(rule.rule, 0))
                for rule in self._validator.rules()
            ],
        )

    def issues(
        self, rule: str | None = None, severity: Severity | None = None, page: int = 1
    ) -> QualityPage:
        """Повертає сторінку фільмів із зауваженнями, по 12 на сторінці.

        Args:
            rule: Ідентифікатор правила або ``None`` — усі правила.
            severity: Рівень або ``None`` — усі рівні.
            page: Номер сторінки, починаючи з 1.

        Returns:
            Фільми з усіма їхніми зауваженнями в порядку рівня й правил.
        """
        order = {item.rule: item.order for item in self._validator.rules()}
        films, total = self._quality.issues(rule, severity, page, ISSUES_PAGE_SIZE)
        return QualityPage(
            items=[
                FilmIssues(
                    film=film,
                    issues=sorted(
                        issues,
                        key=lambda item: (item.severity.rank, order.get(item.rule, len(order))),
                    ),
                )
                for film, issues in films
            ],
            total=total,
            page=page,
        )

    def rule_ids(self) -> list[str]:
        """Повертає ідентифікатори правил у порядку ``sh:order``."""
        return [rule.rule for rule in self._validator.rules()]

    def shapes_turtle(self) -> bytes:
        """Повертає правила SHACL у Turtle."""
        return self._validator.shapes_turtle().encode()

    def report_turtle(self) -> bytes | None:
        """Повертає звіт останньої перевірки в Turtle або ``None``, якщо перевірки ще не було."""
        path = self._validator.report_path
        return path.read_bytes() if path.exists() else None
