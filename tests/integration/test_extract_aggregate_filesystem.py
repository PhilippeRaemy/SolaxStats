from datetime import datetime

import pandas as pd
import pytest

import schemas
import solax_extract as extract


@pytest.mark.integration
def test_aggregate_daily_writes_output_file(isolated_cfg):
    stats_folder, rawdata_folder = isolated_cfg

    base_row = {
        "year": 2024,
        "month": 1,
        "day": 1,
        "hour": 10,
        "minute": 0,
        "elapsed_time": 300,
    }
    for col in schemas.ENERGY_SCHEMA.energy_columns:
        base_row[col] = 1.0

    row2 = dict(base_row)
    row2["minute"] = 5

    df = pd.DataFrame([base_row, row2])
    day_file = rawdata_folder / extract.cfg.gen_feather_d(datetime(2024, 1, 1))
    df.to_feather(day_file)

    extract._aggregate("Daily", "None")

    output_path = stats_folder / extract.cfg.gen_feather_a("Daily")(datetime.now())
    assert output_path.exists()

    out_df = pd.read_feather(output_path)
    assert not out_df.empty
    assert "consumeEnergyMeter2" in out_df.columns

