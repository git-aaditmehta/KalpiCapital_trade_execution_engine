from typing import Dict, Type

from app.brokers.base import BrokerAdapter
from app.brokers.zerodha import ZerodhaAdapter
from app.brokers.fyers import FyersAdapter
from app.brokers.angelone import AngelOneAdapter
from app.brokers.groww import GrowwAdapter
from app.brokers.upstox import UpstoxAdapter
from app.brokers.dhan import DhanAdapter


class BrokerRegistry:
    """
    Central registry that maps broker names to their adapter classes.
    To add a new broker:
      1. Create a new adapter class extending BrokerAdapter
      2. Register it here with BrokerRegistry.register("name", AdapterClass)
    """

    _adapters: Dict[str, Type[BrokerAdapter]] = {}

    @classmethod
    def register(cls, name: str, adapter_class: Type[BrokerAdapter]) -> None:
        cls._adapters[name.lower()] = adapter_class

    @classmethod
    def get(cls, name: str) -> BrokerAdapter:
        adapter_class = cls._adapters.get(name.lower())
        if adapter_class is None:
            available = ", ".join(cls._adapters.keys())
            raise ValueError(f"Broker '{name}' not found. Available brokers: {available}")
        return adapter_class()

    @classmethod
    def list_brokers(cls) -> list[str]:
        return list(cls._adapters.keys())


# Auto-register all built-in adapters
BrokerRegistry.register("zerodha", ZerodhaAdapter)
BrokerRegistry.register("fyers", FyersAdapter)
BrokerRegistry.register("angelone", AngelOneAdapter)
BrokerRegistry.register("groww", GrowwAdapter)
BrokerRegistry.register("upstox", UpstoxAdapter)
BrokerRegistry.register("dhan", DhanAdapter)


def get_broker_adapter(broker_name: str) -> BrokerAdapter:
    """Convenience function to get a broker adapter by name."""
    return BrokerRegistry.get(broker_name)
