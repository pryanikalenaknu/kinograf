"""Тести перевірки за правилами SHACL: правила, зауваження, сховище, сервіс і маршрути."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from rdflib import RDFS, XSD, Graph, Literal, URIRef
from rdflib.plugins.sparql.sparql import QueryContext

from kinograf.api import create_app
from kinograf.config import Settings
from kinograf.models import QualityIssue, Severity
from kinograf.opendata import WikidataLoader
from kinograf.rdf import WD, WDT, ShaclValidator
from kinograf.rdf.shacl import SHAPES_PATH
from kinograf.repositories import LogRepository, QualityRepository, StatsRepository
from kinograf.services import QualityService, Services

TODAY = datetime(2026, 10, 30, tzinfo=UTC)

RULES = [
    ("release-date", Severity.VIOLATION, "P577"),
    ("duration-range", Severity.VIOLATION, "P2047"),
    ("title-uk", Severity.WARNING, None),
    ("director", Severity.WARNING, "P57"),
    ("cast", Severity.WARNING, "P161"),
    ("genre", Severity.WARNING, "P136"),
    ("duration", Severity.INFO, "P2047"),
    ("screenwriter", Severity.INFO, "P58"),
    ("image", Severity.INFO, "P18"),
    ("announced", Severity.INFO, "P577"),
]


@pytest.fixture
def fixed_today(monkeypatch):
    """Підставляє поточну дату 30.10.2026 для ``NOW()`` у SPARQL-обмеженні."""
    monkeypatch.setattr(QueryContext, "now", property(lambda self: TODAY))


def film(graph: Graph, qid: str, title: str, **values) -> URIRef:
    """Додає до графа фільм з країною, назвою й переданими властивостями ``P…``."""
    node = WD[qid]
    graph.add((node, WDT.P495, WD.Q212))
    graph.add((node, RDFS.label, Literal(title, lang="uk")))
    for prop, value in values.items():
        graph.add((node, WDT[prop], value))
    return node


@pytest.fixture
def graph() -> Graph:
    """Маленький граф, де кожне правило спрацьовує хоча б раз."""
    graph = Graph()
    film(graph, "Q1", "Prostchennia", P2047=Literal(5345, datatype=XSD.integer))
    film(
        graph,
        "Q2",
        "Анонс",
        P577=Literal("2026-11-01", datatype=XSD.date),
        P57=WD.Q10,
        P161=WD.Q11,
        P136=WD.Q12,
        P58=WD.Q10,
        P18=URIRef("http://commons.wikimedia.org/wiki/Special:FilePath/A.jpg"),
    )
    film(
        graph,
        "Q3",
        "Поводир",
        P577=Literal("2014-11-13", datatype=XSD.date),
        P2047=Literal(122, datatype=XSD.integer),
        P57=WD.Q10,
        P161=WD.Q11,
        P136=WD.Q12,
        P58=WD.Q10,
        P18=URIRef("http://commons.wikimedia.org/wiki/Special:FilePath/P.jpg"),
    )
    film(graph, "Q4", "Мамай", P577=Literal("2003"))
    graph.add((WD.Q10, RDFS.label, Literal("Режисер", lang="uk")))
    return graph


@pytest.fixture
def validator(tmp_path) -> ShaclValidator:
    return ShaclValidator(tmp_path / "data" / "shacl-report.ttl")


def test_rules_are_read_from_shapes_in_order(validator):
    rules = validator.rules()
    assert [(rule.rule, rule.severity, rule.property) for rule in rules] == RULES
    assert [rule.order for rule in rules] == list(range(1, 11))
    assert rules[1].name == "Тривалість від 1 до 600 хв"
    assert rules[3].message == "Не вказано режисера"
    assert rules[9].name == "Фільм уже вийшов"


def test_every_rule_fires_on_small_graph(validator, graph, fixed_today):
    issues = validator.validate(graph)
    by_film = {}
    for issue in issues:
        by_film.setdefault(issue.film_qid, set()).add(issue.rule)
    assert by_film["Q1"] == {
        "release-date",
        "duration-range",
        "title-uk",
        "director",
        "cast",
        "genre",
        "screenwriter",
        "image",
    }
    assert by_film["Q2"] == {"duration", "announced"}
    assert "Q3" not in by_film
    assert "release-date" in by_film["Q4"]
    assert {issue.rule for issue in issues} == {rule for rule, _, _ in RULES}


def test_issue_details_and_fix_links(validator, graph, fixed_today):
    issues = {(issue.film_qid, issue.rule): issue for issue in validator.validate(graph)}
    duration = issues[("Q1", "duration-range")]
    assert (duration.severity, duration.value, duration.property) == (
        Severity.VIOLATION,
        "5345",
        "P2047",
    )
    assert duration.message == "Тривалість поза межами 1–600 хв"
    assert duration.fix_url == "https://www.wikidata.org/wiki/Q1#P2047"
    title = issues[("Q1", "title-uk")]
    assert (title.severity, title.property, title.value) == (Severity.WARNING, None, "Prostchennia")
    assert title.fix_url == "https://www.wikidata.org/wiki/Q1"
    announced = issues[("Q2", "announced")]
    assert (announced.severity, announced.value) == (Severity.INFO, "2026-11-01")
    assert announced.fix_url == "https://www.wikidata.org/wiki/Q2#P577"
    assert issues[("Q2", "duration")].severity == Severity.INFO
    assert issues[("Q4", "release-date")].fix_url.endswith("#P577")


def test_announced_depends_on_current_date(validator, graph, monkeypatch):
    later = datetime(2026, 11, 2, tzinfo=UTC)
    monkeypatch.setattr(QueryContext, "now", property(lambda self: later))
    assert ("Q2", "announced") not in {
        (issue.film_qid, issue.rule) for issue in validator.validate(graph)
    }


def test_report_is_written_and_parses(validator, graph, fixed_today):
    validator.validate(graph)
    report = Graph().parse(validator.report_path, format="turtle")
    results = set(report.subjects(None, URIRef("http://www.w3.org/ns/shacl#ValidationResult")))
    assert len(results) >= 10
    assert not validator.report_path.with_suffix(".tmp").exists()


def test_shapes_turtle_is_file_as_is(validator):
    assert validator.shapes_turtle() == SHAPES_PATH.read_text(encoding="utf-8")
    assert SHAPES_PATH.name == "shapes.ttl"


ISSUES = [
    QualityIssue("Q1", "director", Severity.WARNING, "Не вказано режисера", "P57"),
    QualityIssue("Q1", "image", Severity.INFO, "Немає зображення (постера)", "P18"),
    QualityIssue("Q2", "duration-range", Severity.VIOLATION, "Тривалість", "P2047", "5345"),
    QualityIssue("Q2", "image", Severity.INFO, "Немає зображення (постера)", "P18"),
    QualityIssue("Q3", "image", Severity.INFO, "Немає зображення (постера)", "P18"),
    QualityIssue("Q4", "cast", Severity.WARNING, "Не вказано акторів", "P161"),
    QualityIssue("Q4", "screenwriter", Severity.INFO, "Не вказано сценариста", "P58"),
    QualityIssue("Q4", "image", Severity.INFO, "Немає зображення (постера)", "P18"),
    QualityIssue("Q999", "image", Severity.INFO, "Немає зображення (постера)", "P18"),
]


@pytest.fixture
def quality(filled_database) -> QualityRepository:
    repository = QualityRepository(filled_database)
    repository.replace_all(ISSUES)
    return repository


def test_repository_counts_films_by_rule_and_severity(quality):
    assert quality.films_by_rule() == {
        "director": 1,
        "image": 4,
        "duration-range": 1,
        "cast": 1,
        "screenwriter": 1,
    }
    assert quality.films_by_severity() == {"violation": 1, "warning": 2, "info": 1}
    assert quality.films_with_issues() == 4


def test_repository_orders_by_worst_issue_then_count(quality):
    films, total = quality.issues()
    assert total == 4
    assert [(film.qid, len(issues)) for film, issues in films] == [
        ("Q2", 2),
        ("Q4", 3),
        ("Q1", 2),
        ("Q3", 1),
    ]


def test_repository_filters_and_keeps_all_issues_of_film(quality):
    films, total = quality.issues(rule="cast")
    assert total == 1
    assert [issue.rule for issue in films[0][1]] == ["cast", "screenwriter", "image"]
    films, total = quality.issues(severity=Severity.INFO, page=2, page_size=3)
    assert total == 4
    assert [film.qid for film, _ in films] == ["Q3"]
    assert quality.issues(rule="director", severity=Severity.INFO) == ([], 0)


def test_repository_replaces_previous_issues(quality):
    quality.replace_all(ISSUES[:1])
    assert quality.films_by_rule() == {"director": 1}


def test_service_report_and_issue_order(filled_database, quality, tmp_path):
    validator = ShaclValidator(tmp_path / "report.ttl")
    logs = LogRepository(filled_database)
    service = QualityService(validator, quality, StatsRepository(filled_database), logs)
    report = service.report()
    assert report.checked_at is None
    assert (report.films_checked, report.films_with_issues) == (7, 4)
    assert [(item.rule.rule, item.films) for item in report.rules][:3] == [
        ("release-date", 0),
        ("duration-range", 1),
        ("title-uk", 0),
    ]
    page = service.issues(rule="cast")
    assert [issue.rule for issue in page.items[0].issues] == ["cast", "screenwriter", "image"]
    assert (page.total, page.page) == (1, 1)
    assert service.report_turtle() is None
    assert service.shapes_turtle().startswith(b"@prefix sh:")


@pytest.fixture
def services(filled_database, rdf_store, fake_client) -> Services:
    settings = Settings(
        database_path=str(filled_database.path),
        graph_path=str(rdf_store.path),
        linked_path=str(rdf_store.path.with_name("linked.ttl")),
        report_path=str(rdf_store.path.with_name("shacl-report.ttl")),
    )
    return Services.create(settings, WikidataLoader(fake_client, 1991))


def test_quality_routes_before_first_check(services):
    client = TestClient(create_app(services))
    body = client.get("/api/quality/rules").json()
    assert body["checked_at"] is None
    assert len(body["rules"]) == 10
    assert all(item["films"] == 0 for item in body["rules"])
    assert client.get("/api/quality/issues").json() == {"items": [], "total": 0, "page": 1}
    assert client.get("/api/quality/report.ttl").status_code == 404


def test_quality_routes_after_update(services, fixed_today):
    log = services.update.run(services.update.start())
    assert (log.status, log.stage) == ("success", "validation")
    client = TestClient(create_app(services))
    body = client.get("/api/quality/rules").json()
    assert body["checked_at"] is not None
    assert (body["films_checked"], body["films_with_issues"]) == (2, 2)
    assert body["by_severity"] == {"violation": 0, "warning": 2, "info": 0}
    counts = {item["rule"]["rule"]: item["films"] for item in body["rules"]}
    assert (counts["cast"], counts["screenwriter"], counts["image"]) == (2, 1, 1)
    assert body["rules"][9]["rule"] == {
        "rule": "announced",
        "name": "Фільм уже вийшов",
        "severity": "info",
        "message": "Дата виходу ще не настала: фільм анонсовано",
        "property": "P577",
        "order": 10,
    }
    page = client.get("/api/quality/issues", params={"rule": "image"}).json()
    assert page["total"] == 1
    item = page["items"][0]
    assert item["film"]["qid"] == "Q2"
    assert [issue["rule"] for issue in item["issues"]] == ["cast", "screenwriter", "image"]
    assert item["issues"][0]["fix_url"] == "https://www.wikidata.org/wiki/Q2#P161"
    warnings = client.get("/api/quality/issues", params={"severity": "warning"}).json()
    assert warnings["total"] == 2
    report = client.get("/api/quality/report.ttl")
    assert report.headers["content-type"] == "text/turtle; charset=utf-8"
    assert "attachment" in report.headers["content-disposition"]
    Graph().parse(data=report.text, format="turtle")
    shapes = client.get("/api/quality/shapes.ttl")
    assert shapes.text == SHAPES_PATH.read_text(encoding="utf-8")


def test_quality_issue_filters_are_validated(services):
    client = TestClient(create_app(services))
    assert client.get("/api/quality/issues", params={"rule": "unknown"}).status_code == 422
    assert client.get("/api/quality/issues", params={"severity": "fatal"}).status_code == 422
    assert client.get("/api/quality/issues", params={"page": 0}).status_code == 422
