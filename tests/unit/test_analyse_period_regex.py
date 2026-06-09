import solax_analyse


def test_show_with_invalid_period_returns_without_loading_data(monkeypatch):
    called = {"read": False}

    def fake_read_feather(*args, **kwargs):
        called["read"] = True
        raise AssertionError("read_feather should not be called for invalid periods")

    monkeypatch.setattr(solax_analyse.pd, "read_feather", fake_read_feather)

    solax_analyse.show.callback(report="Raw", by="5min", period="invalid", uom="kW")

    assert called["read"] is False


