# Tests

The suite is separated to support fast CI unit checks and optional integration coverage.

## Layout

- `tests/unit/`: standalone tests (no network, minimal side effects)
- `tests/integration/`: CLI/filesystem integration tests
  - live external API tests are marked with `@pytest.mark.network`

## Run

Use the project virtual environment:

```powershell
Set-Location "C:\dev\personal\SolaxStats"
.\.env\Scripts\python.exe -m pytest tests\unit -q
.\.env\Scripts\python.exe -m pytest tests\integration -m "integration and not network" -q
.\.env\Scripts\python.exe -m pytest -m network -q
```

The last command runs live SolaX tests and requires credentials in env vars (see `tests/integration/test_extract_history_live_api.py`).

