"""
Deployment scope: select which categories of a device's configured intents
to actually provision this run.

orchestration/base.py's provision() already does intents.get("ospf", []),
intents.get("snmp", []), etc. for every phase -- it silently skips whatever
isn't present. That means provisioning is already safe to call with a
partial intents dict; nothing there needed to change. What was missing was
a way to build that partial dict in the first place, so that adding one
new category (e.g. snmp) doesn't force re-pushing everything else already
configured for a device.

Category names match what devices.yml / the GUI use: "interfaces" and
"network_instances" are top-level; everything else ("ospf", "ntp", "snmp",
...) lives under "protocols". This module doesn't hardcode that list --
it filters whatever protocol keys happen to be present, so a newly added
protocol type works here with no changes.
"""

TOP_LEVEL_CATEGORIES = {"interfaces", "network_instances", "snmp"}


def filter_intents(intents: dict, categories: set[str] | None) -> dict:
    """
    Keep only the requested categories from a hydrated intents dict.
    categories=None means no filtering -- returns intents unchanged
    (today's full-deploy behavior, and the default everywhere this is used).
    """
    if categories is None:
        return intents

    filtered: dict = {}

    for key in TOP_LEVEL_CATEGORIES:
        if key in categories and key in intents:
            filtered[key] = intents[key]

    protocols = intents.get("protocols", {})
    filtered_protocols = {k: v for k, v in protocols.items() if k in categories}
    if filtered_protocols:
        filtered["protocols"] = filtered_protocols

    return filtered
