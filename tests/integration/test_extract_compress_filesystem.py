import json
from datetime import datetime

import pandas as pd
import pytest

import solax_extract as extract


@pytest.mark.integration
def test_compress_converts_json_to_feather(isolated_cfg, sample_power_rows, monkeypatch):
    _, rawdata_folder = isolated_cfg

    json_name = extract.cfg.gen_json_d(datetime(2024, 1, 1))
    json_path = rawdata_folder / json_name
    json_path.write_text(json.dumps({"object": sample_power_rows}), encoding="utf8")

    monkeypatch.setattr(extract.cfg, "solax_rawdata_folder", str(rawdata_folder), raising=False)

    extract.compress.callback(force=True)

    feather_path = json_path.with_suffix(".feather")
    assert feather_path.exists()

    df = pd.read_feather(feather_path)
    assert "timestamp" in df.columns
    assert "elapsed_time" in df.columns
    assert "powerdc1KWh" in df.columns


