"""Тести сервісів читання даних на тестовій базі й тестовому RDF-графі."""

import csv
import io
import json
from datetime import UTC, date, datetime

import pytest
from rdflib import Graph

from kinograf.models import Film, Person, Role
from kinograf.repositories import (
    FilmRepository,
    LogRepository,
    PersonRepository,
    StatsRepository,
)
from kinograf.services import (
    CatalogService,
    ExportService,
    FilmFilters,
    FilmService,
    GraphService,
    PersonService,
    RankedPerson,
    SparqlError,
    SparqlService,
    StatsService,
)
from kinograf.services.export import safe_cell


@pytest.fixture
def films(filled_database) -> FilmRepository:
    return FilmRepository(filled_database)


@pytest.fixture
def people(filled_database) -> PersonRepository:
    return PersonRepository(filled_database)


def test_catalog_search_returns_page_of_twelve(films, people):
    page = CatalogService(films, people).search("", FilmFilters(period="2014-now"), "title", 1)
    assert [item.film.qid for item in page.items] == ["Q5", "Q6", "Q2", "Q1", "Q4"]
    assert (page.total, page.page) == (5, 1)


def test_catalog_items_carry_directors_and_genres(films, people):
    page = CatalogService(films, people).search("", FilmFilters(), "year", 1)
    by_qid = {item.film.qid: item for item in page.items}
    assert [person.name for person in by_qid["Q2"].directors] == ["Ірина Цілик"]
    assert [genre.name for genre in by_qid["Q4"].genres] == ["драма", "історичний фільм"]
    assert by_qid["Q7"].directors == []
    assert by_qid["Q7"].genres == []


def test_catalog_page_beyond_results_is_empty(films, people):
    page = CatalogService(films, people).search("", FilmFilters(), page=2)
    assert page.items == []
    assert page.total == 7


def test_catalog_lists_for_filters(films, people):
    catalog = CatalogService(films, people)
    assert [genre.qid for genre in catalog.genres()] == ["Q93204", "Q130232", "Q17013749"]
    assert [person.qid for person in catalog.directors()] == ["Q12", "Q15", "Q10", "Q11"]


def test_film_details_collect_everything(films, people):
    details = FilmService(films, people).details("Q4")
    assert details.film.title == "Поводир"
    assert details.participants[Role.DIRECTOR] == [Person("Q11", "Олесь Санін")]
    assert details.participants[Role.CAST] == []
    assert [genre.name for genre in details.genres] == ["драма", "історичний фільм"]
    assert details.awards == []
    first = details.related[0]
    assert (first.film.qid, first.shared_people, first.shared_genres) == ("Q3", 2, 2)
    assert len(details.related) == 4


def test_film_details_of_unknown_film(films, people):
    assert FilmService(films, people).details("Q999") is None


def test_person_profile_merges_roles_per_film(people):
    profile = PersonService(people).profile("Q11")
    assert profile.person.name == "Олесь Санін"
    assert [(entry.film.qid, entry.roles) for entry in profile.filmography] == [
        ("Q4", [Role.DIRECTOR, Role.SCREENWRITER]),
        ("Q3", [Role.DIRECTOR, Role.SCREENWRITER]),
    ]
    assert profile.collaborators == [RankedPerson(Person("Q14", "Алла Загайкевич"), 2)]


def test_person_profile_of_unknown_person(people):
    assert PersonService(people).profile("Q999") is None


def test_stats_overview(filled_database):
    logs = LogRepository(filled_database)
    service = StatsService(StatsRepository(filled_database), logs)
    assert service.overview().last_updated is None
    log = logs.start()
    log.status = "success"
    logs.finish(log)
    stats = service.overview()
    assert stats.films_by_year[2014] == 2
    assert stats.genres_by_period["2014-now"]["драма"] == 4
    assert [(top.person.qid, top.films) for top in stats.top_directors][:2] == [
        ("Q12", 2),
        ("Q11", 2),
    ]
    assert [top.person.qid for top in stats.top_actors] == ["Q13", "Q16"]
    assert stats.completeness["poster"] == pytest.approx(2 / 7)
    assert stats.completeness_by_year[2014]["cast"] == 0.5
    assert stats.last_updated == log.finished_at
    assert stats.last_updated <= datetime.now(UTC)


def test_graph_of_film_depth_one(rdf_store):
    graph = GraphService(rdf_store).neighbourhood("Q4", 1)
    assert graph.nodes == [
        {"id": "Q11", "label": "Олесь Санін", "type": "person", "level": 1},
        {"id": "Q14", "label": "Алла Загайкевич", "type": "person", "level": 1},
        {"id": "Q4", "label": "Поводир", "type": "film", "level": 0},
    ]
    assert graph.edges == [
        {"from": "Q4", "to": "Q14", "roles": ["composer"]},
        {"from": "Q4", "to": "Q11", "roles": ["director", "screenwriter"]},
    ]


def test_graph_of_person_depth_two_marks_levels(rdf_store):
    graph = GraphService(rdf_store).neighbourhood("Q12", 2)
    levels = {node["id"]: node["level"] for node in graph.nodes}
    assert levels == {"Q12": 0, "Q5": 1, "Q6": 1, "Q13": 2}
    assert len(graph.edges) == 4


def test_graph_of_isolated_film_has_only_centre(rdf_store):
    graph = GraphService(rdf_store).neighbourhood("Q7", 2)
    assert graph.nodes == [{"id": "Q7", "label": "Їжак", "type": "film", "level": 0}]
    assert graph.edges == []


def test_graph_of_unknown_entity(rdf_store):
    assert GraphService(rdf_store).neighbourhood("Q999", 1) is None
    assert GraphService(rdf_store).neighbourhood("Q130232", 1) is None


def test_sparql_execute_measures_time(rdf_store):
    result = SparqlService(rdf_store).execute(
        "SELECT ?name WHERE { wd:Q5 wdt:P161 ?actor . ?actor rdfs:label ?name }"
    )
    assert result.columns == ["name"]
    assert result.rows == [{"name": "Андрій Римарук"}]
    assert not result.truncated
    assert result.elapsed_ms >= 0


def test_sparql_execute_refuses_non_select(rdf_store):
    with pytest.raises(SparqlError):
        SparqlService(rdf_store).execute("ASK { ?s ?p ?o }")


def test_export_films_csv_has_bom_header_and_filtered_rows(films, rdf_store):
    content = ExportService(films, rdf_store).export_films(
        "csv", "", FilmFilters(director="Q12"), "title"
    )
    assert content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    assert [row["title"] for row in rows] == ["Атлантида", "Відблиск"]
    assert rows[0]["wikidata_url"] == "https://www.wikidata.org/wiki/Q5"
    assert rows[0]["year"] == "2019"


def test_export_films_json_contains_all_results(films, rdf_store):
    content = ExportService(films, rdf_store).export_films("json", "", FilmFilters())
    records = json.loads(content)
    assert len(records) == 7
    assert records[0] == {
        "qid": "Q6",
        "title": "Відблиск",
        "year": 2021,
        "release_date": "2021-09-01",
        "duration_min": 127,
        "image_url": None,
        "wikidata_url": "https://www.wikidata.org/wiki/Q6",
    }


def test_export_films_turtle_describes_found_films(films, rdf_store):
    content = ExportService(films, rdf_store).export_films("ttl", "мамай", FilmFilters())
    turtle = content.decode()
    Graph().parse(data=turtle, format="turtle")
    assert "Мамай" in turtle
    assert "Поводир" not in turtle


def test_export_sparql_csv_and_json(films, rdf_store):
    export = ExportService(films, rdf_store)
    query = "SELECT ?film ?title WHERE { ?film wdt:P57 wd:Q12 ; rdfs:label ?title } ORDER BY ?title"
    rows = list(csv.reader(io.StringIO(export.export_sparql("csv", query).decode("utf-8-sig"))))
    assert rows[0] == ["film", "title"]
    assert rows[1] == ["http://www.wikidata.org/entity/Q5", "Атлантида"]
    assert json.loads(export.export_sparql("json", query))[1]["title"] == "Відблиск"


def test_export_sparql_turtle_describes_entities_in_result(films, rdf_store):
    export = ExportService(films, rdf_store)
    turtle = export.export_sparql("ttl", "SELECT ?film WHERE { ?film wdt:P166 ?award }").decode()
    assert "Атлантида" in turtle
    assert "Земля блакитна" in turtle
    assert "Поводир" not in turtle


def test_export_refuses_unknown_format(films, rdf_store):
    export = ExportService(films, rdf_store)
    with pytest.raises(ValueError, match="xml"):
        export.export_films("xml", "", FilmFilters())
    with pytest.raises(ValueError, match="xml"):
        export.export_sparql("xml", "SELECT * WHERE { ?s ?p ?o }")


def test_export_csv_escapes_formulas(filled_database, rdf_store):
    films = FilmRepository(filled_database)
    films.replace_all([Film("Q9", '=HYPERLINK("http://evil","click")', date(2020, 1, 1))], {}, {})
    rows = list(
        csv.DictReader(
            io.StringIO(
                ExportService(films, rdf_store)
                .export_films("csv", "", FilmFilters())
                .decode("utf-8-sig")
            )
        )
    )
    assert rows[0]["title"] == '\'=HYPERLINK("http://evil","click")'


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=1+1", "'=1+1"),
        ("+380", "'+380"),
        ("-x", "'-x"),
        ("@a", "'@a"),
        ("Мамай", "Мамай"),
        (5, 5),
    ],
)
def test_safe_cell(value, expected):
    assert safe_cell(value) == expected
