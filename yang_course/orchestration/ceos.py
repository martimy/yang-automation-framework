from .base import DeviceOrchestrator
from intent.interface import InterfaceIntent


class CeosOrchestrator(DeviceOrchestrator):
    """
    cEOS recipe:
    1. Enable ip routing (bootstrap, once per device)
    2. Push interface + IP in a single payload
    """

    def bootstrap(self) -> bool:
        # example of something you do once per device
        # payload = self.translators["global"].translate(
        #     GlobalRoutingIntent(ipv4_enabled=True)
        # )
        # return self.transport.push_config(payload)
        return True

    def configure_interface(self, intents: list[InterfaceIntent], payload_format: str = 'xml') -> bool:
        """
        Configures interfaces on a cEOS device.

        Args:
            intents: A list of InterfaceIntent objects.
            payload_format: The desired payload format ('xml' or 'json').
        """
        # The translator's translate_batch method should handle the format.
        # We assume it's updated to do so. If not, logic would be needed here.
        payload = self.translators["interface"].translate_batch(intents, payload_format=payload_format)
        
        return self.transport.push_config(payload)
