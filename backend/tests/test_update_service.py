"""Тести сервісу оновлення даних і команди ``python -m kinograf.update``."""

from dataclasses import replace

import pytest

from kinograf import update
from kinograf.config import Settings
from kinograf.opendata import WikidataError, WikidataLoader
from kinograf.rdf import LinkedDataStore, RdfStore, ShaclValidator
from kinograf.repositories import (
    FilmRepository,
    LinkRepository,
    LogRepository,
    PersonRepository,
    QualityRepository,
)
from kinograf.services import Services, UpdateInProgressError, UpdateService


class FailingClient:
    """Клієнт, що відповідає як підставний, але не виконує запити з даним фрагментом."""

    def __init__(self, client, marker):
        self.client = client
        self.marker = marker

    def run(self, query):
        if self.marker in query:
            raise WikidataError("запит не виконано за 3 спроби: timeout")
        return self.client.run(query)


def make_service(database, tmp_path, client):
    return UpdateService(
        WikidataLoader(client, 1991),
        database,
        FilmRepository(database),
        PersonRepository(database),
        LinkRepository(database),
        LogRepository(database),
        RdfStore(tmp_path / "graph.ttl"),
        LinkedDataStore(tmp_path / "linked.ttl", "http://kino.test"),
        QualityRepository(database),
        ShaclValidator(tmp_path / "shacl-report.ttl"),
    )


def test_run_loads_data_into_database_and_graph(database, tmp_path, fake_client):
    service = make_service(database, tmp_path, fake_client)
    log = service.run(service.start())
    assert (log.status, log.films_added, log.films_changed) == ("success", 2, 0)
    assert log.stage == "validation"
    assert log.finished_at is not None
    assert LogRepository(database).get(log.id) == log
    assert FilmRepository(database).get("Q1").title == "Плем'я"
    assert PersonRepository(database).get("Q20").name == "Ірина Цілик"
    assert [genre.name for genre in FilmRepository(database).genres_of("Q2")] == [
        "документальний фільм"
    ]
    graph = RdfStore(tmp_path / "graph.ttl")
    graph.load()
    assert graph.entities(["Q1", "Q10"]) == {
        "Q1": ("film", "Плем'я"),
        "Q10": ("person", "Мирослав Слабошпицький"),
    }


def test_repeated_run_counts_no_changes(database, tmp_path, fake_client):
    service = make_service(database, tmp_path, fake_client)
    service.run(service.start())
    log = service.run(service.start())
    assert (log.films_added, log.films_changed) == (0, 0)


def test_wikidata_error_sets_error_status_and_keeps_data(database, tmp_path, fake_client):
    loaded = make_service(database, tmp_path, fake_client)
    loaded.run(loaded.start())
    service = make_service(database, tmp_path, FailingClient(fake_client, "?personLabel"))
    log = service.run(service.start())
    assert log.status == "error"
    assert log.stage == "participations"
    assert "3 спроби" in log.message
    assert LogRepository(database).get(log.id).status == "error"
    assert FilmRepository(database).get("Q1") is not None
    assert not service.running


def test_storage_error_rolls_back_database(database, tmp_path, fake_client, monkeypatch):
    service = make_service(database, tmp_path, fake_client)

    def broken_rebuild(*args):
        raise OSError("диск заповнено")

    monkeypatch.setattr(RdfStore, "rebuild", broken_rebuild)
    log = service.run(service.start())
    assert (log.status, log.stage, log.message) == ("error", "storage", "диск заповнено")
    assert FilmRepository(database).get("Q1") is None


def test_second_update_cannot_start_while_first_runs(database, tmp_path, fake_client):
    service = make_service(database, tmp_path, fake_client)
    log = service.start()
    assert service.running
    with pytest.raises(UpdateInProgressError):
        service.start()
    service.run(log)
    assert not service.running
    service.run(service.start())


def test_start_releases_lock_when_log_cannot_be_created(database, tmp_path, fake_client):
    service = make_service(database, tmp_path, fake_client)
    service._logs = None
    with pytest.raises(AttributeError):
        service.start()
    assert not service.running


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        database_path=str(tmp_path / "data" / "kinograf.db"),
        graph_path=str(tmp_path / "data" / "graph.ttl"),
        linked_path=str(tmp_path / "data" / "linked.ttl"),
        report_path=str(tmp_path / "data" / "shacl-report.ttl"),
        admin_key="secret",
    )


def test_command_prints_summary(settings, fake_client, capsys):
    services = Services.create(settings, WikidataLoader(fake_client, 1991))
    assert update.main(services) == 0
    assert "додано 2, змінено 0" in capsys.readouterr().out


def test_command_reports_error(settings, fake_client, capsys):
    loader = WikidataLoader(FailingClient(fake_client, "?genreLabel"), 1991)
    assert update.main(Services.create(settings, loader)) == 1
    assert "етапі «genres»" in capsys.readouterr().out


def test_services_create_default_loader_from_settings(settings):
    services = Services.create(replace(settings, min_year=2014, retry_delay=75))
    assert services.update._loader.min_year == 2014
    assert services.update._loader.client.endpoint == settings.sparql_endpoint
    assert services.update._loader.client.retry_delay == 75


def test_history_and_log_read_journal(database, tmp_path, fake_client):
    service = make_service(database, tmp_path, fake_client)
    first = service.run(service.start())
    second = service.run(service.start())
    assert [log.id for log in service.history()] == [second.id, first.id]
    assert service.log(first.id) == first
    assert service.log(999) is None


def locked_service(database, tmp_path, client):
    service = make_service(database, tmp_path, client)
    service._lock_path = tmp_path / "update.lock"
    return service


def test_update_cannot_start_in_another_process_at_the_same_time(database, tmp_path, fake_client):
    api = locked_service(database, tmp_path, fake_client)
    command = locked_service(database, tmp_path, fake_client)
    log = api.start()
    with pytest.raises(UpdateInProgressError):
        command.start()
    api.run(log)
    command.run(command.start())


def test_lock_is_released_when_journal_cannot_be_written(database, tmp_path, fake_client):
    service = locked_service(database, tmp_path, fake_client)
    log = service.start()
    service._logs.finish = lambda log: (_ for _ in ()).throw(OSError("database is locked"))
    with pytest.raises(OSError):
        service.run(log)
    assert not service.running
    other = locked_service(database, tmp_path, fake_client)
    other.run(other.start())


def test_recover_interrupted_closes_running_records(database, tmp_path, fake_client):
    logs = LogRepository(database)
    stale = logs.start()
    service = locked_service(database, tmp_path, fake_client)
    assert service.recover_interrupted() == 1
    recovered = logs.get(stale.id)
    assert recovered.status == "error"
    assert "перервано" in recovered.message
    assert recovered.finished_at is not None
    assert service.recover_interrupted() == 0


def test_recover_interrupted_skips_running_update(database, tmp_path, fake_client):
    running = locked_service(database, tmp_path, fake_client)
    log = running.start()
    assert locked_service(database, tmp_path, fake_client).recover_interrupted() == 0
    assert LogRepository(database).get(log.id).status == "running"
    running.run(log)


def test_services_close_records_left_by_crash(settings, fake_client):
    crashed = Services.create(settings, WikidataLoader(fake_client, 1991))
    crashed.update._logs.start()
    services = Services.create(settings, WikidataLoader(fake_client, 1991))
    assert services.update.history()[0].status == "error"


def test_run_stores_links_and_imdb_in_graph(database, tmp_path, fake_client):
    service = make_service(database, tmp_path, fake_client)
    stages = []
    service._logs.set_stage = lambda log, stage: stages.append(stage)
    service.run(service.start())
    assert stages == [
        "films",
        "participations",
        "genres",
        "awards",
        "links",
        "storage",
        "publication",
        "validation",
    ]
    links = LinkRepository(database)
    assert links.get("Q1").imdb_id == "tt3904770"
    assert links.get("Q10").ukwiki == "Мирослав Слабошпицький"
    graph = RdfStore(tmp_path / "graph.ttl")
    graph.load()
    rows = graph.query("SELECT ?film ?imdb WHERE { ?film wdt:P345 ?imdb }").rows
    assert {row["imdb"] for row in rows} == {"tt3904770", "nm5752123"}
