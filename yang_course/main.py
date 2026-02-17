"""
Main entry point for YANG configuration provisioning.
"""

import argparse
import os
import yaml
from dotenv import load_dotenv
import traceback

from intent.interface import InterfaceIntent
from intent.network_instance import NetworkInstanceIntent
from registry import TRANSLATORS, ORCHESTRATORS
from transport.netconf import NetconfTransport
from transport.gnmi import GnmiTransport


def main():
    """
    Main entry point for YANG configuration provisioning.
    """
    parser = argparse.ArgumentParser(description="Model-driven network provisioning tool.")
    parser.add_argument(
        '--transport',
        type=str,
        choices=['netconf', 'gnmi'],
        default='netconf',
        help="The transport protocol to use ('netconf' or 'gnmi')."
    )
    args = parser.parse_args()

    # --- Protocol-to-Class Mapping ---
    transport_map = {
        'netconf': NetconfTransport,
        'gnmi': GnmiTransport
    }
    payload_format_map = {
        'netconf': 'xml',
        'gnmi': 'json'
    }

    TransportClass = transport_map[args.transport]
    payload_format = payload_format_map[args.transport]

    print(f"--- Using {args.transport.upper()} transport ---")

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
        print(f"\n>>> Provisioning {device['host']} ({device['vendor']})")

        # --- Dynamic Transport Instantiation ---
        transport = TransportClass(
            host=device["host"],
            username=device.get("username", os.getenv("DEFAULT_USERNAME")), # Add default user
            password=passwords.get(device["vendor"]),
        )

        translators = TRANSLATORS[device["vendor"]]
        orchestrator = ORCHESTRATORS[device["vendor"]](transport, translators)

        orchestrator.bootstrap()
        print(f"  ✓ Bootstrap complete")

        for intent_type, intents in device["intents"].items():
            method_name = intent_method_map.get(intent_type)
            if not method_name:
                print(f"  ✗ No method for intent: {intent_type}")
                continue

            configure_method = getattr(orchestrator, method_name, None)
            if not configure_method:
                print(f"  ✗ Orchestrator missing method: {method_name}")
                continue

            try:
                # --- Pass the payload_format to the orchestrator ---
                # This assumes the orchestrator methods will pass it down to the translators
                configure_method(intents, payload_format=payload_format)
                print(f"  ✓ {device['host']} — {intent_type} configured")
            except Exception as e:
                print(f"  ✗ Failed to configure {device['host']}: {str(e)}")
                traceback.print_exc()
                continue


if __name__ == "__main__":
    main()
