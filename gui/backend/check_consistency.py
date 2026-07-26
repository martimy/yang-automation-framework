"""
Checks that the GUI backend and the framework agree on the shape of every
intent category -- catches the class of bug SNMP had: registry.py,
scope.py, deploy.py, and the GUI's pipeline.py/schema.py each hold their
own opinion about which categories exist, whether each is top-level or
nested under "protocols", and whether it's single-instance or a list.
Nothing enforces that they agree; they just silently drifted for SNMP
until it was caught by hand.

This does not replace testing against real devices -- it only checks that
the *shapes* declared in different files match each other. Run it after
adding or changing any intent category, and ideally wire it into CI:

    python3 gui/backend/check_consistency.py

Exits 0 if everything agrees, 1 (with an explanation of what to fix and
where) if it finds a mismatch.
"""

import sys

import framework_bridge  # noqa: F401  (side effect: puts framework/ on sys.path)
import scope
from registry import TRANSLATORS
from services import pipeline as p
from services import schema

# Translator keys registry.py is known to use today, and which top-level
# intent category (if any) each one implies support for. Update this when
# you add a new translator key:
#   - maps to an existing or new category -> add the mapping below
#   - a secondary/structural translator with no top-level category of its
#     own (like "ni_interface", which derives from network_instances /
#     interfaces rather than being deployed from its own intent) -> add the
#     key to _STRUCTURAL_TRANSLATOR_KEYS instead
_TRANSLATOR_KEY_TO_CATEGORY = {
    "interface": "interfaces",
    "subinterface": "interfaces",
    "network_instance": "network_instances",
    "ospf": "ospf",
    "ntp": "ntp",
    "snmp": "snmp",
}
_STRUCTURAL_TRANSLATOR_KEYS = {"ni_interface"}


def check_top_level_agreement(errors: list[str]) -> None:
    """scope.py and pipeline.py must agree on which categories are
    top-level (a sibling of "protocols") vs. nested under "protocols"."""
    scope_top = set(scope.TOP_LEVEL_CATEGORIES)
    pipeline_top = set(p.KNOWN_TOP_LEVEL_INTENT_KEYS) - {"protocols"}
    if scope_top != pipeline_top:
        errors.append(
            "scope.TOP_LEVEL_CATEGORIES and pipeline.KNOWN_TOP_LEVEL_INTENT_KEYS "
            f"disagree: scope.py has {sorted(scope_top)}, pipeline.py has "
            f"{sorted(pipeline_top)}. A category top-level in one but not the "
            "other means the GUI hydrates/dehydrates or scopes it differently "
            "than deploy.py does. Update framework/scope.py's "
            "TOP_LEVEL_CATEGORIES and/or gui/backend/services/pipeline.py's "
            "KNOWN_TOP_LEVEL_INTENT_KEYS so they match."
        )


def check_category_set_agreement(errors: list[str]) -> None:
    """schema.py's INTENT_CLASSES (what the Intent form can render) must
    cover exactly the categories pipeline.py knows how to hydrate."""
    pipeline_categories = (set(p.KNOWN_TOP_LEVEL_INTENT_KEYS) - {"protocols"}) | set(
        p.KNOWN_PROTOCOL_KEYS
    )
    schema_categories = set(schema.INTENT_CLASSES.keys())
    if pipeline_categories != schema_categories:
        missing_from_schema = pipeline_categories - schema_categories
        missing_from_pipeline = schema_categories - pipeline_categories
        detail = []
        if missing_from_schema:
            detail.append(
                f"pipeline.py hydrates {sorted(missing_from_schema)} but "
                "schema.py's INTENT_CLASSES has no entry for it -- the Intent "
                "form won't offer fields for it."
            )
        if missing_from_pipeline:
            detail.append(
                f"schema.py's INTENT_CLASSES has {sorted(missing_from_pipeline)} "
                "but pipeline.py never hydrates/dehydrates it -- editing it "
                "through the form won't save correctly."
            )
        errors.append(" ".join(detail))


def check_translator_keys_recognized(errors: list[str]) -> None:
    """Every translator key registered in registry.py, for any vendor,
    should be one this checker (and schema.py) knows about. A brand-new
    key showing up here almost always means a new feature was registered
    in registry.py but the rest of the GUI wiring wasn't updated to match."""
    known = set(_TRANSLATOR_KEY_TO_CATEGORY) | _STRUCTURAL_TRANSLATOR_KEYS
    all_keys = {key for vendor_map in TRANSLATORS.values() for key in vendor_map}
    unknown = all_keys - known
    if unknown:
        errors.append(
            f"registry.py has translator key(s) {sorted(unknown)} that this "
            "checker doesn't recognize. If this is a new feature: add it to "
            "_TRANSLATOR_KEY_TO_CATEGORY at the top of this file if it "
            "represents its own top-level intent category (and make sure "
            "schema.py's supported_intent_categories() checks for it too), "
            "or to _STRUCTURAL_TRANSLATOR_KEYS if it's a secondary payload "
            "like ni_interface with no top-level category of its own."
        )


def check_supported_categories_match_registry(errors: list[str]) -> None:
    """schema.supported_intent_categories(vendor) is a hand-written
    if-chain over registry.TRANSLATORS -- easy to register a new
    translator in registry.py and forget to add the matching line there.
    Recompute independently from _TRANSLATOR_KEY_TO_CATEGORY and compare."""
    for vendor, translator_map in TRANSLATORS.items():
        expected = {
            _TRANSLATOR_KEY_TO_CATEGORY[key]
            for key in translator_map
            if key in _TRANSLATOR_KEY_TO_CATEGORY
        }
        actual = set(schema.supported_intent_categories(vendor))
        if expected != actual:
            errors.append(
                f"'{vendor}': registry.py's registered translators imply support "
                f"for {sorted(expected)}, but "
                f"schema.supported_intent_categories('{vendor}') returns "
                f"{sorted(actual)}. schema.py's if-chain is missing a category -- "
                "the GUI would silently hide (or wrongly show) it for this vendor."
            )


def main() -> int:
    errors: list[str] = []
    check_top_level_agreement(errors)
    check_category_set_agreement(errors)
    check_translator_keys_recognized(errors)
    check_supported_categories_match_registry(errors)

    if errors:
        print(f"FAILED -- {len(errors)} consistency issue(s) found:\n")
        for i, msg in enumerate(errors, 1):
            print(f"{i}. {msg}\n")
        return 1

    print("OK -- framework and GUI agree on every intent category's shape.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
