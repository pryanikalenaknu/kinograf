"""Перевірка модуля відкритих даних: завантажує дані з Wikidata й виводить підсумок.

Запуск: ``python -m kinograf.opendata``.
"""

from collections import Counter

from kinograf.config import load_settings
from kinograf.models import Role
from kinograf.opendata import WikidataClient, WikidataLoader


def main() -> None:
    """Завантажує всі групи даних і друкує кількісні показники повноти."""
    settings = load_settings()
    client = WikidataClient(
        settings.sparql_endpoint, settings.user_agent, retry_delay=settings.retry_delay
    )
    loader = WikidataLoader(client, settings.min_year)

    films = loader.fetch_films()
    loaded = loader.fetch_participations()
    genres = loader.fetch_genres()
    awards = loader.fetch_awards()

    total = len(films)
    films_by_role = {
        role: {p.film_qid for p in loaded.participations if p.role is role} for role in Role
    }
    roles = Counter(p.role for p in loaded.participations)

    print(f"фільмів від {settings.min_year} року: {total}")
    for role in Role:
        covered = len(films_by_role[role])
        share = covered / total
        print(f"  з роллю {role.value:<13} {covered:5d} ({share:.0%}), записів: {roles[role]}")
    print(f"  з жанром               {len(genres):5d} ({len(genres) / total:.0%})")
    print(f"  з нагородами           {len(awards):5d} ({len(awards) / total:.0%})")
    with_poster = sum(1 for film in films if film.image_url)
    print(f"  із зображенням         {with_poster:5d} ({with_poster / total:.0%})")
    print(f"персоналій: {len(loaded.people)}")
    print("приклад:", films[-1].title, films[-1].year)


if __name__ == "__main__":
    main()
