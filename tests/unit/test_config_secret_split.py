import json

import solax_configure as cfg


def test_save_public_config_excludes_secret_keys(tmp_path, monkeypatch):
    public_file = tmp_path / "solax.json"
    secrets_file = tmp_path / "solax_secrets.json"

    monkeypatch.setattr(cfg, "local_file", str(public_file), raising=False)
    monkeypatch.setattr(cfg, "local_secrets_file", str(secrets_file), raising=False)

    cfg.save_public_config({
        "solax_stats_folder": "C:/data/solax",
        "auth_mode": "auto",
        "api_token": "must-not-be-public",
    })

    public_json = json.loads(public_file.read_text(encoding="utf8"))
    assert public_json["solax_stats_folder"] == "C:/data/solax"
    assert public_json["auth_mode"] == "auto"
    assert "api_token" not in public_json


def test_save_secret_config_keeps_only_secret_keys(tmp_path, monkeypatch):
    public_file = tmp_path / "solax.json"
    secrets_file = tmp_path / "solax_secrets.json"

    monkeypatch.setattr(cfg, "local_file", str(public_file), raising=False)
    monkeypatch.setattr(cfg, "local_secrets_file", str(secrets_file), raising=False)

    cfg.save_secret_config({
        "user_name": "user@example.com",
        "site_password": "pass",
        "api_token": "tok",
        "solax_stats_folder": "must-not-be-secret",
    })

    secret_json = json.loads(secrets_file.read_text(encoding="utf8"))
    assert secret_json["user_name"] == "user@example.com"
    assert secret_json["site_password"] == "pass"
    assert secret_json["api_token"] == "tok"
    assert "solax_stats_folder" not in secret_json


def test_migrate_secrets_from_public_moves_sensitive_keys(tmp_path):
    public_file = tmp_path / "solax.json"
    secrets_file = tmp_path / "solax_secrets.json"

    public_file.write_text(
        json.dumps({
            "solax_stats_folder": "C:/data/solax",
            "api_token": "tok",
            "encrypted_password": "enc",
        }),
        encoding="utf8",
    )

    moved = cfg.migrate_secrets_from_public(str(public_file), str(secrets_file))

    assert moved["api_token"] == "tok"
    assert moved["encrypted_password"] == "enc"

    public_json = json.loads(public_file.read_text(encoding="utf8"))
    assert "api_token" not in public_json
    assert "encrypted_password" not in public_json

    secret_json = json.loads(secrets_file.read_text(encoding="utf8"))
    assert secret_json["api_token"] == "tok"
    assert secret_json["encrypted_password"] == "enc"


