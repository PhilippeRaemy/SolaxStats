class Schema:
    def __init__(self, key_columns, power_column, energy_columns, info_columns):
        self.key_columns = key_columns
        self.data_columns = power_column, energy_columns, info_columns


POWER_SCHEMA = Schema(
    power_column=[
        "powerdc1",
        "powerdc2",
        "powerdc3",
        "powerdc4",
        "pac1",
        "pac2",
        "pac3",
        "pvPower",
        "gridpower",
        "feedinpower",
        "EPSPower",
        "epspower",
        "EpsActivePower",
        "feedinPowerMeter2",
        "relayPower",
        "batPower1",
    ],
    key_columns=[
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "timestamp"
    ],
    info_columns=[
        "inverterSn",
        "inverterType",
        "pileSn",
        "fiveMinuteVal",
        "uploadTimeValue",
        "Meter2ComState",
        "elapsed_time"
    ],
    energy_columns=[
        "consumeEnergyMeter2",
        "batteryCapacity",
        "totalChargePower"]

)
