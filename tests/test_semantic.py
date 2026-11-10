"""Memoria semántica: recordar por significado con embeddings (simulados)."""

import asyncio

import pytest

from ai.providers.ollama import OllamaProvider
from ai.service import AIService
from core.memory import MemoryStore
from core.persona import Persona
from core.semantic import SemanticMemory
from tests.fakes import FakeClient, FakeEmbedder

PERSONA = Persona(id="p", name="P", prompt="Eres P.", lines={"error": ["E"], "empty_reply": ["V"]})


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(params=[True, False], ids=["sqlite-vec", "python"])
def store(request, tmp_path):
    store = MemoryStore(tmp_path / "meka.db")
    if request.param and not store.vec:
        pytest.skip("sqlite-vec no instalado")
    store.vec = request.param and store.vec
    return store


def test_finds_memories_by_meaning(store):
    memory = SemanticMemory(store, FakeEmbedder(), query_prefix="Q: ", document_prefix="D: ")
    store.add_fact(1, "mi perro se llama Toby")
    store.add_fact(1, "mi color favorito es el azul")
    store.add_fact(2, "a mi gato le gusta el sushi")  # Otro usuario: nunca aparece

    hits = run(memory.search(1, "¿qué te conté de mi mascota?"))
    assert hits[0][0] == "mi perro se llama Toby" and hits[0][1] > 0.9
    assert all(fact != "a mi gato le gusta el sushi" for fact, _ in hits)
    # Prefijos de embeddinggemma: documento al indexar y pregunta al buscar
    assert memory.embedder.calls[0][0].startswith("D: ")
    assert memory.embedder.calls[-1] == ["Q: ¿qué te conté de mi mascota?"]


def test_vectors_are_computed_once_and_follow_new_facts(store):
    embedder = FakeEmbedder()
    memory = SemanticMemory(store, embedder)
    store.add_fact(1, "mi perro se llama Toby")
    run(memory.search(1, "mascota"))
    run(memory.search(1, "mascota"))
    indexed = [call for call in embedder.calls if call != ["mascota"]]
    assert indexed == [["mi perro se llama Toby"]]

    store.add_fact(1, "me encanta el ramen")
    assert run(memory.search(1, "comida"))[0][0] == "me encanta el ramen"


def test_changing_the_model_reindexes(tmp_path):
    store = MemoryStore(tmp_path / "meka.db")
    store.add_fact(1, "mi perro se llama Toby")
    run(SemanticMemory(store, FakeEmbedder()).index(1))
    other = FakeEmbedder()
    other.model = "otro-modelo"
    assert run(SemanticMemory(store, other).index(1)) == 1


def test_deleted_facts_lose_their_vectors(tmp_path):
    store = MemoryStore(tmp_path / "meka.db")
    store.add_fact(1, "mi perro se llama Toby")
    memory = SemanticMemory(store, FakeEmbedder())
    run(memory.index(1))
    store.clear(1)
    assert store.db.execute("SELECT COUNT(*) FROM fact_vectors").fetchone()[0] == 0


def test_without_facts_or_ollama_it_degrades_quietly(tmp_path):
    store = MemoryStore(tmp_path / "meka.db")
    embedder = FakeEmbedder(fail=True)
    memory = SemanticMemory(store, embedder)
    assert run(memory.search(1, "mascota")) == [] and embedder.calls == []  # Sin recuerdos
    store.add_fact(1, "mi perro se llama Toby")
    assert run(memory.search(1, "mascota")) == []  # Ollama caído: vacío, sin excepción


def make_service(tmp_path, client, embedder, **semantic):
    store = MemoryStore(tmp_path / "meka.db")
    return AIService(
        config={"memory": {"semantic": semantic}},
        memory=store,
        persona=PERSONA,
        providers={"ollama": OllamaProvider({}, client=client)},
        semantic=SemanticMemory(store, embedder),
    )


def test_recall_by_meaning_reaches_the_prompt(tmp_path):
    client = FakeClient("Anotado", "¡Toby!")
    service = make_service(tmp_path, client, FakeEmbedder())
    run(service.generate_response(1, 1, "Recuerda esto: mi perro se llama Toby"))
    # Ni "perro" ni "Toby" en la pregunta: solo el significado la conecta
    run(service.generate_response(1, 1, "¿Te acuerdas de mi mascota?"))
    assert "mi perro se llama Toby" in client.calls[1]["messages"][0]["content"]


def test_auto_recall_only_for_close_memories(tmp_path):
    client = FakeClient("ok", "ok", "ok")
    service = make_service(tmp_path, client, FakeEmbedder(), auto_recall_similarity=0.8)
    service.memory.add_fact(1, "mi perro se llama Toby")
    run(service.generate_response(1, 1, "hoy saqué a pasear a mi perro"))  # Sin "¿recuerdas?"
    run(service.generate_response(1, 1, "quiero cenar algo rico"))
    assert "Toby" in client.calls[0]["messages"][0]["content"]
    assert "Toby" not in client.calls[1]["messages"][0]["content"]


def test_keyword_search_still_works_when_embeddings_fail(tmp_path):
    client = FakeClient("ok")
    service = make_service(tmp_path, client, FakeEmbedder(fail=True))
    service.memory.add_fact(1, "mi color favorito es el azul")
    run(service.generate_response(1, 1, "¿Te acuerdas de mi color favorito?"))
    assert "azul" in client.calls[0]["messages"][0]["content"]
