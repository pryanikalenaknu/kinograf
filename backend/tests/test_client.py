"""Тести клієнта Wikidata: розбір відповіді й повторні спроби."""

from email.message import Message
from urllib.error import HTTPError

import pytest

from kinograf.opendata import WikidataClient, WikidataError
from kinograf.opendata.client import retry_after

RESPONSE = {
    "results": {
        "bindings": [
            {
                "film": {"type": "uri", "value": "http://www.wikidata.org/entity/Q1"},
                "filmLabel": {"type": "literal", "value": "Плем'я"},
            },
            {"film": {"type": "uri", "value": "http://www.wikidata.org/entity/Q2"}},
        ]
    }
}


class ScriptedClient(WikidataClient):
    """Клієнт, що замість мережевого виклику відтворює заданий сценарій відповідей."""

    def __init__(self, outcomes, **kwargs):
        super().__init__("https://example.org/sparql", "test-agent", **kwargs)
        self.outcomes = list(outcomes)
        self.calls = 0

    def _execute(self, query):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_run_flattens_bindings_to_values():
    client = ScriptedClient([RESPONSE])
    rows = client.run("SELECT * WHERE {}")
    assert rows == [
        {"film": "http://www.wikidata.org/entity/Q1", "filmLabel": "Плем'я"},
        {"film": "http://www.wikidata.org/entity/Q2"},
    ]


def test_run_retries_after_failure_with_growing_delay():
    pauses = []
    client = ScriptedClient(
        [TimeoutError(), ConnectionError(), RESPONSE],
        max_attempts=3,
        retry_delay=2,
        sleep=pauses.append,
    )
    rows = client.run("SELECT * WHERE {}")
    assert len(rows) == 2
    assert client.calls == 3
    assert pauses == [2, 4]


def test_run_raises_after_all_attempts_fail():
    client = ScriptedClient([TimeoutError()] * 3, max_attempts=3, sleep=lambda _: None)
    with pytest.raises(WikidataError, match="3 спроби"):
        client.run("SELECT * WHERE {}")
    assert client.calls == 3


def rate_limited(retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError("https://example.org/sparql", 429, "Too Many Requests", headers, None)


def test_default_delay_respects_one_request_per_minute():
    pauses = []
    client = ScriptedClient([rate_limited(), rate_limited(), RESPONSE], sleep=pauses.append)
    assert len(client.run("SELECT * WHERE {}")) == 2
    assert pauses == [60, 120]


def test_retry_after_header_extends_pause():
    pauses = []
    client = ScriptedClient([rate_limited("90"), RESPONSE], retry_delay=60, sleep=pauses.append)
    client.run("SELECT * WHERE {}")
    assert pauses == [90]


def test_shorter_retry_after_keeps_own_delay():
    pauses = []
    client = ScriptedClient([rate_limited("5"), RESPONSE], retry_delay=60, sleep=pauses.append)
    client.run("SELECT * WHERE {}")
    assert pauses == [60]


@pytest.mark.parametrize(
    "error",
    [
        rate_limited(),
        rate_limited("Wed, 21 Oct 2026 07:28:00 GMT"),
        TimeoutError(),
    ],
)
def test_retry_after_without_seconds_is_ignored(error):
    assert retry_after(error) == 0


def test_request_is_plain_post_form_with_content_negotiation():
    client = WikidataClient("https://query.example.org/sparql", "KinoGraf/test")
    request = client.prepare("ASK { ?s ?p ?o }")._createRequest()
    assert request.get_method() == "POST"
    assert request.full_url == "https://query.example.org/sparql"
    assert request.data == b"query=ASK+%7B+%3Fs+%3Fp+%3Fo+%7D"
    headers = dict(request.header_items())
    assert headers["Content-type"] == "application/x-www-form-urlencoded"
    assert headers["Accept"].startswith("application/sparql-results+json")
    assert headers["User-agent"] == "KinoGraf/test"
