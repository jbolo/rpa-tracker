class FakeDeduplication:
    version = 1

    def __init__(self):
        self._store = {}

    def calculate_fingerprint(self, data):
        return data["key"]

    def find_existing_uuid(self, fingerprint):
        return self._store.get(fingerprint)

    def persist_data(self, uuid, data):
        self._store[data["key"]] = uuid
