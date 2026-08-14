from cpgf.ingestion.siafi import discover_latest_csv_resource


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload

    def get(self, *args, **kwargs):
        return FakeResponse(self.payload)


def test_discovers_latest_csv_resource():
    payload = {
        "success": True,
        "result": {
            "resources": [
                {
                    "id": "old",
                    "name": "old",
                    "format": "CSV",
                    "url": "https://example/old.csv",
                    "last_modified": "2024-01-01T00:00:00",
                    "size": 10,
                },
                {
                    "id": "new",
                    "name": "new",
                    "format": "CSV",
                    "url": "https://example/new.csv",
                    "last_modified": "2025-06-01T00:00:00",
                    "size": 20,
                },
            ]
        },
    }
    resource = discover_latest_csv_resource(session=FakeSession(payload))
    assert resource.id == "new"
    assert resource.url.endswith("new.csv")
