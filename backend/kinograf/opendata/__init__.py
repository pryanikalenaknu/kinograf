"""Модуль роботи з відкритими даними Wikidata."""

from kinograf.opendata.client import WikidataClient, WikidataError
from kinograf.opendata.loader import LoadedParticipations, WikidataLoader

__all__ = ["LoadedParticipations", "WikidataClient", "WikidataError", "WikidataLoader"]
