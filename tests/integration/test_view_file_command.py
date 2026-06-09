import pandas as pd
import pytest

import solax_view


@pytest.mark.integration
def test_feather_view_opens_generated_html(tmp_path, monkeypatch):
    feather_file = tmp_path / "sample.feather"
    pd.DataFrame([{"a": 1}, {"a": 2}]).to_feather(feather_file)

    opened = {"path": None}

    def fake_open(path):
        opened["path"] = path
        return True

    monkeypatch.setattr(solax_view.webbrowser, "open", fake_open)

    solax_view.feather_view.callback(str(feather_file))

    assert opened["path"] is not None
    assert opened["path"].endswith(".html")


