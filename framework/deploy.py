"""
Main entry point for YANG configuration provisioning.
"""

import argparse
import os
import yaml
from dotenv import load_dotenv

from intent.interface import InterfaceIntent
from intent.network_instance import NetworkInstanceIntent
from intent.ospf import OspfIntent, OspfAreaIntent, OspfInterfaceIntent
from intent.ntp import NtpIntent, NtpServerIntent

from registry import TRANSLATORS, ORCHESTRATORS
from transport.netconf import NetconfTransport
from transport.gnmi import GnmiTransport


def main():
    """
    Main entry point for YANG configuration provisioning.
    """
    parser = argparse.ArgumentParser(
        description="Model-driven network provisioning tool."
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["netconf", "gnmi"],
        default="netconf",
        help="The transport protocol to use ('netconf' or 'gnmi').",
    )
    args = parser.parse_args()

    transport_map = {"netconf": NetconfTransport, "gnmi": GnmiTransport}
    payload_format_map = {"netconf": "xml", "gnmi": "json"}

    TransportClass = transport_map[args.transport]
    payload_format = payload_format_map[args.transport]

    print(f"--- Using {args.transport.upper()} transport ---")

    load_dotenv()
    passwords = {"ceos": os.getenv("CEOS_PASSWORD"), "srl": os.getenv("SRL_PASSWORD")}

    with open("devices.yml", "r") as f:
        raw_devices = yaml.safe_load(f)

    DEVICE_REGISTRY = []
    for raw_device in raw_devices:
        device = raw_device
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
                                    areas.append(
                                        OspfAreaIntent(
                                            id=area_data["id"],
                                            interfaces=area_interfaces,
                                            area_type=area_data.get("area_type", "normal"),
                                        )
                                    )
                                ospf_intents.append(
                                    OspfIntent(
                                        name=ospf_data["name"],
                                        network_instance=ospf_data["network_instance"],
                                        router_id=ospf_data.get("router_id"),
                                        areas=areas,
                                    )
                                )
                            new_intents["protocols"]["ospf"] = ospf_intents
                        elif protocol_type == "ntp":
                            servers = [
                                NtpServerIntent(**server_data)
                                for server_data in instances_data.get("servers", [])
                            ]
                            ntp_intent = NtpIntent(
                                servers=servers,
                                enabled=instances_data.get("enabled", True)
                            )
                            new_intents["protocols"]["ntp"] = [ntp_intent]
            device["intents"] = new_intents
        DEVICE_REGISTRY.append(device)

    for device in DEVICE_REGISTRY:
        print(f"\n>>> Provisioning {device['host']} ({device['vendor']})")
        transport = TransportClass(host=device["host"])
        orchestrator = ORCHESTRATORS[device["vendor"]](transport, TRANSLATORS[device["vendor"]])
        orchestrator.bootstrap()
        print(f"  ✓ Bootstrap complete")
        orchestrator.provision(device["intents"], payload_format=payload_format)


if __name__ == "__main__":
    main()