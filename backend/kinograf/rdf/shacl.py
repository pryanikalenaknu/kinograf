"""Перевірка записів фільмів за правилами SHACL з файлу ``shapes.ttl``."""

import os
import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, URIRef

from kinograf.models import QualityIssue, Severity
from kinograf.rdf.store import WD, WDT, entity

SH = Namespace("http://www.w3.org/ns/shacl#")
KGS = Namespace("urn:kinograf:shapes:")
SHAPES_PATH = Path(str(files("kinograf.rdf").joinpath("shapes.ttl")))

SEVERITIES = {
    SH.Violation: Severity.VIOLATION,
    SH.Warning: Severity.WARNING,
    SH.Info: Severity.INFO,
}
SELECT_PATH = re.compile(r"wdt:(P\d+)\s+AS\s+\?path")


@dataclass(frozen=True)
class QualityRule:
    """Правило перевірки з ``shapes.ttl``.

    Attributes:
        rule: Ідентифікатор правила — локальна назва в просторі ``urn:kinograf:shapes:``.
        name: Назва правила.
        severity: Рівень зауважень за цим правилом.
        message: Повідомлення для зауважень.
        property: Властивість Wikidata, яку перевіряє правило; для назви — ``None``.
        order: Місце правила в таблиці.
    """

    rule: str
    name: str
    severity: Severity
    message: str
    property: str | None
    order: int


def property_id(path: object) -> str | None:
    """Повертає ідентифікатор властивості Wikidata, наприклад ``P57``, або ``None`` для інших."""
    if isinstance(path, URIRef) and str(path).startswith(str(WDT)):
        return str(path).removeprefix(str(WDT))
    return None


def local_name(node: object) -> str | None:
    """Повертає локальну назву вузла в просторі правил або ``None`` для інших вузлів."""
    if isinstance(node, URIRef) and str(node).startswith(str(KGS)):
        return str(node).removeprefix(str(KGS))
    return None


class ShaclValidator:
    """Перевіряє локальний граф у термінах Wikidata за правилами SHACL.

    Ціль правил — усі підмети ``wdt:P495``. Ідентифікатор зауваження — локальна назва
    ``sh:sourceConstraint`` (для SPARQL-обмежень) або ``sh:sourceShape``; назва, рівень,
    повідомлення й порядок читаються з правил.

    Args:
        report_path: Куди записувати звіт останньої перевірки у Turtle.
        shapes_path: Файл правил; типово ``shapes.ttl`` з пакета.
    """

    def __init__(self, report_path: str | Path, shapes_path: str | Path = SHAPES_PATH) -> None:
        self.report_path = Path(report_path)
        self.shapes_path = Path(shapes_path)
        self._shapes = Graph().parse(self.shapes_path, format="turtle")
        self._rules = self._read_rules()

    def rules(self) -> list[QualityRule]:
        """Повертає правила в порядку ``sh:order``.

        Returns:
            Правила.
        """
        return list(self._rules)

    def _read_rules(self) -> list[QualityRule]:
        """Читає правила з графа форм.

        Рівень SPARQL-обмеження береться з вузлової форми, що його містить, а властивість —
        зі змінної ``?path`` у запиті.
        """
        shapes = self._shapes
        found = []
        for node in set(shapes.subjects(SH.order, None)):
            rule = local_name(node)
            if rule is None:
                continue
            severity = shapes.value(node, SH.severity)
            path = shapes.value(node, SH.path)
            prop = property_id(path)
            select = shapes.value(node, SH.select)
            if select is not None:
                owner = shapes.value(None, SH.sparql, node)
                severity = shapes.value(owner, SH.severity) if owner is not None else None
                match = SELECT_PATH.search(str(select))
                prop = match.group(1) if match else None
            found.append(
                QualityRule(
                    rule=rule,
                    name=str(shapes.value(node, SH.name)),
                    severity=SEVERITIES.get(severity, Severity.VIOLATION),
                    message=str(shapes.value(node, SH.message)),
                    property=prop,
                    order=int(shapes.value(node, SH.order)),
                )
            )
        return sorted(found, key=lambda item: item.order)

    def validate(self, graph: Graph) -> list[QualityIssue]:
        """Перевіряє граф і записує звіт pyshacl у ``report_path``.

        Кілька результатів одного правила для одного фільму об'єднуються в одне зауваження.

        Args:
            graph: Локальний граф фільмів у термінах Wikidata.

        Returns:
            Зауваження, впорядковані за фільмом і порядком правил.
        """
        _, report, _ = validate(
            graph,
            shacl_graph=self._shapes,
            inference="none",
            allow_warnings=True,
            abort_on_first=False,
        )
        self._save(report)
        rules = {rule.rule: rule for rule in self.rules()}
        issues: dict[tuple[str, str], QualityIssue] = {}
        for result in report.subjects(None, SH.ValidationResult):
            focus = report.value(result, SH.focusNode)
            source = report.value(result, SH.sourceConstraint) or report.value(
                result, SH.sourceShape
            )
            rule = rules.get(local_name(source))
            if rule is None or not str(focus).startswith(str(WD)):
                continue
            qid = entity(focus)
            value = report.value(result, SH.value)
            path = report.value(result, SH.resultPath)
            issues.setdefault(
                (qid, rule.rule),
                QualityIssue(
                    film_qid=qid,
                    rule=rule.rule,
                    severity=SEVERITIES.get(report.value(result, SH.resultSeverity), rule.severity),
                    message=rule.message,
                    property=property_id(path) if path is not None else rule.property,
                    value=None if value is None else str(value),
                ),
            )
        return sorted(issues.values(), key=lambda item: (item.film_qid, rules[item.rule].order))

    def shapes_turtle(self) -> str:
        """Повертає текст правил так, як він записаний у файлі."""
        return self.shapes_path.read_text(encoding="utf-8")

    def _save(self, report: Graph) -> None:
        """Атомарно записує звіт перевірки."""
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        report.bind("sh", SH)
        report.bind("wd", WD)
        report.bind("wdt", WDT)
        report.bind("kgs", KGS)
        temporary = self.report_path.with_suffix(".tmp")
        report.serialize(temporary, format="turtle")
        os.replace(temporary, self.report_path)
