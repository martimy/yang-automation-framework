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

    def provision(self, intents: dict, payload_format: str):
        """Orchestrate full device provisioning in the correct dependency order."""

        # Phase 1: Network instances (foundation)
        for intent in intents.get("network_instances", []):
            print("config instance")
            self.configure_network_instance([intent], payload_format=payload_format)

        # Phase 2: Interfaces (neded for everything else)
        for intent in intents.get("interfaces", []):
            self.configure_interface([intent], payload_format=payload_format)

        # Phase 3: Protocols (depend on interfaces and network instances)
        protocols = intents.get("protocols", {})

        for ospf_intent in protocols.get("ospf", []):
            self.configure_ospf(ospf_intent, payload_format=payload_format)

        for ntp_intent in protocols.get("ntp", []):
            self.configure_ntp(ntp_intent, payload_format=payload_format)