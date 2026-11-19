"""Сховище зауважень перевірки якості за правилами SHACL."""

import sqlite3

from kinograf.models import Film, QualityIssue, Severity
from kinograf.repositories.database import Database
from kinograf.repositories.films import film_from_row

SEVERITY_RANK = "CASE severity WHEN 'violation' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END"


def issue_from_row(row: sqlite3.Row) -> QualityIssue:
    """Створює зауваження з рядка таблиці ``quality_issues``.

    Args:
        row: Рядок зі стовпцями таблиці ``quality_issues``.

    Returns:
        Зауваження.
    """
    return QualityIssue(
        film_qid=row["film_qid"],
        rule=row["rule"],
        severity=Severity(row["severity"]),
        message=row["message"],
        property=row["property"],
        value=row["value"],
    )


class QualityRepository:
    """Зберігає зауваження останньої перевірки й рахує їх за правилами та рівнями.

    Args:
        database: База даних застосунку.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    def replace_all(self, issues: list[QualityIssue]) -> None:
        """Замінює всі зауваження результатами нової перевірки.

        Args:
            issues: Зауваження; для одного фільму й правила — не більше одного.
        """
        with self._database.transaction() as connection:
            connection.execute("DELETE FROM quality_issues")
            connection.executemany(
                "INSERT INTO quality_issues VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        item.film_qid,
                        item.rule,
                        item.severity.value,
                        item.message,
                        item.property,
                        item.value,
                    )
                    for item in issues
                ],
            )

    def films_by_rule(self) -> dict[str, int]:
        """Рахує фільми каталогу із зауваженнями за кожним правилом.

        Returns:
            Кількість фільмів за ідентифікаторами правил; правила без зауважень відсутні.
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                """SELECT rule, COUNT(DISTINCT film_qid) AS films FROM quality_issues
                   WHERE film_qid IN (SELECT qid FROM films) GROUP BY rule"""
            ).fetchall()
        return {row["rule"]: row["films"] for row in rows}

    def films_with_issues(self) -> int:
        """Рахує фільми каталогу, що мають хоча б одне зауваження."""
        return sum(self.films_by_severity().values())

    def films_by_severity(self) -> dict[str, int]:
        """Розподіляє фільми із зауваженнями за найсерйознішим рівнем.

        Returns:
            Кількість фільмів, у яких найсерйозніше зауваження — помилка (``violation``),
            попередження (``warning``) або лише підказки (``info``).
        """
        with self._database.transaction() as connection:
            rows = connection.execute(
                f"""SELECT worst, COUNT(*) AS films FROM (
                        SELECT film_qid, MIN({SEVERITY_RANK}) AS worst FROM quality_issues
                        WHERE film_qid IN (SELECT qid FROM films) GROUP BY film_qid
                    ) GROUP BY worst"""
            ).fetchall()
        counts = dict.fromkeys((severity.value for severity in Severity), 0)
        for row in rows:
            counts[list(Severity)[row["worst"]].value] = row["films"]
        return counts

    def issues(
        self,
        rule: str | None = None,
        severity: Severity | None = None,
        page: int = 1,
        page_size: int = 12,
    ) -> tuple[list[tuple[Film, list[QualityIssue]]], int]:
        """Повертає сторінку фільмів, що мають зауваження за правилом і рівнем.

        Фільми йдуть від найсерйознішого зауваження, далі — за кількістю зауважень, назвою.
        Для кожного фільму повертаються всі його зауваження, а не лише відібрані фільтром.

        Args:
            rule: Ідентифікатор правила або ``None`` — усі правила.
            severity: Рівень або ``None`` — усі рівні.
            page: Номер сторінки, починаючи з 1.
            page_size: Кількість фільмів на сторінці.

        Returns:
            Фільми з їхніми зауваженнями й загальна кількість відібраних фільмів.
        """
        conditions, params = [], []
        if rule is not None:
            conditions.append("rule = ?")
            params.append(rule)
        if severity is not None:
            conditions.append("severity = ?")
            params.append(severity.value)
        where = " AND ".join(conditions) or "1"
        selected = f"SELECT film_qid FROM quality_issues WHERE {where}"
        with self._database.transaction() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM films WHERE qid IN ({selected})", params
            ).fetchone()[0]
            films = connection.execute(
                f"""SELECT films.*, MIN({SEVERITY_RANK}) AS worst, COUNT(*) AS issues
                    FROM films JOIN quality_issues ON quality_issues.film_qid = films.qid
                    WHERE films.qid IN ({selected})
                    GROUP BY films.qid
                    ORDER BY worst, issues DESC, title COLLATE uk
                    LIMIT ? OFFSET ?""",
                [*params, page_size, (page - 1) * page_size],
            ).fetchall()
            qids = [row["qid"] for row in films]
            placeholders = ", ".join("?" * len(qids))
            rows = connection.execute(
                f"""SELECT * FROM quality_issues WHERE film_qid IN ({placeholders})
                    ORDER BY {SEVERITY_RANK}, rowid""",
                qids,
            ).fetchall()
        grouped: dict[str, list[QualityIssue]] = {qid: [] for qid in qids}
        for row in rows:
            grouped[row["film_qid"]].append(issue_from_row(row))
        return [(film_from_row(row), grouped[row["qid"]]) for row in films], total
