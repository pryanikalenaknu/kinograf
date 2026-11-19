"""Створення й зв'язування сервісів застосунку за налаштуваннями."""

from dataclasses import dataclass
from pathlib import Path

from kinograf.config import Settings
from kinograf.opendata import WikidataClient, WikidataLoader
from kinograf.rdf import LinkedDataStore, RdfStore, ShaclValidator
from kinograf.repositories import (
    Database,
    FilmRepository,
    LinkRepository,
    LogRepository,
    PersonRepository,
    QualityRepository,
    StatsRepository,
)
from kinograf.services.catalog import CatalogService
from kinograf.services.export import ExportService
from kinograf.services.film import FilmService
from kinograf.services.graph import GraphService
from kinograf.services.linkeddata import LinkedDataService
from kinograf.services.person import PersonService
from kinograf.services.quality import QualityService
from kinograf.services.sparql import SparqlService
from kinograf.services.stats import StatsService
from kinograf.services.update import UpdateService


@dataclass
class Services:
    """Набір сервісів, що працюють з одним сховищем.

    Attributes:
        settings: Налаштування застосунку.
        catalog: Каталог фільмів.
        films: Картка фільму.
        people: Сторінка персоналії.
        stats: Статистика й якість даних.
        graph: Граф зв'язків.
        sparql: SPARQL-консоль.
        export: Експорт результатів.
        linked: Опубліковані зв'язані дані.
        quality: Перевірка якості за правилами SHACL.
        update: Оновлення даних і журнал.
    """

    settings: Settings
    catalog: CatalogService
    films: FilmService
    people: PersonService
    stats: StatsService
    graph: GraphService
    sparql: SparqlService
    export: ExportService
    linked: LinkedDataService
    quality: QualityService
    update: UpdateService

    @classmethod
    def create(cls, settings: Settings, loader: WikidataLoader | None = None) -> "Services":
        """Відкриває сховище, завантажує RDF-граф і створює сервіси.

        Записи журналу, що лишилися незавершеними після аварійної зупинки, закриваються.

        Args:
            settings: Налаштування застосунку.
            loader: Завантажувач Wikidata; за замовчуванням створюється за налаштуваннями.

        Returns:
            Готові до роботи сервіси.
        """
        database = Database(settings.database_path)
        database.create_schema()
        rdf = RdfStore(settings.graph_path)
        rdf.load()
        linked = LinkedDataStore(settings.linked_path, settings.base_url)
        linked.load()
        if loader is None:
            client = WikidataClient(
                settings.sparql_endpoint, settings.user_agent, retry_delay=settings.retry_delay
            )
            loader = WikidataLoader(client, settings.min_year)
        films = FilmRepository(database)
        people = PersonRepository(database)
        logs = LogRepository(database)
        links = LinkRepository(database)
        stats = StatsRepository(database)
        quality = QualityRepository(database)
        validator = ShaclValidator(settings.report_path)
        services = cls(
            settings=settings,
            catalog=CatalogService(films, people),
            films=FilmService(films, people, links, settings.base_url),
            people=PersonService(people, links, settings.base_url),
            stats=StatsService(stats, logs),
            graph=GraphService(rdf),
            sparql=SparqlService(rdf),
            export=ExportService(films, rdf),
            linked=LinkedDataService(linked, logs),
            quality=QualityService(validator, quality, stats, logs),
            update=UpdateService(
                loader,
                database,
                films,
                people,
                links,
                logs,
                rdf,
                linked,
                quality,
                validator,
                lock_path=Path(settings.database_path).with_name("update.lock"),
            ),
        )
        services.update.recover_interrupted()
        return services
