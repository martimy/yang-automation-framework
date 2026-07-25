"""
Wraps the existing framework package (framework/deploy.py's logic, split
into reusable pieces) for the GUI:

  load_devices()        -- devices.yml -> list of dicts with hydrated
                            intent dataclasses (same shape deploy.py builds)
  save_devices(devices)  -- reverse of the above, back to devices.yml
  preview_translation()  -- runs ONLY the Translation stage (translator.translate)
                            for a device, without calling transport.push_config.
                            This is what powers "inspect the Translation stage"
                            with zero side effects on real devices.
  run_deployment()       -- runs orchestrator.bootstrap() + .provision(), i.e.
                            Orchestration -> Translation -> Transport for real,
                            captures stdout, returns one structured result.

Nothing here talks to devices.yml's on-disk YAML comments/formatting -- ruamel
would preserve those if that's wanted later; plain PyYAML is used for now,
consistent with what deploy.py already does.
"""

import contextlib
import dataclasses
import io
from typing import Any

import yaml

import framework_bridge  # noqa: F401  (side effect: sys.path)
from framework_bridge import DEVICES_YML

import credentials
from credentials import CredentialsError
from scope import filter_intents

from intent.interface import InterfaceIntent
from intent.network_instance import NetworkInstanceIntent
from intent.ospf import OspfIntent, OspfAreaIntent, OspfInterfaceIntent
from intent.ntp import NtpIntent, NtpServerIntent
from intent.snmp import SnmpIntent

from registry import TRANSLATORS, ORCHESTRATORS
from transport.netconf import NetconfTransport
from transport.gnmi import GnmiTransport

TRANSPORT_MAP = {"netconf": NetconfTransport, "gnmi": GnmiTransport}
PAYLOAD_FORMAT_MAP = {"netconf": "xml", "gnmi": "json"}

# The only top-level / protocols keys the framework's dataclasses actually
# understand today. Anything else (e.g. a hand-added "protocols: {radius: ...}"
# block) has no dataclass, translator, or orchestrator wiring behind it --
# hydrate_intents/dehydrate_intents preserve it verbatim through save/load
# rather than silently discarding it, but nothing will ever translate or
# deploy it. unrecognized_intent_keys() is how callers surface that as a
# warning instead of letting it pass silently.
#
# "snmp" hydrates into SnmpIntent below even though no translator/registry
# entry exists for it yet -- see intent/snmp.py and the GUI README's "If you
# extend the framework" note. Without this, preview_translation()'s snmp loop
# would hand a translator a raw dict instead of an SnmpIntent instance the
# moment one gets registered.
KNOWN_TOP_LEVEL_INTENT_KEYS = {"interfaces", "network_instances", "protocols"}
KNOWN_PROTOCOL_KEYS = {"ospf", "ntp", "snmp"}


class ValidationError(Exception):
    """Raised when a device entry from the GUI doesn't hydrate cleanly."""


def unrecognized_intent_keys(raw_intents: dict) -> list[str]:
    """Human-readable dotted names (e.g. 'protocols.snmp') for any key in a
    raw intents dict that the framework has no dataclass/translator for."""
    unrecognized = [k for k in raw_intents if k not in KNOWN_TOP_LEVEL_INTENT_KEYS]
    protocols = raw_intents.get("protocols") or {}
    unrecognized += [f"protocols.{k}" for k in protocols if k not in KNOWN_PROTOCOL_KEYS]
    return unrecognized


# ---------------------------------------------------------------------------
# Hydration: raw dict (as read from YAML / posted by the GUI) -> dataclasses.
# This mirrors the loop in deploy.py's main(), extracted so both the CLI
# and the GUI share one implementation instead of drifting apart.
# ---------------------------------------------------------------------------

def hydrate_intents(raw_intents: dict) -> dict:
    new_intents: dict[str, Any] = {}

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

        if "snmp" in protocols:
            # List-shaped, like ospf -- a device can have more than one SNMP
            # target (e.g. separate v2c and v3 configs).
            new_intents["protocols"]["snmp"] = [
                SnmpIntent(**snmp_data) for snmp_data in protocols["snmp"]
            ]

        # Anything else under protocols (e.g. a hand-added "radius" block) has
        # no dataclass/translator behind it -- pass it through untouched so
        # a save never silently discards it. See unrecognized_intent_keys().
        for key, value in protocols.items():
            if key not in KNOWN_PROTOCOL_KEYS:
                new_intents["protocols"][key] = value

    # Same for unrecognized top-level keys (anything besides interfaces /
    # network_instances / protocols).
    for key, value in raw_intents.items():
        if key not in KNOWN_TOP_LEVEL_INTENT_KEYS:
            new_intents[key] = value

    return new_intents


def hydrate_device(raw_device: dict) -> dict:
    device = dict(raw_device)
    if "intents" in device:
        try:
            device["intents"] = hydrate_intents(device["intents"])
        except (TypeError, KeyError) as exc:
            raise ValidationError(f"{device.get('host', '?')}: {exc}") from exc
    return device


# ---------------------------------------------------------------------------
# Dehydration: dataclasses -> plain dict, matching devices.yml's own shape
# (not just dataclasses.asdict's default shape -- ntp in particular is
# stored as a single dict in the YAML but as a 1-item list internally,
# same asymmetry deploy.py's hydration introduces).
# ---------------------------------------------------------------------------

def dehydrate_intents(intents: dict) -> dict:
    raw: dict[str, Any] = {}

    if "interfaces" in intents:
        raw["interfaces"] = [dataclasses.asdict(i) for i in intents["interfaces"]]

    if "network_instances" in intents:
        raw["network_instances"] = [
            dataclasses.asdict(i) for i in intents["network_instances"]
        ]

    if "protocols" in intents:
        raw["protocols"] = {}
        protocols = intents["protocols"]

        if "ospf" in protocols:
            raw["protocols"]["ospf"] = [dataclasses.asdict(i) for i in protocols["ospf"]]

        if "ntp" in protocols:
            # hydrate_intents wraps the single NTP instance in a 1-item list;
            # unwrap it back to the flat dict devices.yml expects.
            (ntp_intent,) = protocols["ntp"]
            raw["protocols"]["ntp"] = dataclasses.asdict(ntp_intent)

        if "snmp" in protocols:
            raw["protocols"]["snmp"] = [dataclasses.asdict(i) for i in protocols["snmp"]]

        # Pass through anything hydrate_intents preserved verbatim (plain
        # dicts/lists, not dataclasses -- nothing to asdict()).
        for key, value in protocols.items():
            if key not in KNOWN_PROTOCOL_KEYS:
                raw["protocols"][key] = value

    for key, value in intents.items():
        if key not in KNOWN_TOP_LEVEL_INTENT_KEYS:
            raw[key] = value

    return raw


def dehydrate_device(device: dict) -> dict:
    raw = dict(device)
    if "intents" in raw:
        raw["intents"] = dehydrate_intents(raw["intents"])
    return raw


# ---------------------------------------------------------------------------
# Load / save
#
# devices.yml is now sparse: it only has entries for hosts that have some
# configured intent, not every device (that list lives in inventory.yml,
# via credentials.all_hosts()). host is the join key between the two files.
# ---------------------------------------------------------------------------

def load_raw_devices() -> list[dict]:
    """Raw (un-hydrated) devices.yml entries -- host + intents only, no
    vendor/username (that's inventory.yml's job now)."""
    with open(DEVICES_YML, "r") as f:
        return yaml.safe_load(f) or []


def load_devices() -> list[dict]:
    """Every device in inventory.yml, each with intents hydrated into
    dataclasses -- empty ({}) for a device inventory.yml knows about but
    devices.yml doesn't have an entry for yet."""
    intents_by_host = {d["host"]: d.get("intents", {}) for d in load_raw_devices()}
    devices = []
    for host in credentials.all_hosts():
        raw_intents = intents_by_host.get(host, {})
        try:
            hydrated_intents = hydrate_intents(raw_intents)
        except (TypeError, KeyError) as exc:
            raise ValidationError(f"{host}: {exc}") from exc
        devices.append({
            "host": host,
            "vendor": credentials.vendor_for_host(host),
            "intents": hydrated_intents,
        })
    return devices


def load_device(host: str) -> dict:
    for device in load_devices():
        if device["host"] == host:
            return device
    raise KeyError(host)


def save_devices(devices: list[dict]) -> None:
    """
    devices: list of dicts, intents already hydrated into dataclasses
    (i.e. what load_devices() returns, after edits). Only host + intents
    are written to devices.yml -- vendor comes from inventory.yml and was
    never devices.yml's to store.
    """
    raw = [{"host": d["host"], "intents": dehydrate_intents(d.get("intents", {}))} for d in devices]
    with open(DEVICES_YML, "w") as f:
        yaml.safe_dump(raw, f, sort_keys=False)


def save_device(host: str, updated_intents: dict) -> None:
    """updated_intents: hydrated intents (dataclasses) for `host`. Creates a
    new devices.yml entry if this host has no intents configured yet --
    devices.yml is sparse by design, so "not there yet" isn't an error the
    way it would be for inventory.yml."""
    if host not in credentials.all_hosts():
        raise KeyError(host)
    devices = load_devices()
    for device in devices:
        if device["host"] == host:
            device["intents"] = updated_intents
            break
    save_devices(devices)


# ---------------------------------------------------------------------------
# Translation stage preview -- Intent -> Translation only, no transport call.
# ---------------------------------------------------------------------------

def preview_translation(host: str, payload_format: str = "xml") -> list[dict]:
    """
    Runs each intent through its translator and returns the rendered
    payload, WITHOUT calling transport.push_config. This is what the
    Translation stage inspector in the canvas shows -- side-effect-free
    by construction, so clicking around the GUI never touches a real device.
    """
    device = load_device(host)
    vendor = device["vendor"]
    translators = TRANSLATORS[vendor]
    intents = device.get("intents", {})
    results = []

    for ni in intents.get("network_instances", []):
        if "network_instance" in translators:
            payload = translators["network_instance"].translate(
                ni, payload_format=payload_format
            )
            results.append(_preview_entry("network_instances", ni, payload))

    for iface in intents.get("interfaces", []):
        key = "subinterface" if "subinterface" in translators else "interface"
        if key in translators:
            payload = translators[key].translate([iface], payload_format=payload_format)
            results.append(_preview_entry("interfaces", iface, payload))
        # SR Linux's orchestrator (orchestration/srlinux.py configure_interface)
        # pushes a SECOND payload per interface -- binding the new subinterface
        # to its network-instance -- via the separately registered "ni_interface"
        # translator. cEOS has no such translator registered, so this only
        # fires for vendors that actually do it during a real deploy.
        if "ni_interface" in translators:
            binding_payload = translators["ni_interface"].translate(
                iface, payload_format=payload_format
            )
            results.append(_preview_entry("interfaces_ni_binding", iface, binding_payload))

    protocols = intents.get("protocols", {})
    for ospf in protocols.get("ospf", []):
        if "ospf" in translators:
            payload = translators["ospf"].translate(ospf, payload_format=payload_format)
            results.append(_preview_entry("ospf", ospf, payload))

    for ntp in protocols.get("ntp", []):
        if "ntp" in translators:
            payload = translators["ntp"].translate(ntp, payload_format=payload_format)
            results.append(_preview_entry("ntp", ntp, payload))

    for snmp in protocols.get("snmp", []):
        if "snmp" in translators:
            payload = translators["snmp"].translate(snmp, payload_format=payload_format)
            results.append(_preview_entry("snmp", snmp, payload))

    return results


def _preview_entry(category: str, intent_obj: Any, payload: Any) -> dict:
    is_dataclass = dataclasses.is_dataclass(intent_obj)
    return {
        "category": category,
        "intent": dataclasses.asdict(intent_obj) if is_dataclass else intent_obj,
        "payload": payload if isinstance(payload, str) else payload,
        "payload_is_xml": isinstance(payload, str),
    }


# ---------------------------------------------------------------------------
# Deployment -- the real thing: Orchestration -> Translation -> Transport.
# ---------------------------------------------------------------------------

def run_deployment(host: str, transport_kind: str = "netconf", categories: set[str] | None = None) -> dict:
    """
    categories: optional set of intent categories to provision this run
    (e.g. {"snmp"}) -- lets the GUI push one new piece of configuration
    without re-pushing everything else already configured for the device.
    None (the default) provisions everything, matching prior behavior.
    """
    if transport_kind not in TRANSPORT_MAP:
        raise ValueError(f"Unknown transport '{transport_kind}', expected one of {list(TRANSPORT_MAP)}")

    device = load_device(host)
    vendor = device["vendor"]
    TransportClass = TRANSPORT_MAP[transport_kind]
    payload_format = PAYLOAD_FORMAT_MAP[transport_kind]

    log = io.StringIO()
    result = {"host": host, "vendor": vendor, "transport": transport_kind, "success": False}

    try:
        conn = credentials.resolve_credentials(host)
    except CredentialsError as exc:
        # Same treatment as any other deploy-time failure: a clean result
        # for the caller, not a stack trace -- but distinct enough (no log,
        # no vague "connection failed") that a missing .env entry doesn't
        # look like a device/network problem.
        result["error"] = str(exc)
        return result

    scoped_intents = filter_intents(device.get("intents", {}), categories)

    try:
        with contextlib.redirect_stdout(log):
            print(f"--- Using {transport_kind.upper()} transport ---")
            if transport_kind == "netconf":
                transport = TransportClass(host=host, username=conn.username, password=conn.password)
            else:
                transport = TransportClass(
                    host=host, username=conn.username, password=conn.password, vendor=vendor
                )
            orchestrator = ORCHESTRATORS[vendor](transport, TRANSLATORS[vendor])
            orchestrator.bootstrap()
            print("  \u2713 Bootstrap complete")
            orchestrator.provision(scoped_intents, payload_format=payload_format)
        result["success"] = True
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: this is a
        # user-triggered deploy against a live device; any failure (auth,
        # unreachable host, translator error) should come back as a result,
        # not a 500.
        result["error"] = f"{type(exc).__name__}: {exc}"

    result["log"] = log.getvalue()
    return result
