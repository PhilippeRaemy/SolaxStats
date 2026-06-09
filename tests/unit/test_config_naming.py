from datetime import datetime

import solax_configure as cfg


def test_date_from_filename_parses_date():
    dt = cfg.date_from_filename("solax.2024-06-09.json")
    assert dt == datetime(2024, 6, 9)


def test_date_from_filename_defaults_on_invalid_name():
    dt = cfg.date_from_filename("bad-name.json")
    assert dt == datetime(1900, 1, 1)


def test_daily_namers_build_expected_suffixes():
    dt = datetime(2025, 1, 2)
    assert cfg.gen_json_d(dt).endswith("2025-01-02.json")
    assert cfg.gen_feather_d(dt).endswith("2025-01-02.feather")


def test_partitioned_namers_return_filename_and_regex_pattern():
    dt = datetime(2025, 3, 1)

    monthly = cfg.gen_feather_m("Daily")
    yearly = cfg.gen_feather_y("Monthly")
    all_file = cfg.gen_feather_a("All")

    assert monthly(dt).endswith("Daily.2025-03.feather")
    assert yearly(dt).endswith("Monthly.2025.feather")
    assert all_file(dt).endswith("All.feather")

    # pattern strings are used in re.compile(...) in aggregation code
    assert "(?P<yyyy>" in monthly(None)
    assert "(?P<yyyy>" in yearly(None)
    assert all_file(None).endswith("All\\.feather")

