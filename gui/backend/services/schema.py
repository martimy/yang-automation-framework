"""
Generic dataclass -> form-schema introspection.

The framework's intents (framework/intent/*.py) are plain dataclasses.
Instead of hand-writing a form definition per intent type -- which drifts
the moment someone adds a field in the framework -- we introspect them at
request time with dataclasses.fields() and typing.get_type_hints().

This also reads registry.TRANSLATORS to answer "which intent types does
this vendor actually support", e.g. cEOS has no network_instance /
ni_interface translator, so the GUI shouldn't offer those fields for a
cEOS device (see InterfaceIntent's own docstring: "SR-Linux specific --
ignored by cEOS orchestrator").
"""

import dataclasses
import typing
from typing import Any

import framework_bridge  # noqa: F401  (side effect: puts framework/ on sys.path)

from intent.interface import InterfaceIntent
from intent.network_instance import NetworkInstanceIntent
from intent.ospf import OspfIntent, OspfAreaIntent, OspfInterfaceIntent
from intent.ntp import NtpIntent, NtpServerIntent
from intent.snmp import SnmpIntent
from registry import TRANSLATORS

# Intent dataclasses actually wired into deploy.py's hydration path today.
# (intent/routing.py exists in the framework but is dead code -- unregistered
# in registry.py and unreferenced by any orchestrator. Left out on purpose;
# see the README note in this GUI's own docs. intent/ni_interface.py, which
# used to be in the same boat, has since been removed from the framework.)
INTENT_CLASSES: dict[str, type] = {
    "interfaces": InterfaceIntent,
    "network_instances": NetworkInstanceIntent,
    "ospf": OspfIntent,
    "ntp": NtpIntent,
    "snmp": SnmpIntent,
}

# Nested dataclasses referenced by the top-level ones above, needed so the
# recursive schema builder can expand them too.
_NESTED_HINT_MODULES = {
    OspfAreaIntent,
    OspfInterfaceIntent,
    NtpServerIntent,
}


def _is_dataclass_type(tp: Any) -> bool:
    return dataclasses.is_dataclass(tp)


def _unwrap_list(tp: Any):
    """Return the element type if tp is List[X] / list[X], else None."""
    origin = typing.get_origin(tp)
    if origin in (list, typing.List):
        args = typing.get_args(tp)
        return args[0] if args else None
    return None


def dataclass_to_schema(cls: type, _seen: set | None = None) -> dict:
    """
    Turn a dataclass into a JSON-schema-ish dict the frontend can render
    a form from:

    {
      "type": "object",
      "fields": [
        {"name": "name", "type": "str", "required": true, "default": null},
        {"name": "areas", "type": "list", "items": {...nested schema...}},
        ...
      ]
    }
    """
    _seen = _seen or set()
    if cls in _seen:
        # Defensive -- none of today's intents are self-referential, but
        # don't hang if that ever changes.
        return {"type": "object", "fields": [], "recursive": True}
    _seen = _seen | {cls}

    hints = typing.get_type_hints(cls)
    fields = []
    for f in dataclasses.fields(cls):
        tp = hints.get(f.name, f.type)
        entry: dict[str, Any] = {"name": f.name, "required": f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING}

        list_item = _unwrap_list(tp)
        if list_item is not None and _is_dataclass_type(list_item):
            entry["type"] = "list"
            entry["items"] = dataclass_to_schema(list_item, _seen)
        elif _is_dataclass_type(tp):
            entry["type"] = "object"
            entry["object"] = dataclass_to_schema(tp, _seen)
        else:
            entry["type"] = getattr(tp, "__name__", str(tp))
            if f.default is not dataclasses.MISSING:
                entry["default"] = f.default

        fields.append(entry)

    return {"type": "object", "fields": fields}


def full_intent_schema() -> dict:
    """Schema for every top-level intent type, keyed the way devices.yml keys them."""
    return {key: dataclass_to_schema(cls) for key, cls in INTENT_CLASSES.items()}


def supported_intent_categories(vendor: str) -> list[str]:
    """
    Which top-level intent categories (interfaces / network_instances /
    ospf / ntp / snmp) make sense to show for this vendor, derived from
    which translators registry.py actually registers for it.

    "snmp" is a top-level category, not a "protocols" one (see
    framework/devices.yml and framework/scope.py -- SNMP isn't a routing
    protocol). It appears here for "srlinux" now that registry.py registers
    SrlinuxSnmpTranslator; cEOS has no snmp translator, since SNMP can't be
    configured via YANG on cEOS, so it's correctly absent for that vendor.
    """
    translator_keys = set(TRANSLATORS.get(vendor, {}).keys())
    supported = []
    if "interface" in translator_keys or "subinterface" in translator_keys:
        supported.append("interfaces")
    if "network_instance" in translator_keys:
        supported.append("network_instances")
    if "ospf" in translator_keys:
        supported.append("ospf")
    if "ntp" in translator_keys:
        supported.append("ntp")
    if "snmp" in translator_keys:
        supported.append("snmp")
    return supported


def known_vendors() -> list[str]:
    return list(TRANSLATORS.keys())
