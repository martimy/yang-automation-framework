from .base import DeviceOrchestrator
from intent.interface import InterfaceIntent
from intent.ni_interface import NiInterfaceBindingIntent
from intent.ospf import OspfIntent
from intent.ntp import NtpIntent


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

    def configure_interface(
        self, intent: InterfaceIntent, payload_format: str = "xml"
    ) -> bool:
        # Step 1: Create the subinterface with IP
        subif_payload = self.translators["subinterface"].translate(
            intent, payload_format=payload_format
        )
        # print(subif_payload)

        return self.transport.push_config(subif_payload)

        if self.transport.push_config(subif_payload):
            # # Step 2: Ensure the network-instance exists
            # ni_payload = self.translators["network_instance"].translate_batch(
            #     NetworkInstanceIntent(
            #         name=intent.network_instance,
            #         type="ip-vrf",
            #         description="default vrf",
            #     )
            # )
            # if self.transport.push_config(ni_payload):

            # Step 3: Bind subinterface to network-instance
            # Temp solution

            for i in intent:
                binding_payload = self.translators["ni_interface"].translate(
                    NiInterfaceBindingIntent(
                        network_instance=i.network_instance,
                        interface=i.name,
                        subinterface=i.subinterface,
                    ),
                    payload_format=payload_format,
                )
                if not self.transport.push_config(binding_payload):
                    return False
            return True
        return False

    def configure_ospf(self, intent: OspfIntent, payload_format: str = "xml") -> bool:
        ospf_payload = self.translators["ospf"].translate(
            intent, payload_format=payload_format
        )
        return self.transport.push_config(ospf_payload)

    def configure_ntp(self, intent: NtpIntent, payload_format: str = "xml") -> bool:
        ntp_payload = self.translators["ntp"].translate(
            intent, payload_format=payload_format
        )
        return self.transport.push_config(ntp_payload)
