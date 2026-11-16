"""Тести сховищ персоналій, статистики й журналу оновлень."""

import pytest

from kinograf.models import Person, Role
from kinograf.repositories import LogRepository, PersonRepository, StatsRepository
from tests import sample_data


@pytest.fixture
def people(filled_database) -> PersonRepository:
    return PersonRepository(filled_database)


@pytest.fixture
def stats(filled_database) -> StatsRepository:
    return StatsRepository(filled_database)


@pytest.fixture
def logs(database) -> LogRepository:
    return LogRepository(database)


def test_get_person(people):
    assert people.get("Q11") == Person("Q11", "Олесь Санін")
    assert people.get("Q999") is None


def test_filmography_newest_first_with_every_role(people):
    entries = [(film.qid, role) for film, role in people.filmography("Q11")]
    assert entries == [
        ("Q4", Role.DIRECTOR),
        ("Q4", Role.SCREENWRITER),
        ("Q3", Role.DIRECTOR),
        ("Q3", Role.SCREENWRITER),
    ]


def test_filmography_of_unknown_person_is_empty(people):
    assert people.filmography("Q999") == []


def test_collaborators_count_shared_films(people):
    assert people.collaborators("Q11") == [(Person("Q14", "Алла Загайкевич"), 2)]
    assert people.collaborators("Q10") == [(Person("Q16", "Яна Новікова"), 1)]


def test_collaborators_respect_limit(people):
    assert len(people.collaborators("Q12", limit=1)) == 1
    assert people.collaborators("Q15") == []


def test_participants_grouped_by_every_role(people):
    participants = people.participants("Q1")
    assert participants == {
        Role.DIRECTOR: [Person("Q10", "Мирослав Слабошпицький")],
        Role.SCREENWRITER: [Person("Q10", "Мирослав Слабошпицький")],
        Role.COMPOSER: [],
        Role.CAST: [Person("Q16", "Яна Новікова")],
    }


def test_directors_by_film_for_several_films(people):
    directors = people.directors_by_film(["Q1", "Q3", "Q7"])
    assert directors["Q1"] == [Person("Q10", "Мирослав Слабошпицький")]
    assert directors["Q3"] == [Person("Q11", "Олесь Санін")]
    assert directors["Q7"] == []


def test_directors_sorted_by_name(people):
    assert [person.qid for person in people.directors()] == ["Q12", "Q15", "Q10", "Q11"]


def test_replace_all_replaces_people_and_participations(people):
    people.replace_all([Person("Q10", "М. Слабошпицький")], sample_data.PARTICIPATIONS[:1])
    assert people.get("Q10").name == "М. Слабошпицький"
    assert people.get("Q11") is None
    assert people.participants("Q4")[Role.DIRECTOR] == []


def test_totals(stats):
    assert stats.totals() == {"films": 7, "people": 7}


def test_films_by_year(stats):
    assert stats.films_by_year() == {1995: 1, 2003: 1, 2014: 2, 2019: 1, 2020: 1, 2021: 1}


def test_genres_by_period(stats):
    assert stats.genres_by_period() == {
        "1991-2013": {"драма": 1, "історичний фільм": 1},
        "2014-now": {"драма": 4, "документальний фільм": 1, "історичний фільм": 1},
    }


def test_top_people_by_role(stats):
    top = stats.top_people(Role.DIRECTOR, limit=3)
    assert [(person.qid, films) for person, films in top] == [("Q12", 2), ("Q11", 2), ("Q15", 1)]
    cast = stats.top_people(Role.CAST)
    assert [(person.qid, films) for person, films in cast] == [("Q13", 2), ("Q16", 1)]


def test_completeness(stats):
    assert stats.completeness() == pytest.approx(
        {"director": 6 / 7, "cast": 3 / 7, "genre": 6 / 7, "poster": 2 / 7}
    )


def test_completeness_by_year(stats):
    by_year = stats.completeness_by_year()
    assert list(by_year) == [1995, 2003, 2014, 2019, 2020, 2021]
    assert by_year[2014] == {"director": 1.0, "cast": 0.5, "genre": 1.0, "poster": 1.0}
    assert by_year[1995] == {"director": 0.0, "cast": 0.0, "genre": 0.0, "poster": 0.0}


def test_completeness_of_empty_database(database):
    stats = StatsRepository(database)
    assert stats.completeness() == {"director": 0.0, "cast": 0.0, "genre": 0.0, "poster": 0.0}
    assert stats.completeness_by_year() == {}
    assert stats.films_by_year() == {}
    assert stats.totals() == {"films": 0, "people": 0}


def test_log_start_creates_running_record(logs):
    log = logs.start()
    assert log.id == 1
    assert log.status == "running"
    assert logs.get(1) == log


def test_log_stage_and_finish_are_saved(logs):
    log = logs.start()
    logs.set_stage(log, "genres")
    assert logs.get(log.id).stage == "genres"
    log.status, log.films_added, log.films_changed = "success", 5, 2
    logs.finish(log)
    saved = logs.get(log.id)
    assert saved == log
    assert saved.finished_at >= saved.started_at


def test_log_get_unknown_returns_none(logs):
    assert logs.get(42) is None


def test_log_recent_newest_first_and_last_success(logs):
    assert logs.last_success() is None
    first, second, third = logs.start(), logs.start(), logs.start()
    for log, status in ((first, "success"), (second, "success"), (third, "error")):
        log.status = status
        logs.finish(log)
    assert [log.id for log in logs.recent()] == [3, 2, 1]
    assert [log.id for log in logs.recent(limit=2)] == [3, 2]
    assert logs.last_success().id == second.id
