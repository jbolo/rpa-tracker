class DeduplicationRegistry:
    _registry = {}

    @classmethod
    def register(cls, process_code: str, strategy):
        cls._registry[process_code] = strategy

    @classmethod
    def get(cls, process_code: str):
        return cls._registry[process_code]
