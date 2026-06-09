import json

import solax_extract as extract


class DummyResponse:
    def __init__(self, payload):
        self.content = json.dumps(payload).encode("utf8")


def test_json_decode_reads_utf8_content():
    response = DummyResponse({"ok": True, "token": "abc"})
    decoded = extract.json_decode(response)
    assert decoded == {"ok": True, "token": "abc"}

