"""
Main entry point for YANG configuration provisioning.
"""

from device_registry import DEVICE_REGISTRY
from registry import TRANSLATORS, ORCHESTRATORS
from transport.netconf import NetconfTransport
from orchestration.ceos import CeosOrchestrator
from orchestration.srlinux import SrlinuxOrchestrator
from translation.ceos.interface import CeosInterfaceTranslator
from translation.srlinux.subinterface import SrlinuxInterfaceTranslator


def provision_all():
    """
    Provision all devices defined in the device registry.
    """
    for device in DEVICE_REGISTRY:
        # Create transport
        print(f"\n>>> Provisioning {device['host']} ({device['vendor']})")
        transport = NetconfTransport(
            host=device["host"], username=device["admin"], password=device["secret"]
        )

        # Get vendor-specific translators and orchestrator
        translators = TRANSLATORS[device["vendor"]]

        # Create orchestrator instance
        orchestrator = ORCHESTRATORS[device["vendor"]](transport, translators)

        # Run bootstrap once per device
        orchestrator.bootstrap()
        print(f"  ✓ Bootstrap complete")

        # Apply each intent in order
        for type, intent in device["intents"].items():
            # try:
            if type == "interfaces":
                orchestrator.configure_interface(intent)

            print(f"✓ {device['host']} — {type} configured")

            # except Exception as e:
            #     print(f"✗ Failed to configure {device['host']}: {str(e)}")
            #     continue


if __name__ == "__main__":
    provision_all()
