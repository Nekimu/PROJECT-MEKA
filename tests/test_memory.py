import json

from core.memory import MemorySystem, extract_keywords, normalize_text


def test_normalize_text_removes_accents_and_punctuation():
    assert normalize_text("¿Recuérdas mi color FAVORITO?").split() == [
        "recuerdas",
        "mi",
        "color",
        "favorito",
    ]


def test_extract_keywords_skips_stopwords_and_short_words():
    assert extract_keywords("¿Te acuerdas de mi color favorito?") == ["color", "favorito"]


def test_facts_are_isolated_per_user(tmp_path):
    memory = MemorySystem(tmp_path / "memory.json")
    assert memory.add_fact(1, "mi color favorito es el azul")
    assert not memory.add_fact(1, "mi color favorito es el azul")  # duplicado
    memory.add_fact(2, "mi contraseña del wifi es secreta")

    assert memory.get_facts(1) == ["mi color favorito es el azul"]
    assert memory.search(2, "¿recuerdas mi color favorito?") == [
        "mi contraseña del wifi es secreta"
    ]
    assert "azul" not in " ".join(memory.search(2, "color favorito"))


def test_search_ranks_by_keyword_matches(tmp_path):
    memory = MemorySystem(tmp_path / "memory.json")
    memory.add_fact(1, "mi perro se llama Toby")
    memory.add_fact(1, "mi color favorito es el azul")
    memory.add_fact(1, "el color de mi coche es rojo")
    assert memory.search(1, "¿recuerdas mi color favorito?")[0] == "mi color favorito es el azul"


def test_persistence_and_clear(tmp_path):
    path = tmp_path / "memory.json"
    MemorySystem(path).add_fact(7, "me gusta el ramen")
    reloaded = MemorySystem(path)
    assert reloaded.get_facts(7) == ["me gusta el ramen"]
    assert reloaded.clear(7) == 1
    assert MemorySystem(path).get_facts(7) == []


def test_legacy_format_is_migrated_to_owner(tmp_path):
    path = tmp_path / "memory.json"
    path.write_text(json.dumps({"facts": ["dato antiguo"]}), encoding="utf-8")
    memory = MemorySystem(path, legacy_owner_id=42)
    assert memory.get_facts(42) == ["dato antiguo"]
    assert "facts" not in json.loads(path.read_text(encoding="utf-8"))


def test_legacy_format_without_owner_is_kept_but_not_served(tmp_path):
    path = tmp_path / "memory.json"
    path.write_text(json.dumps({"facts": ["dato antiguo"]}), encoding="utf-8")
    memory = MemorySystem(path)
    assert memory.get_facts(1) == []
    assert memory.data["legacy_facts"] == ["dato antiguo"]


def test_corrupt_file_is_backed_up(tmp_path):
    path = tmp_path / "memory.json"
    path.write_text("{no es json", encoding="utf-8")
    memory = MemorySystem(path)
    assert memory.get_facts(1) == []
    assert list(tmp_path.glob("memory.json.corrupt-*"))
