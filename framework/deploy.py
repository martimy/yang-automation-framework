"""
Main entry point for YANG configuration provisioning.
"""

import argparse

import yaml

from intent.interface import InterfaceIntent
from intent.network_instance import NetworkInstanceIntent
from intent.ospf import OspfIntent, OspfAreaIntent, OspfInterfaceIntent
from intent.ntp import NtpIntent, NtpServerIntent

from credentials import resolve_credentials, vendor_for_host, all_hosts, CredentialsError
from registry import TRANSLATORS, ORCHESTRATORS
from scope import filter_intents
from transport.netconf import NetconfTransport
from transport.gnmi import GnmiTransport


def hydrate_intents(raw_intents: dict) -> dict:
    new_intents = {}

    if "interfaces" in raw_intents:
        new_intents["interfaces"] = [
            InterfaceIntent(**data) for data in raw_intents["interfaces"]
        ]

    if "network_instances" in raw_intents:
        new_intents["network_instances"] = [
            NetworkInstanceIntent(**data) for data in raw_intents["network_instances"]
        ]

    if "protocols" in raw_intents:
        new_intents["protocols"] = {}
        protocols = raw_intents["protocols"]

        if "ospf" in protocols:
            ospf_intents = []
            for ospf_data in protocols["ospf"]:
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

        if "ntp" in protocols:
            ntp_data = protocols["ntp"]
            servers = [
                NtpServerIntent(**server_data)
                for server_data in ntp_data.get("servers", [])
            ]
            new_intents["protocols"]["ntp"] = [
                NtpIntent(servers=servers, enabled=ntp_data.get("enabled", True))
            ]

    return new_intents


def load_devices_yml(path="devices.yml") -> dict:
    """host -> hydrated intents, for whichever devices currently have any
    configured. devices.yml no longer carries vendor/username -- those come
    from inventory.yml, looked up by host at deploy time."""
    with open(path, "r") as f:
        raw_devices = yaml.safe_load(f) or []

    intents_by_host = {}
    for raw_device in raw_devices:
        intents_by_host[raw_device["host"]] = hydrate_intents(raw_device.get("intents", {}))
    return intents_by_host


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
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Provision only this device (must be declared in inventory.yml). "
             "Default: every device in inventory.yml.",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default=None,
        help="Comma-separated intent categories to provision, e.g. "
             "'interfaces,ospf' or just 'snmp' -- lets you push one new "
             "piece of configuration without re-pushing everything else "
             "already configured for the device. Default: everything "
             "configured for the device (today's full-deploy behavior).",
    )
    args = parser.parse_args()

    transport_map = {"netconf": NetconfTransport, "gnmi": GnmiTransport}
    payload_format_map = {"netconf": "xml", "gnmi": "json"}
    TransportClass = transport_map[args.transport]
    payload_format = payload_format_map[args.transport]

    categories = (
        {c.strip() for c in args.categories.split(",")} if args.categories else None
    )

    print(f"--- Using {args.transport.upper()} transport ---")

    intents_by_host = load_devices_yml()
    hosts = [args.host] if args.host else all_hosts()

    for host in hosts:
        try:
            vendor = vendor_for_host(host)
            conn = resolve_credentials(host)
        except CredentialsError as e:
            print(f"\n>>> Skipping {host}: {e}")
            continue

        intents = intents_by_host.get(host, {})
        if not intents:
            print(f"\n>>> Skipping {host}: no configured intents in devices.yml")
            continue

        scoped_intents = filter_intents(intents, categories)
        if not scoped_intents:
            print(f"\n>>> Skipping {host}: nothing to provision for the selected categories")
            continue

        print(f"\n>>> Provisioning {host} ({vendor})")
        if args.transport == "netconf":
            transport = TransportClass(
                host=host, username=conn.username, password=conn.password
            )
        else:
            transport = TransportClass(
                host=host, username=conn.username, password=conn.password, vendor=vendor
            )

        orchestrator = ORCHESTRATORS[vendor](transport, TRANSLATORS[vendor])
        orchestrator.bootstrap()
        print("  \u2713 Bootstrap complete")
        orchestrator.provision(scoped_intents, payload_format=payload_format)


if __name__ == "__main__":
    main()
