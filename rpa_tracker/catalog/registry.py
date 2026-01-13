"""Registry for platform definitions in RPA Tracker."""
from typing import Dict
from rpa_tracker.catalog.platform import PlatformDefinition


class PlatformRegistry:
    _platforms: Dict[str, PlatformDefinition] = {}

    @classmethod
    def register(cls, platform: PlatformDefinition) -> None:
        """Registers a platform definition."""
        cls._platforms[platform.code] = platform

    @classmethod
    def get(cls, code: str) -> PlatformDefinition:
        """Retrieves a platform definition by code."""
        return cls._platforms[code]

    @classmethod
    def all(cls):
        """Retrieves all platform definitions."""
        return sorted(
            cls._platforms.values(),
            key=lambda p: p.order
        )
