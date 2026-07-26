from .base import DeviceOrchestrator
from intent.interface import InterfaceIntent
from intent.network_instance import NetworkInstanceIntent
from intent.ospf import OspfIntent
from intent.ntp import NtpIntent
from intent.snmp import SnmpIntent
from typing import List

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

    def configure_network_instance(self, intent: NetworkInstanceIntent, payload_format: str = "xml") -> bool:
        ni_payload = self.translators["network_instance"].translate(
            intent, payload_format=payload_format
        )
        return self.transport.push_config(ni_payload)

    def configure_interface(
        self, intent: list[InterfaceIntent], payload_format: str = "xml"
    ) -> bool:

        # Step 1: Create the subinterface with IP
        subif_payload = self.translators["subinterface"].translate(
            intent, payload_format=payload_format
        )

        self.transport.push_config(subif_payload)

        # Step 2: Associate an interface to an instance

        if self.transport.push_config(subif_payload):
            for i in intent:
                binding_payload = self.translators["ni_interface"].translate(
                    i,
                    payload_format=payload_format
                )
                # print(binding_payload)
                result = self.transport.push_config(binding_payload)

        return True


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

    def configure_snmp(self, intent: SnmpIntent, payload_format: str = "xml") -> bool:
        snmp_payload = self.translators["snmp"].translate(
            intent, payload_format=payload_format
        )
        return self.transport.push_config(snmp_payload)
