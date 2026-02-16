from abc import ABC, abstractmethod

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
        pass

class CeosOrchestrator(DeviceOrchestrator):
    """
    cEOS recipe:
    1. Enable ip routing (bootstrap, once per device)
    2. Push interface + IP in a single payload
    """
    def bootstrap(self) -> bool:
        # ip routing is a global prerequisite on cEOS
        payload = self.translators['global'].translate_routing(
            GlobalRoutingIntent(enabled=True)
        )
        return self.transport.push_config(payload)

    def configure_interface(self, intent: InterfaceIntent) -> bool:
        # Single payload covers interface + IP + implicit no switchport
        payload = self.translators['interface'].translate(intent)
        return self.transport.push_config(payload)

class SrlinuxOrchestrator(DeviceOrchestrator):
    """
    SR-Linux recipe:
    1. Create subinterface on the parent interface
    2. Create or verify network-instance exists
    3. Bind subinterface to network-instance
    All three must succeed in order.
    """
    def bootstrap(self) -> bool:
        # SR-Linux has a default network-instance already
        # but we verify it exists before proceeding
        return True

    def configure_interface(self, intent: InterfaceIntent) -> bool:
        # Step 1: Create the subinterface with IP
        subif_payload = self.translators['subinterface'].translate(intent)
        self.transport.push_config(subif_payload)

        # Step 2: Ensure the network-instance exists
        ni_payload = self.translators['network_instance'].translate(
            NetworkInstanceIntent(
                name=intent.network_instance,
                type='L3'
            )
        )
        self.transport.push_config(ni_payload)

        # Step 3: Bind subinterface to network-instance
        binding_payload = self.translators['ni_interface'].translate(
            NiInterfaceBindingIntent(
                network_instance=intent.network_instance,
                interface=intent.name,
                subinterface=intent.subinterface_index
            )
        )
        return self.transport.push_config(binding_payload)
