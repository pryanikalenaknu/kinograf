"""Опублікований граф КіноГраф: зв'язані відкриті дані у словнику schema.org з власними URI."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, VOID

from kinograf.models import Award, ExternalLinks, Film, Genre, Participation, Person, Role
from kinograf.rdf.base import GraphStore
from kinograf.rdf.store import WD

SCHEMA = Namespace("https://schema.org/")
CC0 = URIRef("https://creativecommons.org/publicdomain/zero/1.0/")
LANGUAGE = "uk"

KINDS = {"film": SCHEMA.Movie, "person": SCHEMA.Person}

ROLE_PROPERTIES = {
    Role.DIRECTOR: SCHEMA.director,
    Role.SCREENWRITER: SCHEMA.author,
    Role.COMPOSER: SCHEMA.musicBy,
    Role.CAST: SCHEMA.actor,
}

JSONLD_CONTEXT = {
    "@vocab": str(SCHEMA),
    "owl": str(OWL),
    "dcterms": str(DCTERMS),
    "foaf": str(FOAF),
    "void": str(VOID),
}

FORMATS = {"ttl": "turtle", "jsonld": "json-ld"}


@dataclass
class LinkTarget:
    """Набір даних, з яким пов'язано КіноГраф.

    Attributes:
        key: Короткий ідентифікатор набору в адресах VoID.
        target: Назва набору для людей.
        homepage: Головна сторінка набору.
        predicate: Властивість зв'язку.
        prefix: Початок адрес сутностей цього набору.
    """

    key: str
    target: str
    homepage: str
    predicate: URIRef
    prefix: str


LINK_TARGETS = [
    LinkTarget("wikidata", "Wikidata", "https://www.wikidata.org/", OWL.sameAs, str(WD)),
    LinkTarget(
        "ukwiki",
        "Вікіпедія (укр.)",
        "https://uk.wikipedia.org/",
        SCHEMA.sameAs,
        "https://uk.wikipedia.org/wiki/",
    ),
    LinkTarget("imdb", "IMDb", "https://www.imdb.com/", SCHEMA.sameAs, "https://www.imdb.com/"),
    LinkTarget(
        "dbpedia", "DBpedia", "https://dbpedia.org/", OWL.sameAs, "http://dbpedia.org/resource/"
    ),
]


@dataclass
class Linkset:
    """Скільки фільмів і персоналій КіноГраф мають відповідник в іншому наборі.

    Attributes:
        target: Назва набору.
        homepage: Головна сторінка набору.
        predicate: Властивість зв'язку в скороченому записі, наприклад ``owl:sameAs``.
        films: Кількість фільмів із посиланням.
        people: Кількість персоналій із посиланням.
    """

    target: str
    homepage: str
    predicate: str
    films: int
    people: int


class LinkedDataStore(GraphStore):
    """Будує й зберігає опублікований граф ``linked.ttl`` та описує його у VoID.

    Args:
        path: Шлях до файлу ``linked.ttl``.
        base_url: Базова адреса застосунку, від якої будуються URI сутностей.
        timeout: Найбільший час виконання SPARQL-запиту в секундах.
        max_rows: Найбільша кількість рядків результату запиту.
        max_concurrent: Найбільша кількість SPARQL-запитів, що виконуються одночасно.
    """

    NAMESPACES = {
        "schema": SCHEMA,
        "owl": OWL,
        "dcterms": DCTERMS,
        "foaf": FOAF,
        "void": VOID,
        "rdfs": RDFS,
        "xsd": XSD,
        "wd": WD,
    }
    QUERY_FORMS = {"SelectQuery": "SELECT", "AskQuery": "ASK"}

    def __init__(
        self,
        path: str | Path,
        base_url: str,
        timeout: float = 10.0,
        max_rows: int = 1000,
        max_concurrent: int = 2,
    ) -> None:
        super().__init__(path, timeout, max_rows, max_concurrent)
        self.base_url = base_url.rstrip("/")

    def uri(self, kind: str, qid: str) -> URIRef:
        """Повертає постійну адресу сутності.

        Args:
            kind: Вид сутності: ``film`` або ``person``.
            qid: Ідентифікатор у Wikidata.

        Returns:
            URI вигляду ``{base}/id/{kind}/{qid}``.
        """
        return URIRef(f"{self.base_url}/id/{kind}/{qid}")

    def publish(
        self,
        films: list[Film],
        people: list[Person],
        participations: list[Participation],
        genres: dict[str, list[Genre]],
        awards: dict[str, list[Award]],
        links: dict[str, ExternalLinks],
    ) -> None:
        """Будує опублікований граф з даних каталогу й зберігає його у файл.

        Args:
            films: Фільми.
            people: Персоналії.
            participations: Участь персоналій у фільмах.
            genres: Жанри за ідентифікаторами фільмів.
            awards: Нагороди за ідентифікаторами фільмів.
            links: Посилання на інші набори за ідентифікаторами сутностей.
        """
        graph = self._empty_graph()
        for film in films:
            node = self.uri("film", film.qid)
            graph.add((node, RDF.type, SCHEMA.Movie))
            graph.add((node, SCHEMA.name, Literal(film.title, lang=LANGUAGE)))
            graph.add((node, SCHEMA.datePublished, Literal(film.release_date, datatype=XSD.date)))
            if film.duration_min is not None:
                duration = Literal(f"PT{film.duration_min}M", datatype=XSD.duration)
                graph.add((node, SCHEMA.duration, duration))
            if film.image_url:
                graph.add((node, SCHEMA.image, URIRef(film.image_url)))
            graph.add((node, SCHEMA.countryOfOrigin, WD.Q212))
            graph.add((node, SCHEMA.url, URIRef(f"{self.base_url}/films/{film.qid}")))
            for genre in genres.get(film.qid, []):
                graph.add((node, SCHEMA.genre, WD[genre.qid]))
                graph.add((WD[genre.qid], RDFS.label, Literal(genre.name, lang=LANGUAGE)))
            for award in awards.get(film.qid, []):
                graph.add((node, SCHEMA.award, Literal(award.name, lang=LANGUAGE)))
            self._add_links(graph, node, film.qid, links.get(film.qid))
        for person in people:
            node = self.uri("person", person.qid)
            graph.add((node, RDF.type, SCHEMA.Person))
            graph.add((node, SCHEMA.name, Literal(person.name, lang=LANGUAGE)))
            graph.add((node, SCHEMA.url, URIRef(f"{self.base_url}/people/{person.qid}")))
            self._add_links(graph, node, person.qid, links.get(person.qid))
        for item in participations:
            graph.add(
                (
                    self.uri("film", item.film_qid),
                    ROLE_PROPERTIES[item.role],
                    self.uri("person", item.person_qid),
                )
            )
        self._replace(graph)

    def contains(self, kind: str, qid: str) -> bool:
        """Перевіряє, чи є сутність в опублікованому наборі.

        Args:
            kind: Вид сутності: ``film`` або ``person``.
            qid: Ідентифікатор у Wikidata.

        Returns:
            ``True``, якщо сутність опубліковано.
        """
        cls = KINDS.get(kind)
        return cls is not None and (self.uri(kind, qid), RDF.type, cls) in self.graph()

    def describe(self, kind: str, qid: str) -> Graph:
        """Будує документ про сутність.

        Документ містить трійки, де сутність є підметом, назви сутностей, на які вона
        посилається, для персоналії — фільми з її участю та їхні назви, а також трійки
        про сам документ: ``foaf:primaryTopic``, ліцензію й ``void:inDataset``.

        Args:
            kind: Вид сутності: ``film`` або ``person``.
            qid: Ідентифікатор у Wikidata.

        Returns:
            Граф документа.
        """
        graph = self.graph()
        node = self.uri(kind, qid)
        document = self._empty_graph()
        for _, prop, value in graph.triples((node, None, None)):
            document.add((node, prop, value))
            self._add_names(graph, document, value)
        if kind == "person":
            for film, prop, _ in graph.triples((None, None, node)):
                document.add((film, prop, node))
                self._add_names(graph, document, film)
        doc = URIRef(f"{self.base_url}/data/{kind}/{qid}")
        document.add((doc, FOAF.primaryTopic, node))
        document.add((doc, DCTERMS.license, CC0))
        document.add((doc, VOID.inDataset, self._dataset()))
        return document

    def void(self, modified: datetime | None = None) -> Graph:
        """Будує опис набору у словнику VoID.

        Args:
            modified: Час останнього успішного оновлення.

        Returns:
            Граф опису набору з наборами зв'язків.
        """
        graph = self.graph()
        dataset = self._dataset()
        description = self._empty_graph()
        add = description.add
        add((dataset, RDF.type, VOID.Dataset))
        add((dataset, DCTERMS.title, Literal("КіноГраф", lang=LANGUAGE)))
        add(
            (
                dataset,
                DCTERMS.description,
                Literal(
                    "Українські фільми від 1991 року та їхні творці за відкритими даними Wikidata",
                    lang=LANGUAGE,
                ),
            )
        )
        add((dataset, DCTERMS.license, CC0))
        add((dataset, DCTERMS.source, URIRef("https://www.wikidata.org/")))
        if modified is not None:
            add((dataset, DCTERMS.modified, Literal(modified, datatype=XSD.dateTime)))
        add((dataset, FOAF.homepage, URIRef(f"{self.base_url}/")))
        add((dataset, VOID.uriSpace, Literal(f"{self.base_url}/id/")))
        add((dataset, VOID.sparqlEndpoint, URIRef(f"{self.base_url}/data/sparql")))
        add((dataset, VOID.dataDump, URIRef(f"{self.base_url}/data/kinograf.ttl")))
        example = self.example_film()
        if example is not None:
            add((dataset, VOID.exampleResource, self.uri("film", example)))
        for vocabulary in (SCHEMA, OWL, DCTERMS):
            add((dataset, VOID.vocabulary, URIRef(str(vocabulary))))
        add((dataset, VOID.triples, Literal(len(graph))))
        counts = {KINDS[kind]: entities for kind, entities in self.entity_counts().items()}
        add((dataset, VOID.entities, Literal(sum(counts.values()))))
        for cls, entities in counts.items():
            partition = BNode()
            add((dataset, VOID.classPartition, partition))
            add((partition, VOID["class"], cls))
            add((partition, VOID.entities, Literal(entities)))
        for target, linkset in zip(LINK_TARGETS, self.linkset_counts(), strict=True):
            node = URIRef(f"{self.base_url}/.well-known/void#{target.key}")
            other = URIRef(f"{self.base_url}/.well-known/void#{target.key}-dataset")
            add((dataset, VOID.subset, node))
            add((node, RDF.type, VOID.Linkset))
            add((node, VOID.subjectsTarget, dataset))
            add((node, VOID.objectsTarget, other))
            add((node, VOID.linkPredicate, target.predicate))
            add((node, VOID.triples, Literal(linkset.films + linkset.people)))
            add((other, RDF.type, VOID.Dataset))
            add((other, DCTERMS.title, Literal(target.target)))
            add((other, FOAF.homepage, URIRef(target.homepage)))
        return description

    def entity_counts(self) -> dict[str, int]:
        """Рахує опубліковані сутності кожного виду.

        Returns:
            Кількість фільмів (``film``) і персоналій (``person``).
        """
        graph = self.graph()
        return {kind: len(set(graph.subjects(RDF.type, cls))) for kind, cls in KINDS.items()}

    def example_film(self) -> str | None:
        """Обирає фільм для прикладів: перший за адресою серед фільмів із режисером.

        Returns:
            Ідентифікатор фільму або ``None``, якщо набір порожній.
        """
        graph = self.graph()
        films = sorted(graph.subjects(RDF.type, SCHEMA.Movie))
        directed = [film for film in films if (film, SCHEMA.director, None) in graph]
        chosen = (directed or films or [None])[0]
        return None if chosen is None else str(chosen).rsplit("/", 1)[-1]

    def linkset_counts(self) -> list[Linkset]:
        """Рахує, скільки фільмів і персоналій мають посилання на кожен набір.

        Returns:
            Набори зв'язків у порядку Wikidata, Вікіпедія, IMDb, DBpedia.
        """
        graph = self.graph()
        result = []
        for target in LINK_TARGETS:
            counts = {"film": 0, "person": 0}
            for kind, cls in KINDS.items():
                for subject in graph.subjects(RDF.type, cls):
                    if any(
                        str(value).startswith(target.prefix)
                        for value in graph.objects(subject, target.predicate)
                    ):
                        counts[kind] += 1
            predicate = "owl:sameAs" if target.predicate == OWL.sameAs else "schema:sameAs"
            result.append(
                Linkset(target.target, target.homepage, predicate, counts["film"], counts["person"])
            )
        return result

    @staticmethod
    def serialize(graph: Graph, fmt: str) -> bytes:
        """Серіалізує граф у Turtle або JSON-LD з контекстом schema.org.

        Args:
            graph: Граф.
            fmt: Формат: ``ttl`` або ``jsonld``.

        Returns:
            Вміст документа в UTF-8.

        Raises:
            ValueError: Якщо формат не підтримується.
        """
        if fmt not in FORMATS:
            raise ValueError(f"непідтримуваний формат: {fmt}")
        if fmt == "jsonld":
            data = graph.serialize(format="json-ld", context=JSONLD_CONTEXT, auto_compact=True)
            return json.dumps(json.loads(data), ensure_ascii=False, indent=2).encode()
        return graph.serialize(format="turtle").encode()

    def _dataset(self) -> URIRef:
        """Повертає URI опису набору."""
        return URIRef(f"{self.base_url}/.well-known/void#dataset")

    def _add_links(self, graph: Graph, node: URIRef, qid: str, links: ExternalLinks | None) -> None:
        """Додає зв'язки сутності з Wikidata, DBpedia, IMDb і Вікіпедією."""
        graph.add((node, OWL.sameAs, WD[qid]))
        if links is None:
            return
        if links.dbpedia_uri:
            graph.add((node, OWL.sameAs, URIRef(links.dbpedia_uri)))
        if links.imdb_url:
            graph.add((node, SCHEMA.sameAs, URIRef(links.imdb_url)))
        if links.ukwiki_url:
            graph.add((node, SCHEMA.sameAs, URIRef(links.ukwiki_url)))

    @staticmethod
    def _add_names(source: Graph, target: Graph, node: object) -> None:
        """Копіює назви (``schema:name``, ``rdfs:label``) сутності в документ."""
        for prop in (SCHEMA.name, RDFS.label):
            for name in source.objects(node, prop):
                target.add((node, prop, name))
