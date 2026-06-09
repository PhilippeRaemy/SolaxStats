from datetime import datetime
import os

import pytest

import solax_extract as extract


@pytest.mark.integration
@pytest.mark.network
def test_legacy_login_and_daily_data_live(monkeypatch):
    user_name = os.environ.get("SOLAX_TEST_USER_NAME")
    encrypted_password = os.environ.get("SOLAX_TEST_ENCRYPTED_PASSWORD")
    site_id = os.environ.get("SOLAX_TEST_SITE_ID")

    if not (user_name and encrypted_password and site_id):
        pytest.skip("Set SOLAX_TEST_USER_NAME, SOLAX_TEST_ENCRYPTED_PASSWORD and SOLAX_TEST_SITE_ID to run live test.")

    monkeypatch.setattr(extract.cfg, "site_id", site_id, raising=False)

    session, login_response = extract.login(
        extract.LEGACY_LOGIN_URL,
        proxies={},
        user_name=user_name,
        encrypted_password=encrypted_password,
    )

    assert isinstance(login_response, dict)
    assert login_response.get("token")

    daily_response = extract.get_daily_data(
        session=session,
        token=login_response["token"],
        url=extract.LEGACY_DAILY_URL,
        date=datetime.now(),
        proxies={},
    )

    assert daily_response.status_code == 200
    payload = extract.json_decode(daily_response)
    assert isinstance(payload, dict)

