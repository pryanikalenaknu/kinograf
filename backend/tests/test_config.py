"""Тести читання налаштувань зі змінних середовища."""

from kinograf.config import Settings, load_settings


def test_defaults_without_environment(monkeypatch):
    for name in (
        "KINOGRAF_MIN_YEAR",
        "KINOGRAF_ADMIN_KEY",
        "KINOGRAF_SPARQL_ENDPOINT",
        "KINOGRAF_RETRY_DELAY",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = load_settings()
    assert settings == Settings()
    assert settings.min_year == 1991
    assert settings.retry_delay == 60


def test_environment_overrides_defaults(monkeypatch):
    monkeypatch.setenv("KINOGRAF_MIN_YEAR", "2014")
    monkeypatch.setenv("KINOGRAF_ADMIN_KEY", "secret")
    monkeypatch.setenv("KINOGRAF_RETRY_DELAY", "90")
    settings = load_settings()
    assert settings.retry_delay == 90
    assert settings.min_year == 2014
    assert settings.admin_key == "secret"
