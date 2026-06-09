# AGENTS

## Purpose
SolaxStats is a command-line toolkit for collecting and analyzing historical production and consumption data from a solar installation using SolaX hardware (via SolaX Cloud APIs).

The main goal is to:
- authenticate to SolaX Cloud,
- extract daily raw telemetry history,
- transform and store it in local analytics-friendly formats,
- aggregate it by time period,
- inspect and plot production/consumption trends.

## Architecture Overview
The project follows a small CLI-oriented ETL architecture:

1. **Configure** data source and storage paths.
2. **Extract** daily history from SolaX Cloud and save raw JSON snapshots.
3. **Transform** JSON snapshots into Feather files with normalized timestamps and derived energy values.
4. **Aggregate** into broader time windows (`All`, `Hourly`, `Daily`, `Monthly`).
5. **Consume** via plotting and table viewing commands.

## Main Components
- `solax.py`
  - Root CLI entrypoint.
  - Registers command groups: `configure`, `extract`, `analyse`, `view`.

- `solax_configure.py`
  - Loads and merges settings from environment variables and JSON config files.
  - Defines folder/file naming helpers used by extract/aggregate steps.

- `solax_extract.py`
  - Handles login and historical API calls.
  - Writes raw day-level JSON files to `rawdata/`.
  - Converts daily JSON to Feather.
  - Computes helper fields (for example: timestamps, elapsed seconds, derived `*KWh` columns).
  - Aggregates daily files into period-level datasets.

- `schemas.py`
  - Defines schema/column groupings used during transformation and aggregation.

- `solax_analyse.py`
  - Loads aggregated Feather data for a selected period.
  - Produces plots for production/consumption-related metrics.

- `solax_view.py`
  - Opens a Feather file as an HTML table in a browser for quick inspection.

- `clock_watch.py`
  - Lightweight timing utility used to report elapsed processing time.

## Data Layout (Typical)
- `rawdata/`
  - Daily JSON snapshots fetched from SolaX Cloud.
- stats/output folder (from config)
  - Daily Feather files.
  - Aggregated Feather files by granularity (`All`, `Hourly`, `Daily`, `Monthly`).

## Typical Workflow
1. Configure credentials and local storage (`solax configure ...` or config file/environment).
2. Run extraction (`solax extract history`) to pull date ranges from SolaX Cloud.
3. Let conversion and aggregation generate analytics datasets.
4. Use `solax analyse show` for charts.
5. Use `solax view file <path>` for tabular inspection.

## Notes
- This is a local, user-operated data pipeline intended for personal energy analytics.
- API authentication/session behavior depends on SolaX Cloud endpoints.
- Existing tests are minimal; validate key flows after changes, especially around schema evolution and aggregation outputs.

