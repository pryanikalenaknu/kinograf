"""Тести маршрутів зв'язаних даних і узгодження формату через TestClient."""

import csv
import io
import json

import pytest
from fastapi.testclient import TestClient
from rdflib import RDF, Graph, URIRef
from rdflib.namespace import VOID

from kinograf.api import create_app
from kinograf.config import Settings
from kinograf.rdf import SCHEMA
from kinograf.repositories import LinkRepository, LogRepository
from kinograf.services import Services, negotiate_media
from tests import sample_data

BASE = "http://kino.test"
OFFERS = ["text/html", "text/turtle", "application/ld+json"]


@pytest.fixture
def client(filled_database, rdf_store, linked_store) -> TestClient:
    LinkRepository(filled_database).replace_all(sample_data.LINKS)
    logs = LogRepository(filled_database)
    log = logs.start()
    log.status = "success"
    logs.finish(log)
    settings = Settings(
        database_path=str(filled_database.path),
        graph_path=str(rdf_store.path),
        linked_path=str(linked_store.path),
        report_path=str(linked_store.path.with_name("shacl-report.ttl")),
        base_url=BASE,
    )
    return TestClient(create_app(Services.create(settings)), follow_redirects=False)


@pytest.mark.parametrize(
    ("accept", "expected"),
    [
        (None, "text/html"),
        ("", "text/html"),
        ("*/*", "text/html"),
        ("text/turtle", "text/turtle"),
        ("application/ld+json", "application/ld+json"),
        ("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "text/html"),
        ("text/turtle;q=0.5, application/ld+json;q=0.9", "application/ld+json"),
        ("text/turtle, */*;q=0.1", "text/turtle"),
        ("text/*;q=0.9, text/html;q=0.1", "text/turtle"),
        ("text/turtle;q=0, */*", "text/html"),
        ("TEXT/Turtle", "text/turtle"),
        ("text/turtle;q=abc, application/ld+json;q=0.2", "application/ld+json"),
        ("image/png", None),
    ],
)
def test_negotiate_media_with_weights(accept, expected):
    assert negotiate_media(accept, OFFERS) == expected


@pytest.mark.parametrize(
    ("path", "accept", "location"),
    [
        ("/id/film/Q1", "text/turtle", "/data/film/Q1.ttl"),
        ("/id/film/Q1", "application/ld+json", "/data/film/Q1.jsonld"),
        ("/id/film/Q1", "text/html", "/films/Q1"),
        ("/id/film/Q1", "*/*", "/films/Q1"),
        ("/id/film/Q1", "text/turtle;q=0.4, application/ld+json;q=0.8", "/data/film/Q1.jsonld"),
        ("/id/person/Q11", "text/turtle", "/data/person/Q11.ttl"),
        ("/id/person/Q11", "text/html", "/people/Q11"),
    ],
)
def test_persistent_uri_redirects_by_accept(client, path, accept, location):
    response = client.get(path, headers={"Accept": accept})
    assert response.status_code == 303
    assert response.headers["location"] == location
    assert response.headers["vary"] == "Accept"
    assert response.headers["access-control-allow-origin"] == "*"


def test_persistent_uri_answers_head(client):
    response = client.head("/id/film/Q1", headers={"Accept": "text/turtle"})
    assert response.status_code == 303
    assert response.headers["location"] == "/data/film/Q1.ttl"


def test_redirect_leads_to_turtle_movie(client):
    response = client.get("/id/film/Q1", headers={"Accept": "text/turtle"}, follow_redirects=True)
    assert response.status_code == 200
    graph = Graph().parse(data=response.text, format="turtle")
    assert (URIRef(f"{BASE}/id/film/Q1"), RDF.type, SCHEMA.Movie) in graph


@pytest.mark.parametrize(
    "path",
    [
        "/id/film/Q999",
        "/id/person/Q1",
        "/id/film/Q11",
        "/id/series/Q1",
        "/id/film/abc",
        "/data/film/Q999.ttl",
        "/data/film/Q1.xml",
        "/data/person/Q1.jsonld",
    ],
)
def test_unknown_entity_is_not_found(client, path):
    response = client.get(path, headers={"Accept": "text/turtle"})
    assert response.status_code == 404
    assert response.headers["access-control-allow-origin"] == "*"
    assert response.headers["vary"] == "Accept"


def test_turtle_document_of_film(client):
    response = client.get("/data/film/Q1.ttl")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/turtle; charset=utf-8"
    graph = Graph().parse(data=response.text, format="turtle")
    film = URIRef(f"{BASE}/id/film/Q1")
    assert (film, SCHEMA.director, URIRef(f"{BASE}/id/person/Q10")) in graph
    assert (film, SCHEMA.sameAs, URIRef("https://www.imdb.com/title/tt3904770/")) in graph


def test_jsonld_document_of_person(client):
    response = client.get("/data/person/Q11.jsonld")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/ld+json"
    data = response.json()
    assert data["@context"]["@vocab"] == "https://schema.org/"
    assert "Олесь Санін" in response.text
    graph = Graph().parse(data=response.text, format="json-ld")
    person = URIRef(f"{BASE}/id/person/Q11")
    assert (URIRef(f"{BASE}/id/film/Q4"), SCHEMA.director, person) in graph


def test_dump_is_whole_published_graph(client):
    response = client.get("/data/kinograf.ttl")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/turtle; charset=utf-8"
    graph = Graph().parse(data=response.text, format="turtle")
    assert len(set(graph.subjects(RDF.type, SCHEMA.Movie))) == len(sample_data.FILMS)


def test_void_parses_in_rdflib(client):
    response = client.get("/.well-known/void")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/turtle; charset=utf-8"
    assert response.headers["access-control-allow-origin"] == "*"
    graph = Graph().parse(data=response.text, format="turtle")
    dataset = URIRef(f"{BASE}/.well-known/void#dataset")
    assert (dataset, RDF.type, VOID.Dataset) in graph
    assert (dataset, VOID.sparqlEndpoint, URIRef(f"{BASE}/data/sparql")) in graph
    assert len(list(graph.subjects(RDF.type, VOID.Linkset))) == 4
    assert graph.value(dataset, URIRef("http://purl.org/dc/terms/modified")) is not None


def test_void_as_jsonld(client):
    response = client.get("/.well-known/void", headers={"Accept": "application/ld+json"})
    assert response.headers["content-type"] == "application/ld+json"
    graph = Graph().parse(data=response.text, format="json-ld")
    assert (URIRef(f"{BASE}/.well-known/void#dataset"), RDF.type, VOID.Dataset) in graph


FILMS_QUERY = (
    "SELECT ?film ?name WHERE { ?film a schema:Movie ; schema:name ?name } ORDER BY ?film LIMIT 2"
)


def test_sparql_get_returns_results_json(client):
    response = client.get("/data/sparql", params={"query": FILMS_QUERY})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/sparql-results+json"
    assert response.headers["access-control-allow-origin"] == "*"
    body = response.json()
    assert body["head"]["vars"] == ["film", "name"]
    first = body["results"]["bindings"][0]
    assert first["film"] == {"type": "uri", "value": f"{BASE}/id/film/Q1"}
    assert first["name"] == {"type": "literal", "value": "Плем'я", "xml:lang": "uk"}


def test_sparql_post_form(client):
    response = client.post("/data/sparql", data={"query": FILMS_QUERY})
    assert response.status_code == 200
    assert len(response.json()["results"]["bindings"]) == 2


def test_sparql_post_query_body(client):
    response = client.post(
        "/data/sparql",
        content=FILMS_QUERY.encode(),
        headers={"Content-Type": "application/sparql-query"},
    )
    assert response.status_code == 200
    assert len(response.json()["results"]["bindings"]) == 2


def test_sparql_csv_results(client):
    response = client.get(
        "/data/sparql", params={"query": FILMS_QUERY}, headers={"Accept": "text/csv"}
    )
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == ["film", "name"]
    assert rows[1] == [f"{BASE}/id/film/Q1", "Плем'я"]


def test_sparql_ask(client):
    query = "ASK { ?film owl:sameAs wd:Q1 }"
    response = client.get("/data/sparql", params={"query": query})
    assert response.json() == {"head": {}, "boolean": True}
    csv_response = client.get(
        "/data/sparql", params={"query": query}, headers={"Accept": "text/csv"}
    )
    assert csv_response.text.split() == ["boolean", "true"]


@pytest.mark.parametrize(
    "query",
    [
        "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
        "DESCRIBE <http://kino.test/id/film/Q1>",
        "SELECT * WHERE { SERVICE <https://query.wikidata.org/sparql> { ?s ?p ?o } }",
        "SELECT * FROM <http://example.org/> WHERE { ?s ?p ?o }",
        "SELECT WHERE",
    ],
)
def test_sparql_refuses_other_queries(client, query):
    response = client.get("/data/sparql", params={"query": query})
    assert response.status_code == 400
    assert response.headers["access-control-allow-origin"] == "*"


def test_sparql_requires_one_query(client):
    assert client.get("/data/sparql").status_code == 400
    response = client.get("/data/sparql?query=ASK%7B%7D&query=ASK%7B%7D")
    assert response.status_code == 400
    response = client.get(
        "/data/sparql", params={"query": "ASK {}", "default-graph-uri": "http://example.org/"}
    )
    assert response.status_code == 400


def test_sparql_rejects_wrong_body(client):
    response = client.post("/data/sparql", content=b"{}", headers={"Content-Type": "text/plain"})
    assert response.status_code == 415
    response = client.post(
        "/data/sparql", content=b"\xff\xfe", headers={"Content-Type": "application/sparql-query"}
    )
    assert response.status_code == 400
    response = client.post(
        "/data/sparql",
        content=b"query=" + b"x" * (70 * 1024),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 413


def test_sparql_rejects_long_query(client):
    response = client.post("/data/sparql", data={"query": "#" * 20_001})
    assert response.status_code == 413


def test_sparql_preflight(client):
    response = client.options("/data/sparql")
    assert response.status_code == 204
    assert "POST" in response.headers["access-control-allow-methods"]
    assert response.headers["access-control-allow-origin"] == "*"


def test_api_routes_have_no_cors_header(client):
    response = client.get("/api/films/Q1")
    assert "access-control-allow-origin" not in response.headers


def test_film_details_include_links(client):
    links = client.get("/api/films/Q1").json()["links"]
    assert links == {
        "uri": f"{BASE}/id/film/Q1",
        "wikidata": "https://www.wikidata.org/wiki/Q1",
        "imdb": "https://www.imdb.com/title/tt3904770/",
        "wikipedia": "https://uk.wikipedia.org/wiki/%D0%9F%D0%BB%D0%B5%D0%BC'%D1%8F_(%D1%84%D1%96%D0%BB%D1%8C%D0%BC)",
        "dbpedia": "http://dbpedia.org/resource/The_Tribe_(2014_film)",
        "turtle": f"{BASE}/data/film/Q1.ttl",
        "jsonld": f"{BASE}/data/film/Q1.jsonld",
    }


def test_person_profile_includes_links(client):
    links = client.get("/api/people/Q10").json()["links"]
    assert links["uri"] == f"{BASE}/id/person/Q10"
    assert (links["imdb"], links["wikipedia"], links["dbpedia"]) == (None, None, None)


def test_opendata_overview(client):
    response = client.get("/api/opendata")
    assert response.status_code == 200
    body = response.json()
    assert body["base_url"] == BASE
    assert body["license"] == "https://creativecommons.org/publicdomain/zero/1.0/"
    assert (body["films"], body["people"]) == (7, 7)
    assert body["triples"] > 0
    assert body["modified"] is not None
    assert body["example_film"] == "Q1"
    assert body["endpoints"] == {
        "void": f"{BASE}/.well-known/void",
        "dump": f"{BASE}/data/kinograf.ttl",
        "sparql": f"{BASE}/data/sparql",
    }
    assert [
        (item["target"], item["predicate"], item["films"], item["people"])
        for item in body["linksets"]
    ] == [
        ("Wikidata", "owl:sameAs", 7, 7),
        ("Вікіпедія (укр.)", "schema:sameAs", 2, 1),
        ("IMDb", "schema:sameAs", 2, 1),
        ("DBpedia", "owl:sameAs", 1, 1),
    ]
    json.dumps(body)


def test_opendata_of_unpublished_dataset(filled_database, rdf_store, tmp_path):
    settings = Settings(
        database_path=str(filled_database.path),
        graph_path=str(rdf_store.path),
        linked_path=str(tmp_path / "empty" / "linked.ttl"),
        report_path=str(tmp_path / "empty" / "shacl-report.ttl"),
        base_url=BASE,
    )
    client = TestClient(create_app(Services.create(settings)))
    body = client.get("/api/opendata").json()
    assert (body["triples"], body["films"], body["people"], body["example_film"]) == (0, 0, 0, None)
    assert client.get("/data/kinograf.ttl").status_code == 200
    assert client.get("/id/film/Q1").status_code == 404
