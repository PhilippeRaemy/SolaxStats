import pandas as pd

import schemas
import solax_extract as extract


def test_concat_impl_groups_and_sums_energy_columns():
    def make_row(minute, powerdc1, consume, battery):
        row = {"year": 2024, "month": 1, "day": 1, "hour": 10, "minute": minute, "elapsed_time": 300}
        for col in schemas.ENERGY_SCHEMA.energy_columns:
            row[col] = 0.0
        row["powerdc1KWh"] = powerdc1
        row["consumeEnergyMeter2"] = consume
        row["batteryCapacity"] = battery
        return row

    df1 = pd.DataFrame([make_row(0, 100, 5, 50), make_row(5, 110, 6, 52)])
    df2 = pd.DataFrame([make_row(0, 120, 7, 53)])

    result = extract.concat_impl([df1, df2], ["year", "month", "day", "hour", "minute"])

    first_group = result.loc[(2024, 1, 1, 10, 0)]
    assert first_group["elapsed_time"] == 600
    assert first_group["powerdc1KWh"] == 220
    assert first_group["consumeEnergyMeter2"] == 12


