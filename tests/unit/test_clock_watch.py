from clock_watch import clock_watch


def test_clock_watch_reports_messages():
    messages = []

    with clock_watch(messages.append, "sample") as cw:
        cw.print("step")

    assert any("sample : step" in msg for msg in messages)
    assert any("sample : Done" in msg for msg in messages)

