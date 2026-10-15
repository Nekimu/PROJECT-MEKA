import pytest

from core.config import BASE_DIR, is_valid_token, load_config, parse_user_ids, resolve_path


def test_parse_user_ids_keeps_order_and_skips_invalid():
    assert parse_user_ids(" 123, abc,456,123 ,") == [123, 456]
    assert parse_user_ids([1, "2"]) == [1, 2]
    assert parse_user_ids(None) == []


def test_resolve_path_is_relative_to_project_root(tmp_path):
    assert resolve_path("audio/x.wav") == BASE_DIR / "audio" / "x.wav"
    assert resolve_path(tmp_path) == tmp_path


def test_is_valid_token():
    assert is_valid_token("123:abc")
    assert not is_valid_token("tu_token_aqui_sin_comillas")
    assert not is_valid_token(None)


def test_load_config_overrides_secrets_from_env(tmp_path, monkeypatch):
    path = tmp_path / "config.yml"
    path.write_text("telegram:\n  request_timeout: 10\n", encoding="utf-8")
    monkeypatch.setenv("TELEGRAM_TOKEN", " 999:XYZ ")
    monkeypatch.setenv("ALLOWED_USER_IDS", "1,2")

    config = load_config(path)
    assert config["telegram"] == {
        "request_timeout": 10,
        "token": "999:XYZ",
        "allowed_user_ids": [1, 2],
    }


def test_load_config_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "no-existe.yml")


def test_repository_config_is_valid():
    config = load_config()
    assert config["tts"]["engine"] in {"qwen-tts", "edge-tts", "piper"}
    assert isinstance(config["media"]["stickers"], list)
