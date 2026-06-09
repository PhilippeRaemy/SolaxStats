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

