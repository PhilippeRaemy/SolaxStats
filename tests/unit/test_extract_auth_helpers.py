import pytest

import solax_extract as extract


def test_first_non_empty_returns_first_value():
    assert extract.first_non_empty(None, "", "x", "y") == "x"


def test_resolve_session_token_in_token_mode(monkeypatch):
    monkeypatch.setattr(extract.cfg, "auth_mode", "token", raising=False)
    monkeypatch.setattr(extract.cfg, "api_token", "abc-token", raising=False)

    session, token = extract.resolve_session_token(proxies={})

    assert token == "abc-token"
    assert session is not None


def test_resolve_session_token_token_mode_requires_token(monkeypatch):
    monkeypatch.setattr(extract.cfg, "auth_mode", "token", raising=False)
    monkeypatch.setattr(extract.cfg, "api_token", None, raising=False)

    with pytest.raises(Exception) as ex:
        extract.resolve_session_token(proxies={})

    assert "requires --api-token" in str(ex.value)


def test_resolve_session_token_legacy_login_uses_username_and_password(monkeypatch):
    monkeypatch.setattr(extract.cfg, "auth_mode", "legacy_encrypted", raising=False)
    monkeypatch.setattr(extract.cfg, "user_name", "u", raising=False)
    monkeypatch.setattr(extract.cfg, "encrypted_password", "enc", raising=False)

    def fake_login(url, proxies, user_name, encrypted_password):
        assert "phoebus/login/loginNew" in url
        assert user_name == "u"
        assert encrypted_password == "enc"
        return object(), {"token": "tok-1"}

    monkeypatch.setattr(extract, "login", fake_login)

    session, token = extract.resolve_session_token(proxies={})
    assert token == "tok-1"
    assert session is not None


def test_resolve_session_token_legacy_raises_on_missing_token(monkeypatch):
    monkeypatch.setattr(extract.cfg, "auth_mode", "legacy_encrypted", raising=False)
    monkeypatch.setattr(extract.cfg, "user_name", "u", raising=False)
    monkeypatch.setattr(extract.cfg, "encrypted_password", "enc", raising=False)

    monkeypatch.setattr(extract, "login", lambda *args, **kwargs: (object(), {"success": True}))

    with pytest.raises(Exception) as ex:
        extract.resolve_session_token(proxies={})

    assert "No token returned" in str(ex.value)


def test_resolve_session_token_browser_auto_uses_browser_helper(monkeypatch):
    monkeypatch.setattr(extract.cfg, "auth_mode", "browser_auto", raising=False)
    monkeypatch.setattr(extract.cfg, "user_name", "u", raising=False)
    monkeypatch.setattr(extract.cfg, "site_password", "p", raising=False)

    def fake_browser_token(**kwargs):
        assert kwargs["user_name"] == "u"
        assert kwargs["site_password"] == "p"
        return "browser-token"

    monkeypatch.setattr(extract, "get_api_token_via_browser", fake_browser_token)

    session, token = extract.resolve_session_token(proxies={})
    assert token == "browser-token"
    assert session is not None


def test_resolve_session_token_auto_uses_saved_token_when_valid(monkeypatch):
    monkeypatch.setattr(extract.cfg, "auth_mode", "auto", raising=False)
    monkeypatch.setattr(extract.cfg, "api_token", "saved-token", raising=False)
    monkeypatch.setattr(extract, "token_works_for_daily_data", lambda *args, **kwargs: True)

    session, token = extract.resolve_session_token(proxies={})
    assert token == "saved-token"
    assert session is not None


def test_token_auto_saves_config_when_requested(monkeypatch):
    monkeypatch.setattr(extract.cfg, "user_name", "u", raising=False)
    monkeypatch.setattr(extract.cfg, "site_password", "p", raising=False)
    monkeypatch.setattr(
        extract,
        "get_auth_artifacts_via_browser",
        lambda **kwargs: {"token": "tok-env", "encrypted_password": "enc-from-browser"}
    )

    captured = {"token": None, "encrypted_password": None}
    monkeypatch.setattr(
        extract,
        "save_auth_to_config",
        lambda token=None, encrypted_password=None: captured.update(
            {"token": token, "encrypted_password": encrypted_password}
        )
    )

    extract.token_auto.callback(
        user_name=None,
        site_password=None,
        login_url=None,
        headless=True,
        timeout_seconds=10,
        debug_login=False,
        save_config=True,
    )

    assert captured["token"] == "tok-env"
    assert captured["encrypted_password"] == "enc-from-browser"


