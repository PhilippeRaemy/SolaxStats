class Schema:
    def __init__(self, key_columns, power_columns, energy_columns, info_columns):
        self.key_columns = key_columns
        self.data_columns = power_columns, energy_columns, info_columns
        self.power_columns = power_columns
        self.energy_columns = energy_columns
        self.info_columns = info_columns


POWER_SCHEMA = Schema(
    power_columns=[
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
        "totalChargePower"
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
        "batteryCapacity"]

)

ENERGY_SCHEMA = Schema(
    power_columns=[
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
        "totalChargePower",
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
        "powerdc1KWh",
        "powerdc2KWh",
        "powerdc3KWh",
        "powerdc4KWh",
        "pac1KWh",
        "pac2KWh",
        "pac3KWh",
        "pvPowerKWh",
        "gridpowerKWh",
        "feedinpowerKWh",
        "EPSPowerKWh",
        "epspowerKWh",
        "EpsActivePowerKWh",
        "feedinPowerMeter2KWh",
        "relayPowerKWh",
        "batPower1KWh",
        "consumeEnergyMeter2",
        "batteryCapacity"]

)
