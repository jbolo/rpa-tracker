from rpa_tracker.tracking.deduplication.registry import DeduplicationRegistry


class DummyStrategy:
    pass


def test_registry_register_and_get():
    strategy = DummyStrategy()
    DeduplicationRegistry.register("TEST_PROC", strategy)

    retrieved = DeduplicationRegistry.get("TEST_PROC")
    assert retrieved is strategy
