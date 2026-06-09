import os
from datetime import datetime

import pytest

import solax_configure as cfg


@pytest.fixture
def isolated_cfg(tmp_path, monkeypatch):
    stats_folder = tmp_path / "stats"
    rawdata_folder = stats_folder / "rawdata"
    stats_folder.mkdir(parents=True, exist_ok=True)
    rawdata_folder.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(cfg, "solax_stats_folder", str(stats_folder), raising=False)
    monkeypatch.setattr(cfg, "solax_rawdata_folder", str(rawdata_folder), raising=False)
    monkeypatch.setattr(cfg, "site_id", "site-123", raising=False)
    monkeypatch.setattr(cfg, "user_name", "user@example.com", raising=False)
    monkeypatch.setattr(cfg, "site_password", "plain-password", raising=False)
    monkeypatch.setattr(cfg, "encrypted_password", "encrypted-password", raising=False)
    monkeypatch.setattr(cfg, "auth_mode", "legacy_encrypted", raising=False)
    monkeypatch.setattr(cfg, "api_token", None, raising=False)

    return stats_folder, rawdata_folder


@pytest.fixture
def sample_power_rows():
    return [
        {
            "year": 2024,
            "month": 1,
            "day": 1,
            "hour": 10,
            "minute": 0,
            "powerdc1": 1000,
            "powerdc2": 900,
            "pac1": 400,
            "pac2": 300,
            "pac3": 300,
            "pvPower": 1200,
            "gridpower": 250,
            "feedinpower": 120,
            "EPSPower": 0,
            "epspower": 0,
            "EpsActivePower": 0,
            "feedinPowerMeter2": 0,
            "relayPower": 0,
            "batPower1": 100,
            "consumeEnergyMeter2": 100,
            "batteryCapacity": 50,
        },
        {
            "year": 2024,
            "month": 1,
            "day": 1,
            "hour": 10,
            "minute": 5,
            "powerdc1": 1100,
            "powerdc2": 950,
            "pac1": 450,
            "pac2": 300,
            "pac3": 300,
            "pvPower": 1300,
            "gridpower": 240,
            "feedinpower": 130,
            "EPSPower": 0,
            "epspower": 0,
            "EpsActivePower": 0,
            "feedinPowerMeter2": 0,
            "relayPower": 0,
            "batPower1": 80,
            "consumeEnergyMeter2": 105,
            "batteryCapacity": 51,
        },
    ]

