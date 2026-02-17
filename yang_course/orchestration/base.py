from abc import ABC, abstractmethod
from intent.interface import InterfaceIntent


class DeviceOrchestrator(ABC):
    """
    Abstract base — one concrete subclass per vendor.
    Knows the correct sequence of operations for that vendor.
    """

    def __init__(self, transport, translators):
        self.transport = transport
        self.translators = translators

    @abstractmethod
    def configure_interface(self, intent: InterfaceIntent) -> bool:
        pass

    @abstractmethod
    def bootstrap(self) -> bool:
        """Apply any one-time prerequisites the device needs."""
