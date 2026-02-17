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

    def configure_interface(self, intent: InterfaceIntent) -> bool:
        # Single payload covers interface + IP + implicit no switchport
        payload = self.translators["interface"].translate_batch(intent)
        # print(payload)
        return self.transport.push_config(payload)
