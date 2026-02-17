"""
Main entry point for YANG configuration provisioning.
"""

import os
import yaml
from dotenv import load_dotenv
from intent.interface import InterfaceIntent
from intent.network_instance import NetworkInstanceIntent
from registry import TRANSLATORS, ORCHESTRATORS
from transport.netconf import NetconfTransport


def provision_all():
    """
    Provision all devices defined in the device registry.
    """

    load_dotenv()
    passwords = {"ceos": os.getenv("CEOS_PASSWORD"), "srl": os.getenv("SRL_PASSWORD")}

    # Load DEVICE_REGISTRY from YAML file
    with open("devices.yml", "r") as f:
        raw_devices = yaml.safe_load(f)

    DEVICE_REGISTRY = []
    for raw_device in raw_devices:
        device = raw_device
        # Re-instantiate intent objects from loaded data
        if "intents" in device:
            new_intents = {}
            for intent_type, intents_data in device["intents"].items():
                if intent_type == "interfaces":
                    new_intents["interfaces"] = [
                        InterfaceIntent(**data) for data in intents_data
                    ]
                elif intent_type == "network_instances":
                    new_intents["network_instances"] = [
                        NetworkInstanceIntent(**data) for data in intents_data
                    ]
                # Add other intent types here
            device["intents"] = new_intents
        DEVICE_REGISTRY.append(device)

    # A mapping between intent types and orchestrator methods
    intent_method_map = {
        "interfaces": "configure_interface",
        "network_instances": "configure_network_instance",
    }

    for device in DEVICE_REGISTRY:
        # Create transport
        print(f"\n>>> Provisioning {device['host']} ({device['vendor']})")

        transport = NetconfTransport(
            host=device["host"],
            username=device["username"],
            password=passwords.get(device["vendor"]),
        )

        # Get vendor-specific translators and orchestrator
        translators = TRANSLATORS[device["vendor"]]

        # Create orchestrator instance
        orchestrator = ORCHESTRATORS[device["vendor"]](transport, translators)

        # Run bootstrap once per device
        orchestrator.bootstrap()
        print(f"  ✓ Bootstrap complete")

        # Apply each intent in order
        for intent_type, intents in device["intents"].items():
            method_name = intent_method_map.get(intent_type)
            if not method_name:
                print(
                    f"  ✗ No orchestrator method found for intent type: {intent_type}"
                )
                continue

            # Get the actual orchestrator method
            configure_method = getattr(orchestrator, method_name, None)

            if not configure_method:
                print(
                    f"  ✗ Orchestrator for {device['vendor']} does not have method: {method_name}"
                )
                continue

            try:
                configure_method(intents)
                print(f"  ✓ {device['host']} — {intent_type} configured")
            except Exception as e:
                print(f"  ✗ Failed to configure {device['host']}: {str(e)}")
                continue


if __name__ == "__main__":
    provision_all()
