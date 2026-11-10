import json

from core.memory import MemoryStore, extract_keywords, normalize_text


def test_normalize_text_removes_accents_and_punctuation():
    assert normalize_text("¿Recuérdas MI canción?").split() == ["recuerdas", "mi", "cancion"]


def test_extract_keywords_skips_stopwords_and_short_words():
    assert extract_keywords("¿Te acuerdas de mi color favorito?") == ["color", "favorito"]


def test_facts_are_isolated_per_user(tmp_path):
    memory = MemoryStore(tmp_path / "meka.db")
    assert memory.add_fact(1, "mi color favorito es el azul")
    assert not memory.add_fact(1, "mi color favorito es el azul")  # duplicado
    memory.add_fact(2, "mi contraseña del wifi es secreta")

    assert memory.get_facts(1) == ["mi color favorito es el azul"]
    assert memory.search(2, "¿recuerdas mi color favorito?") == [
        "mi contraseña del wifi es secreta"
    ]
    assert "azul" not in " ".join(memory.search(2, "color favorito"))


def test_search_ranks_by_keyword_matches(tmp_path):
    memory = MemoryStore(tmp_path / "meka.db")
    memory.add_fact(1, "mi perro se llama Toby")
    memory.add_fact(1, "mi color favorito es el azul")
    memory.add_fact(1, "el color de mi coche es rojo")
    assert memory.search(1, "¿recuerdas mi color favorito?")[0] == "mi color favorito es el azul"


def test_search_ignores_accents_and_matches_prefixes(tmp_path):
    memory = MemoryStore(tmp_path / "meka.db")
    memory.add_fact(1, "Mi canción favorita es de Ado")
    memory.add_fact(1, "Juego Overwatch los viernes")
    assert memory.search(1, "¿recuerdas mi cancion?") == ["Mi canción favorita es de Ado"]
    assert memory.search(1, "¿te acuerdas de los juegos?") == ["Juego Overwatch los viernes"]


def test_simple_search_without_fts(tmp_path):
    memory = MemoryStore(tmp_path / "meka.db")
    memory.fts = False
    memory.add_fact(1, "mi perro se llama Toby")
    memory.add_fact(1, "mi color favorito es el azul")
    assert memory.search(1, "color favorito") == ["mi color favorito es el azul"]


def test_persistence_and_clear(tmp_path):
    path = tmp_path / "meka.db"
    MemoryStore(path).add_fact(7, "me gusta el ramen")
    reloaded = MemoryStore(path)
    assert reloaded.get_facts(7) == ["me gusta el ramen"]
    assert reloaded.clear(7) == 1
    assert MemoryStore(path).get_facts(7) == []


def test_history_is_kept_per_session_and_pruned(tmp_path):
    memory = MemoryStore(tmp_path / "meka.db")
    for i in range(3):
        memory.add_messages("a", [("user", f"hola {i}"), ("assistant", f"respuesta {i}")])
    memory.add_messages("b", [("user", "otro chat"), ("assistant", "vale")])
    memory.prune_messages("a", 4)
    assert [m["content"] for m in memory.recent_messages("a", 10)] == [
        "hola 1", "respuesta 1", "hola 2", "respuesta 2",
    ]  # fmt: skip
    assert memory.clear_messages("a") == 4
    assert len(memory.recent_messages("b", 10)) == 2


def test_json_memory_is_migrated_once(tmp_path):
    legacy = tmp_path / "memory.json"
    legacy.write_text(
        json.dumps({"users": {"1": ["me gusta el ramen"]}, "facts": ["dato antiguo"]}),
        encoding="utf-8",
    )
    memory = MemoryStore(tmp_path / "meka.db", legacy_json=legacy, legacy_owner=42)
    assert memory.get_facts(1) == ["me gusta el ramen"]
    assert memory.get_facts(42) == ["dato antiguo"]
    assert not legacy.exists() and (tmp_path / "memory.json.migrated").exists()


def test_json_without_owner_is_not_migrated(tmp_path):
    legacy = tmp_path / "memory.json"
    legacy.write_text(json.dumps({"facts": ["dato antiguo"]}), encoding="utf-8")
    memory = MemoryStore(tmp_path / "meka.db", legacy_json=legacy)
    assert memory.get_facts("None") == []
    assert legacy.exists()  # Se espera a que haya ALLOWED_USER_IDS


def test_corrupt_json_is_left_alone(tmp_path):
    legacy = tmp_path / "memory.json"
    legacy.write_text("{no es json", encoding="utf-8")
    MemoryStore(tmp_path / "meka.db", legacy_json=legacy)
    assert legacy.exists()
