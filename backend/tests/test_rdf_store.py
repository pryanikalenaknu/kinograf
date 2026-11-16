"""Тести RDF-графа: побудова, збереження, SPARQL-запити, сусіди, експорт."""

import threading
import time
from datetime import date

import pytest
from rdflib import Graph

from kinograf.models import Film
from kinograf.rdf import RdfStore, SparqlBusyError, SparqlError, SparqlTimeoutError

DIRECTED_BY_SANIN = """
SELECT ?title ?year WHERE {
  ?film wdt:P57 wd:Q11 ; rdfs:label ?title ; wdt:P577 ?date .
  BIND(YEAR(?date) AS ?year)
} ORDER BY ?year
"""


def test_rebuild_saves_graph_that_load_restores(rdf_store, tmp_path):
    assert (tmp_path / "graph.ttl").exists()
    restored = RdfStore(tmp_path / "graph.ttl")
    restored.load()
    assert len(restored) == len(rdf_store) > 0


def test_load_without_file_keeps_empty_graph(tmp_path):
    store = RdfStore(tmp_path / "missing.ttl")
    store.load()
    assert len(store) == 0


def test_query_select_returns_columns_and_rows(rdf_store):
    result = rdf_store.query(DIRECTED_BY_SANIN)
    assert result.columns == ["title", "year"]
    assert result.rows == [{"title": "Мамай", "year": "2003"}, {"title": "Поводир", "year": "2014"}]
    assert not result.truncated


def test_query_omits_unbound_variables(rdf_store):
    result = rdf_store.query(
        """SELECT ?film ?minutes WHERE {
             ?film wdt:P31 wd:Q11424 . OPTIONAL { ?film wdt:P2047 ?minutes }
             FILTER(?film IN (wd:Q1, wd:Q7))
           } ORDER BY ?film"""
    )
    assert result.rows == [
        {"film": "http://www.wikidata.org/entity/Q1", "minutes": "132"},
        {"film": "http://www.wikidata.org/entity/Q7"},
    ]


def test_query_limits_rows(rdf_store):
    rdf_store.max_rows = 2
    result = rdf_store.query("SELECT ?film WHERE { ?film wdt:P31 wd:Q11424 }")
    assert len(result.rows) == 2
    assert result.truncated


def test_query_stops_after_timeout(rdf_store):
    rdf_store.timeout = 0.05
    rdf_store.max_rows = 10**9
    with pytest.raises(SparqlTimeoutError, match="0.05"):
        rdf_store.query("SELECT * WHERE { ?a ?b ?c . ?d ?e ?f . ?g ?h ?i . ?j ?k ?l }")


@pytest.mark.parametrize(
    "query",
    [
        "ASK { ?s ?p ?o }",
        "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
        "DESCRIBE wd:Q1",
    ],
)
def test_query_refuses_everything_except_select(rdf_store, query):
    with pytest.raises(SparqlError, match="лише запити SELECT"):
        rdf_store.query(query)


def test_query_refuses_update(rdf_store):
    with pytest.raises(SparqlError, match="синтаксична помилка"):
        rdf_store.query("DELETE WHERE { ?s ?p ?o }")
    assert len(rdf_store) > 0


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * WHERE { SERVICE <http://example.org/sparql> { ?s ?p ?o } }",
        "SELECT * FROM <http://example.org/data.ttl> WHERE { ?s ?p ?o }",
    ],
)
def test_query_refuses_external_sources(rdf_store, query):
    with pytest.raises(SparqlError, match="зовнішніх джерел"):
        rdf_store.query(query)


def test_query_reports_syntax_error(rdf_store):
    with pytest.raises(SparqlError, match="синтаксична помилка"):
        rdf_store.query("SELECT ?x WHERE { ?x")


def test_query_reports_evaluation_error(rdf_store, monkeypatch):
    def broken_query(*args, **kwargs):
        raise ValueError("зламано")

    monkeypatch.setattr(rdf_store._graph, "query", broken_query)
    with pytest.raises(SparqlError, match="помилка виконання запиту: зламано"):
        rdf_store.query("SELECT * WHERE { ?s ?p ?o }")


def test_neighbours_of_film_depth_one(rdf_store):
    assert rdf_store.neighbours("Q4", 1) == [
        ("Q4", "composer", "Q14"),
        ("Q4", "director", "Q11"),
        ("Q4", "screenwriter", "Q11"),
    ]


def test_neighbours_of_film_depth_two(rdf_store):
    assert rdf_store.neighbours("Q4", 2) == [
        ("Q3", "composer", "Q14"),
        ("Q3", "director", "Q11"),
        ("Q3", "screenwriter", "Q11"),
        ("Q4", "composer", "Q14"),
        ("Q4", "director", "Q11"),
        ("Q4", "screenwriter", "Q11"),
    ]


def test_neighbours_of_person_depth_one_and_two(rdf_store):
    assert rdf_store.neighbours("Q12", 1) == [
        ("Q5", "director", "Q12"),
        ("Q5", "screenwriter", "Q12"),
        ("Q6", "director", "Q12"),
    ]
    assert rdf_store.neighbours("Q12", 2) == [
        ("Q5", "cast", "Q13"),
        ("Q5", "director", "Q12"),
        ("Q5", "screenwriter", "Q12"),
        ("Q6", "cast", "Q13"),
        ("Q6", "director", "Q12"),
    ]


def test_neighbours_respect_node_limit(rdf_store):
    assert rdf_store.neighbours("Q12", 2, limit=2) == [
        ("Q5", "director", "Q12"),
        ("Q5", "screenwriter", "Q12"),
    ]


def test_neighbours_of_unknown_or_isolated_entity_are_empty(rdf_store):
    assert rdf_store.neighbours("Q999", 2) == []
    assert rdf_store.neighbours("Q7", 2) == []


def test_entities_return_kind_and_label(rdf_store):
    assert rdf_store.entities(["Q1", "Q10", "Q130232", "Q999"]) == {
        "Q1": ("film", "Плем'я"),
        "Q10": ("person", "Мирослав Слабошпицький"),
    }


def test_export_turtle_of_whole_graph_parses_back(rdf_store):
    graph = Graph().parse(data=rdf_store.export_turtle(), format="turtle")
    assert len(graph) == len(rdf_store)


def test_export_turtle_of_selected_films(rdf_store):
    turtle = rdf_store.export_turtle(["Q1"])
    graph = Graph().parse(data=turtle, format="turtle")
    assert "Плем'я" in turtle
    assert "Мирослав Слабошпицький" in turtle
    assert "Атлантида" not in turtle
    assert "@prefix wd:" in turtle
    assert len(graph) > 0


def test_query_select_star_keeps_variable_order_of_query(rdf_store):
    result = rdf_store.query(
        "SELECT * WHERE { ?film wdt:P57 ?director . ?director rdfs:label ?name }"
    )
    assert result.columns == ["film", "director", "name"]
    explicit = rdf_store.query(
        "SELECT ?name ?film WHERE { ?film wdt:P57 ?d . ?d rdfs:label ?name }"
    )
    assert explicit.columns == ["name", "film"]


HEAVY = "SELECT (COUNT(*) AS ?n) WHERE { ?a ?b ?c . ?d ?e ?f . ?g ?h ?i . ?j ?k ?l }"


def sparql_threads():
    return [thread for thread in threading.enumerate() if thread.name == "sparql-query"]


def test_timed_out_query_stops_computing(rdf_store):
    rdf_store.timeout = 0.2
    with pytest.raises(SparqlTimeoutError):
        rdf_store.query(HEAVY)
    deadline = time.monotonic() + 3
    while sparql_threads() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert sparql_threads() == []


def test_query_is_refused_while_console_is_busy(tmp_path, rdf_store):
    busy = RdfStore(rdf_store.path, timeout=1.0, max_concurrent=1)
    busy.load()
    worker = threading.Thread(target=lambda: pytest.raises(SparqlTimeoutError, busy.query, HEAVY))
    worker.start()
    time.sleep(0.2)
    with pytest.raises(SparqlBusyError, match="зайнята"):
        busy.query("SELECT ?film WHERE { ?film wdt:P31 wd:Q11424 }")
    worker.join()
    assert len(busy.query("SELECT ?film WHERE { ?film wdt:P31 wd:Q11424 }").rows) == 7


def test_store_reloads_graph_written_by_another_process(rdf_store, tmp_path):
    reader = RdfStore(rdf_store.path)
    reader.load()
    assert "Q8" not in reader.entities(["Q8"])
    time.sleep(0.01)
    writer = RdfStore(rdf_store.path)
    writer.rebuild([Film("Q8", "Носоріг", date(2021, 9, 5))], [], [], {}, {})
    assert reader.entities(["Q8"]) == {"Q8": ("film", "Носоріг")}
    assert reader.neighbours("Q4", 1) == []
