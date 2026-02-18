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
from intent.ospf import OspfIntent, OspfAreaIntent, OspfInterfaceIntent

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
                elif intent_type == "protocols":
                    new_intents["protocols"] = {}
                    
                    for protocol_type, instances_data in intents_data.items():
                        if protocol_type == "ospf":
                            ospf_intents = []
                            for ospf_data in instances_data:
                                areas = []
                                for area_data in ospf_data.get("areas", []):
                                    area_interfaces = [
                                        OspfInterfaceIntent(**iface_data)
                                        for iface_data in area_data.get("interfaces", [])
                                    ]
                                    areas.append(OspfAreaIntent(
                                        id=area_data["id"],
                                        interfaces=area_interfaces,
                                        area_type=area_data.get("area_type", "normal")
                                    ))
                                ospf_intents.append(OspfIntent(
                                    name=ospf_data["name"],
                                    network_instance=ospf_data["network_instance"],
                                    router_id=ospf_data.get("router_id"),
                                    areas=areas,
                                ))
                            new_intents["protocols"]["ospf"] = ospf_intents
                        
                        # Add other protocol types here (bgp, isis, etc.)
                        # elif protocol_type == "bgp":
                        #     bgp_intents = []
                        #     for bgp_data in instances_data:
                        #         neighbors = [
                        #             BgpNeighborIntent(**n) for n in bgp_data.get("neighbors", [])
                        #         ]
                        #         bgp_intents.append(BgpIntent(...))
                        #     new_intents["protocols"]["bgp"] = bgp_intents
                        
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
            username=device.get("username", os.getenv("DEFAULT_USERNAME")),
            password=passwords.get(device["vendor"]),
        )

        translators = TRANSLATORS[device["vendor"]]
        orchestrator = ORCHESTRATORS[device["vendor"]](transport, translators)

        orchestrator.bootstrap()
        print(f"  ✓ Bootstrap complete")

        # Configure interfaces and network instances first
        for intent_type, intents in device["intents"].items():
            if intent_type == "protocols":
                continue  # Handle protocols separately below
                
            method_name = intent_method_map.get(intent_type)
            if not method_name:
                print(f"  ✗ No method for intent: {intent_type}")
                continue

            configure_method = getattr(orchestrator, method_name, None)
            if not configure_method:
                print(f"  ✗ Orchestrator missing method: {method_name}")
                continue

            try:
                configure_method(intents, payload_format=payload_format)
                print(f"  ✓ {device['host']} — {intent_type} configured")
            except Exception as e:
                print(f"  ✗ Failed to configure {device['host']} {intent_type}: {str(e)}")
                traceback.print_exc()
                continue

        # Now configure protocols (must come after interfaces)
        protocols = device["intents"].get("protocols", {})
        
        for ospf_intent in protocols.get("ospf", []):
            try:
                orchestrator.configure_ospf(ospf_intent, payload_format=payload_format)
                print(f"  ✓ OSPF instance '{ospf_intent.name}' in {ospf_intent.network_instance}")
            except Exception as e:
                print(f"  ✗ Failed to configure OSPF '{ospf_intent.name}': {str(e)}")
                traceback.print_exc()
        
        # Add other protocol handlers here
        # for bgp_intent in protocols.get("bgp", []):
        #     try:
        #         orchestrator.configure_bgp(bgp_intent, payload_format=payload_format)
        #         print(f"  ✓ BGP AS {bgp_intent.as_number} in {bgp_intent.network_instance}")
        #     except Exception as e:
        #         print(f"  ✗ Failed to configure BGP: {str(e)}")
        #         traceback.print_exc()


if __name__ == "__main__":
    main()