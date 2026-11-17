"""Тести REST API через TestClient: кожен маршрут, помилки 401, 404, 409, 422."""

import csv
import io

import pytest
from fastapi.testclient import TestClient

from kinograf.api import create_app
from kinograf.config import Settings
from kinograf.opendata import WikidataLoader
from kinograf.services import Services, SparqlBusyError, SparqlTimeoutError

ADMIN = {"X-Admin-Key": "secret"}


@pytest.fixture
def services(filled_database, rdf_store, fake_client) -> Services:
    settings = Settings(
        database_path=str(filled_database.path),
        graph_path=str(rdf_store.path),
        admin_key="secret",
    )
    return Services.create(settings, WikidataLoader(fake_client, 1991))


@pytest.fixture
def client(services) -> TestClient:
    return TestClient(create_app(services))


def test_films_first_page(client):
    response = client.get("/api/films")
    assert response.status_code == 200
    body = response.json()
    assert (body["total"], body["page"], len(body["items"])) == (7, 1, 7)
    assert body["items"][0]["directors"] == [
        {
            "qid": "Q12",
            "name": "Валентин Васянович",
            "wikidata_url": "https://www.wikidata.org/wiki/Q12",
        }
    ]
    assert body["items"][0]["genres"] == [{"qid": "Q130232", "name": "драма"}]
    assert body["items"][0]["film"] == {
        "qid": "Q6",
        "title": "Відблиск",
        "release_date": "2021-09-01",
        "year": 2021,
        "duration_min": 127,
        "image_url": None,
        "wikidata_url": "https://www.wikidata.org/wiki/Q6",
    }


def test_films_with_text_filters_and_sort(client):
    response = client.get(
        "/api/films",
        params={"period": "2014-now", "genre": "Q130232", "has_cast": "true", "sort": "title"},
    )
    assert [item["film"]["title"] for item in response.json()["items"]] == [
        "Атлантида",
        "Відблиск",
        "Плем'я",
    ]
    response = client.get("/api/films", params={"q": "поводир", "year_from": 2010, "year_to": 2015})
    assert [item["film"]["qid"] for item in response.json()["items"]] == ["Q4"]
    response = client.get("/api/films", params={"director": "Q12", "page": 2})
    assert response.json() == {"items": [], "total": 2, "page": 2}


@pytest.mark.parametrize(
    "params",
    [{"sort": "rating"}, {"page": 0}, {"period": "2000-2010"}, {"year_from": "давно"}],
)
def test_films_reject_invalid_parameters(client, params):
    assert client.get("/api/films", params=params).status_code == 422


def test_film_details(client):
    body = client.get("/api/films/Q4").json()
    assert body["film"]["title"] == "Поводир"
    assert list(body["participants"]) == ["director", "screenwriter", "composer", "cast"]
    assert body["participants"]["director"][0]["name"] == "Олесь Санін"
    assert body["participants"]["cast"] == []
    assert [genre["name"] for genre in body["genres"]] == ["драма", "історичний фільм"]
    assert body["related"][0]["film"]["qid"] == "Q3"
    assert body["related"][0]["shared_people"] == 2


def test_person_profile(client):
    body = client.get("/api/people/Q11").json()
    assert body["person"]["wikidata_url"] == "https://www.wikidata.org/wiki/Q11"
    assert body["filmography"][0]["roles"] == ["director", "screenwriter"]
    assert body["collaborators"][0] == {
        "person": {
            "qid": "Q14",
            "name": "Алла Загайкевич",
            "wikidata_url": "https://www.wikidata.org/wiki/Q14",
        },
        "films": 2,
    }


@pytest.mark.parametrize("path", ["/api/films/Q999", "/api/people/Q999", "/api/graph/Q999"])
def test_unknown_entities_return_404(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert "не знайдено" in response.json()["detail"]


def test_graph(client):
    body = client.get("/api/graph/Q12", params={"depth": 2}).json()
    assert {node["id"] for node in body["nodes"]} == {"Q12", "Q5", "Q6", "Q13"}
    assert {"from": "Q5", "to": "Q12", "roles": ["director", "screenwriter"]} in body["edges"]
    assert len(client.get("/api/graph/Q12").json()["nodes"]) == 3
    assert client.get("/api/graph/Q12", params={"depth": 3}).status_code == 422


def test_filter_lists(client):
    assert [genre["name"] for genre in client.get("/api/genres").json()] == [
        "документальний фільм",
        "драма",
        "історичний фільм",
    ]
    assert client.get("/api/directors").json()[0]["name"] == "Валентин Васянович"


def test_stats(client):
    body = client.get("/api/stats").json()
    assert body["totals"] == {"films": 7, "people": 7}
    assert body["films_by_year"]["2014"] == 2
    assert body["genres_by_period"]["1991-2013"] == {"драма": 1, "історичний фільм": 1}
    assert body["top_directors"][0]["person"]["qid"] == "Q12"
    assert body["top_actors"][0]["films"] == 2
    assert set(body["completeness"]) == {"director", "cast", "genre", "poster"}
    assert body["completeness_by_year"]["2014"]["cast"] == 0.5
    assert body["last_updated"] is None


def test_sparql(client):
    response = client.post(
        "/api/sparql",
        json={"query": "SELECT ?title WHERE { ?film wdt:P57 wd:Q11 ; rdfs:label ?title }"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["columns"] == ["title"]
    assert sorted(row["title"] for row in body["rows"]) == ["Мамай", "Поводир"]
    assert body["truncated"] is False
    assert body["elapsed_ms"] >= 0


@pytest.mark.parametrize(
    ("query", "message"),
    [
        ("ASK { ?s ?p ?o }", "лише запити SELECT"),
        ("SELECT ?x WHERE {", "синтаксична помилка"),
        ("SELECT * WHERE { SERVICE <http://example.org/> { ?s ?p ?o } }", "зовнішніх"),
    ],
)
def test_sparql_errors_return_400(client, query, message):
    response = client.post("/api/sparql", json={"query": query})
    assert response.status_code == 400
    assert message in response.json()["detail"]


def test_sparql_timeout_returns_408(client, services, monkeypatch):
    def slow(query):
        raise SparqlTimeoutError("запит виконувався довше 10 с")

    monkeypatch.setattr(services.sparql, "execute", slow)
    response = client.post("/api/sparql", json={"query": "SELECT * WHERE { ?s ?p ?o }"})
    assert response.status_code == 408
    assert "10 с" in response.json()["detail"]


def test_export_films_csv(client):
    response = client.get("/api/export/films", params={"format": "csv", "director": "Q12"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == 'attachment; filename="films.csv"'
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert [row["qid"] for row in rows] == ["Q6", "Q5"]


def test_export_films_json_and_turtle(client):
    films = client.get("/api/export/films", params={"format": "json"}).json()
    assert len(films) == 7
    response = client.get("/api/export/films", params={"format": "ttl", "q": "плем'я"})
    assert response.headers["content-type"] == "text/turtle; charset=utf-8"
    assert "Плем'я" in response.text


def test_export_films_rejects_unknown_format(client):
    assert client.get("/api/export/films", params={"format": "xml"}).status_code == 422
    assert client.get("/api/export/films").status_code == 422


def test_export_sparql(client):
    response = client.post(
        "/api/export/sparql",
        json={"query": "SELECT ?film WHERE { ?film wdt:P166 ?award }", "format": "json"},
    )
    assert response.headers["content-disposition"] == 'attachment; filename="sparql.json"'
    assert len(response.json()) == 2
    bad = client.post("/api/export/sparql", json={"query": "ASK {}", "format": "csv"})
    assert bad.status_code == 400
    assert client.post("/api/export/sparql", json={"query": "", "format": "xml"}).status_code == 422


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/api/admin/log"), ("post", "/api/admin/update"), ("get", "/api/admin/update/1")],
)
@pytest.mark.parametrize("headers", [{}, {"X-Admin-Key": "wrong"}, {"X-Admin-Key": ""}])
def test_admin_routes_require_key(client, method, path, headers):
    response = client.request(method, path, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "неправильний ключ адміністратора"


def test_admin_disabled_without_configured_key(filled_database, rdf_store):
    settings = Settings(database_path=str(filled_database.path), graph_path=str(rdf_store.path))
    client = TestClient(create_app(Services.create(settings)))
    assert client.get("/api/admin/log", headers={"X-Admin-Key": ""}).status_code == 401


def test_admin_update_runs_in_background_and_is_logged(client):
    assert client.get("/api/admin/log", headers=ADMIN).json() == []
    response = client.post("/api/admin/update", headers=ADMIN)
    assert response.status_code == 202
    started = response.json()
    assert (started["status"], started["finished_at"]) == ("running", None)
    progress = client.get(f"/api/admin/update/{started['id']}", headers=ADMIN).json()
    assert (progress["status"], progress["stage"]) == ("success", "storage")
    assert (progress["films_added"], progress["films_changed"]) == (0, 0)
    assert [log["id"] for log in client.get("/api/admin/log", headers=ADMIN).json()] == [1]
    assert client.get("/api/films").json()["total"] == 2
    assert client.get("/api/stats").json()["last_updated"] == progress["finished_at"]


def test_admin_update_conflict_while_running(client, services):
    services.update.start()
    response = client.post("/api/admin/update", headers=ADMIN)
    assert response.status_code == 409
    assert response.json()["detail"] == "оновлення вже виконується"


def test_admin_update_status_of_unknown_log(client):
    assert client.get("/api/admin/update/999", headers=ADMIN).status_code == 404


def test_openapi_documentation(client):
    assert client.get("/api/docs").status_code == 200
    paths = client.get("/api/openapi.json").json()["paths"]
    assert "/api/films" in paths
    assert "/api/admin/update/{log_id}" in paths


def test_create_app_reads_settings_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("KINOGRAF_DATABASE_PATH", str(tmp_path / "env.db"))
    monkeypatch.setenv("KINOGRAF_GRAPH_PATH", str(tmp_path / "env.ttl"))
    client = TestClient(create_app())
    assert client.get("/api/films").json() == {"items": [], "total": 0, "page": 1}
    assert (tmp_path / "env.db").exists()


@pytest.mark.parametrize(
    "params",
    [
        {"year_from": 10**20},
        {"year_to": 99999},
        {"page": 10**18},
        {"q": "ж" * 201},
        {"genre": "Q" * 40},
    ],
)
def test_out_of_range_parameters_are_rejected(client, params):
    assert client.get("/api/films", params=params).status_code == 422


def test_export_rejects_out_of_range_year(client):
    response = client.get("/api/export/films", params={"format": "csv", "year_to": 10**20})
    assert response.status_code == 422


def test_sparql_query_size_is_limited(client):
    response = client.post("/api/sparql", json={"query": "#" * 20_001})
    assert response.status_code == 422


def test_sparql_busy_returns_429(client, services, monkeypatch):
    def busy(query):
        raise SparqlBusyError("консоль зайнята")

    monkeypatch.setattr(services.sparql, "execute", busy)
    response = client.post("/api/sparql", json={"query": "SELECT * WHERE { ?s ?p ?o }"})
    assert response.status_code == 429
    assert response.headers["retry-after"] == "5"


def test_non_ascii_admin_key_is_rejected_not_crashing(client):
    response = client.get("/api/admin/log", headers={"X-Admin-Key": "clé".encode("latin-1")})
    assert response.status_code == 401
