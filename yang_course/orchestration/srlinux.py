from .base import DeviceOrchestrator
from intent.interface import InterfaceIntent
from intent.network_instance import NetworkInstanceIntent
from intent.ni_interface import NiInterfaceBindingIntent


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
        subif_payload = self.translators["subinterface"].translate_batch(intent)
        # print(subif_payload)

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
                    )
                )
                if not self.transport.push_config(binding_payload):
                    return False 
            return True
        return False
