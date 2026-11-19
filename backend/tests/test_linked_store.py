"""Тести опублікованого графа: словник schema.org, зв'язки, документи сутностей, VoID, JSON-LD."""

from datetime import UTC, datetime

import pytest
from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import DCTERMS, FOAF, VOID

from kinograf.rdf import SCHEMA, WD, LinkedDataStore, SparqlError

BASE = "http://kino.test"
FILM = URIRef(f"{BASE}/id/film/Q4")
PERSON = URIRef(f"{BASE}/id/person/Q11")


def test_film_uses_schema_org_vocabulary(linked_store):
    graph = linked_store.graph()
    assert (FILM, RDF.type, SCHEMA.Movie) in graph
    assert (FILM, SCHEMA.name, Literal("Поводир", lang="uk")) in graph
    assert (FILM, SCHEMA.datePublished, Literal("2014-11-13", datatype=XSD.date)) in graph
    assert (FILM, SCHEMA.duration, Literal("PT122M", datatype=XSD.duration)) in graph
    assert (
        FILM,
        SCHEMA.image,
        URIRef("http://commons.wikimedia.org/wiki/Special:FilePath/Povodyr.jpg"),
    ) in graph
    assert (FILM, SCHEMA.countryOfOrigin, WD.Q212) in graph
    assert (FILM, SCHEMA.url, URIRef(f"{BASE}/films/Q4")) in graph
    assert (FILM, SCHEMA.genre, WD.Q130232) in graph
    assert (WD.Q130232, RDFS.label, Literal("драма", lang="uk")) in graph


def test_roles_and_awards(linked_store):
    graph = linked_store.graph()
    assert (FILM, SCHEMA.director, PERSON) in graph
    assert (FILM, SCHEMA.author, PERSON) in graph
    assert (FILM, SCHEMA.musicBy, URIRef(f"{BASE}/id/person/Q14")) in graph
    atlantis = URIRef(f"{BASE}/id/film/Q5")
    assert (atlantis, SCHEMA.actor, URIRef(f"{BASE}/id/person/Q13")) in graph
    awards = {str(value) for value in graph.objects(atlantis, SCHEMA.award)}
    assert awards == {"Венеційський кінофестиваль — найкращий фільм програми «Горизонти»"}


def test_person_has_type_name_and_page(linked_store):
    graph = linked_store.graph()
    assert (PERSON, RDF.type, SCHEMA.Person) in graph
    assert (PERSON, SCHEMA.name, Literal("Олесь Санін", lang="uk")) in graph
    assert (PERSON, SCHEMA.url, URIRef(f"{BASE}/people/Q11")) in graph


def test_links_to_other_datasets(linked_store):
    graph = linked_store.graph()
    tribe = URIRef(f"{BASE}/id/film/Q1")
    assert set(graph.objects(tribe, OWL.sameAs)) == {
        WD.Q1,
        URIRef("http://dbpedia.org/resource/The_Tribe_(2014_film)"),
    }
    assert set(graph.objects(tribe, SCHEMA.sameAs)) == {
        URIRef("https://www.imdb.com/title/tt3904770/"),
        URIRef(
            "https://uk.wikipedia.org/wiki/%D0%9F%D0%BB%D0%B5%D0%BC'%D1%8F_(%D1%84%D1%96%D0%BB%D1%8C%D0%BC)"
        ),
    }
    assert URIRef("https://www.imdb.com/name/nm1125213/") in set(
        graph.objects(PERSON, SCHEMA.sameAs)
    )
    assert set(graph.objects(URIRef(f"{BASE}/id/film/Q7"), OWL.sameAs)) == {WD.Q7}


def test_publish_saves_file_that_load_restores(linked_store, tmp_path):
    restored = LinkedDataStore(tmp_path / "linked.ttl", BASE)
    restored.load()
    assert len(restored) == len(linked_store) > 0


def test_contains(linked_store):
    assert linked_store.contains("film", "Q4")
    assert linked_store.contains("person", "Q11")
    assert not linked_store.contains("film", "Q11")
    assert not linked_store.contains("film", "Q999")
    assert not linked_store.contains("genre", "Q130232")


def test_film_document(linked_store):
    document = linked_store.describe("film", "Q4")
    doc = URIRef(f"{BASE}/data/film/Q4")
    assert (doc, FOAF.primaryTopic, FILM) in document
    assert (
        doc,
        DCTERMS.license,
        URIRef("https://creativecommons.org/publicdomain/zero/1.0/"),
    ) in document
    assert (doc, VOID.inDataset, URIRef(f"{BASE}/.well-known/void#dataset")) in document
    assert (FILM, SCHEMA.director, PERSON) in document
    assert (PERSON, SCHEMA.name, Literal("Олесь Санін", lang="uk")) in document
    assert (WD.Q130232, RDFS.label, Literal("драма", lang="uk")) in document
    assert not any(document.triples((URIRef(f"{BASE}/id/film/Q5"), None, None)))


def test_person_document_includes_films(linked_store):
    document = linked_store.describe("person", "Q11")
    assert (PERSON, SCHEMA.name, Literal("Олесь Санін", lang="uk")) in document
    for qid, title in (("Q3", "Мамай"), ("Q4", "Поводир")):
        film = URIRef(f"{BASE}/id/film/{qid}")
        assert (film, SCHEMA.director, PERSON) in document
        assert (film, SCHEMA.name, Literal(title, lang="uk")) in document


def test_void_description(linked_store):
    modified = datetime(2026, 10, 30, 21, 38, tzinfo=UTC)
    void = linked_store.void(modified)
    dataset = URIRef(f"{BASE}/.well-known/void#dataset")
    assert (dataset, RDF.type, VOID.Dataset) in void
    assert (dataset, DCTERMS.title, Literal("КіноГраф", lang="uk")) in void
    assert (
        dataset,
        DCTERMS.license,
        URIRef("https://creativecommons.org/publicdomain/zero/1.0/"),
    ) in void
    assert (dataset, DCTERMS.source, URIRef("https://www.wikidata.org/")) in void
    assert void.value(dataset, DCTERMS.modified).toPython() == modified
    assert (dataset, VOID.sparqlEndpoint, URIRef(f"{BASE}/data/sparql")) in void
    assert (dataset, VOID.dataDump, URIRef(f"{BASE}/data/kinograf.ttl")) in void
    assert (dataset, VOID.uriSpace, Literal(f"{BASE}/id/")) in void
    assert void.value(dataset, VOID.triples).toPython() == len(linked_store)
    assert void.value(dataset, VOID.entities).toPython() == 14
    assert void.value(dataset, VOID.exampleResource) is not None
    vocabularies = set(void.objects(dataset, VOID.vocabulary))
    assert URIRef("https://schema.org/") in vocabularies
    partitions = {
        void.value(part, VOID["class"]): void.value(part, VOID.entities).toPython()
        for part in void.objects(dataset, VOID.classPartition)
    }
    assert partitions == {SCHEMA.Movie: 7, SCHEMA.Person: 7}


def test_void_linksets(linked_store):
    void = linked_store.void()
    dataset = URIRef(f"{BASE}/.well-known/void#dataset")
    linksets = {
        str(void.value(void.value(subset, VOID.objectsTarget), DCTERMS.title)): (
            void.value(subset, VOID.linkPredicate),
            void.value(subset, VOID.triples).toPython(),
        )
        for subset in void.objects(dataset, VOID.subset)
        if (subset, RDF.type, VOID.Linkset) in void
    }
    assert linksets == {
        "Wikidata": (OWL.sameAs, 14),
        "Вікіпедія (укр.)": (SCHEMA.sameAs, 3),
        "IMDb": (SCHEMA.sameAs, 3),
        "DBpedia": (OWL.sameAs, 2),
    }


def test_linkset_counts(linked_store):
    counts = [
        (item.target, item.predicate, item.films, item.people)
        for item in linked_store.linkset_counts()
    ]
    assert counts == [
        ("Wikidata", "owl:sameAs", 7, 7),
        ("Вікіпедія (укр.)", "schema:sameAs", 2, 1),
        ("IMDb", "schema:sameAs", 2, 1),
        ("DBpedia", "owl:sameAs", 1, 1),
    ]


@pytest.mark.parametrize("kind,qid", [("film", "Q4"), ("person", "Q11")])
def test_jsonld_parses_back_to_same_graph(linked_store, kind, qid):
    document = linked_store.describe(kind, qid)
    data = LinkedDataStore.serialize(document, "jsonld")
    assert b'"@vocab": "https://schema.org/"' in data
    assert isomorphic(Graph().parse(data=data, format="json-ld"), document)


def test_turtle_parses_back_to_same_graph(linked_store):
    document = linked_store.void()
    data = LinkedDataStore.serialize(document, "ttl")
    assert b"@prefix void:" in data
    assert isomorphic(Graph().parse(data=data, format="turtle"), document)


def test_serialize_refuses_unknown_format(linked_store):
    with pytest.raises(ValueError, match="xml"):
        LinkedDataStore.serialize(linked_store.graph(), "xml")


def test_query_allows_select_and_ask_only(linked_store):
    result = linked_store.query("SELECT ?film WHERE { ?film a schema:Movie ; schema:director ?d }")
    assert len(result.rows) == 6
    assert linked_store.query("ASK { ?film a schema:Movie }").boolean is True
    with pytest.raises(SparqlError, match="SELECT і ASK"):
        linked_store.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    with pytest.raises(SparqlError, match="зовнішніх"):
        linked_store.query("SELECT * WHERE { SERVICE <http://example.org/> { ?s ?p ?o } }")
