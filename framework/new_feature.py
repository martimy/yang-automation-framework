"""
Scaffolds the framework-side files for a new feature (intent dataclass,
translator stub per vendor, template stubs) and prints ready-to-paste
snippets for the handful of shared files that must be *edited* rather
than created (registry.py, orchestration/base.py, orchestration/<vendor>.py,
scope.py, deploy.py).

This deliberately only writes brand-new files. Shared files that already
have real content only get printed snippets to paste in by hand -- an
automated in-place edit to an existing multi-hundred-line file is exactly
the kind of thing that has bitten this project before (see the devices.yml
data-loss bug from an earlier automated save). Generating new files is
safe because they don't exist yet; there's nothing to lose.

This only covers the framework/ side. It does not touch gui/ at all --
follow docs/framework-developer-guide.md's "Extension Guide" checklist
for the GUI steps, and run gui/backend/check_consistency.py once you've
done them, to make sure the GUI agrees with what you build here.

Usage:
    python3 framework/new_feature.py bgp --location top-level --cardinality single
    python3 framework/new_feature.py bgp --location protocols --cardinality list --vendors srlinux

--location:
    top-level   -- a sibling of "protocols" in devices.yml, like snmp
                   (use this if the feature isn't a routing protocol)
    protocols   -- nested under devices.yml's "protocols" key, like ospf/ntp
                   (use this if it is one)

--cardinality:
    single      -- one instance per device, like snmp
    list        -- a device can have more than one, like ospf

--vendors: comma-separated, default "ceos,srlinux"
"""

import argparse
import re
import sys
from pathlib import Path

FRAMEWORK_DIR = Path(__file__).resolve().parent


def to_class_prefix(name: str) -> str:
    """bgp -> Bgp, static_route -> StaticRoute"""
    return "".join(part.capitalize() for part in name.split("_"))


def check_name(name: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        sys.exit(
            f"error: '{name}' should be a lowercase snake_case name, e.g. "
            "'bgp' or 'static_route' -- it's used as-is as the devices.yml "
            "key and the Python module/class name."
        )


def write_new_file(path: Path, content: str) -> None:
    if path.exists():
        sys.exit(
            f"error: {path} already exists -- refusing to overwrite. "
            "Remove it first if you really want to regenerate it."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"  created {path.relative_to(FRAMEWORK_DIR.parent)}")


# ---------------------------------------------------------------------------
# New-file templates
# ---------------------------------------------------------------------------

def intent_stub(name: str, class_name: str) -> str:
    return f'''"""
TODO: describe what {class_name} configures.
"""

from dataclasses import dataclass


@dataclass
class {class_name}:
    """
    TODO: replace these placeholder fields with the real ones this
    feature needs. Keep every field either required (no default) or
    Optional[...] with a sensible default -- see intent/snmp.py or
    intent/ntp.py for two worked examples.
    """

    # TODO: placeholder field, delete once you've added real ones
    enabled: bool = True
'''


def translator_stub(name: str, class_name: str, vendor: str, vendor_prefix: str) -> str:
    return f'''import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import xmltodict

from translation.base import BaseTranslator
from intent.{name} import {class_name}


class {vendor_prefix}{class_name.replace("Intent", "")}Translator(BaseTranslator):

    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            self.template_dir = Path(__file__).parent.parent / "templates" / "{vendor}"

    def _build_data_structure(self, intent: {class_name}) -> dict:
        # TODO: if {class_name} has nested dataclasses that need reshaping
        # for the template (see SrlinuxOspfTranslator for an example with
        # areas/interfaces), do it here. A flat dataclass can just asdict().
        return asdict(intent)

    def translate(
        self,
        intent: {class_name},
        payload_format: str = "xml",
    ) -> str | dict:
        data = self._build_data_structure(intent)
        if payload_format == "xml":
            return self._render_and_validate_xml(data, "{name}.xml.j2")
        elif payload_format == "json":
            return self._render_and_validate_json(data, "{name}.json.j2")
        else:
            raise ValueError(f"Unsupported format: {{payload_format}}")

    def _render_and_validate_xml(self, data: dict, template_file: str) -> str:
        template = self._load_template(template_file)
        rendered = template.render(data)
        xmltodict.parse(rendered)
        return rendered

    def _render_and_validate_json(self, data: dict, template_file: str) -> dict:
        template = self._load_template(template_file)
        rendered = template.render(data)
        return json.loads(rendered)
'''


def xml_template_stub(name: str) -> str:
    return (
        '<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">\n'
        f"  {{# TODO: fill in the real {name} payload, using this intent's\n"
        "     fields as Jinja variables (e.g. {{ enabled }}) -- see\n"
        "     translation/templates/srlinux/ntp.xml.j2 for a worked example\n"
        "     that includes a loop over a nested list. #}\n"
        "</config>\n"
    )


def json_template_stub(name: str) -> str:
    return f"{{# TODO: fill in the real {name} JSON payload #}}\n{{}}\n"


# ---------------------------------------------------------------------------
# Printed snippets for shared files (not auto-edited)
# ---------------------------------------------------------------------------

def print_snippet(title: str, path: str, body: str) -> None:
    print(f"\n--- {title} ({path}) ---")
    print(body.rstrip())


def hydrate_snippet(name: str, class_name: str, location: str, cardinality: str) -> str:
    if location == "top-level" and cardinality == "single":
        return f'''if "{name}" in raw_intents:
    new_intents["{name}"] = {class_name}(**raw_intents["{name}"])'''
    if location == "top-level" and cardinality == "list":
        return f'''if "{name}" in raw_intents:
    new_intents["{name}"] = [{class_name}(**d) for d in raw_intents["{name}"]]'''
    if location == "protocols" and cardinality == "single":
        return f'''if "{name}" in protocols:
    new_intents["protocols"]["{name}"] = {class_name}(**protocols["{name}"])'''
    return f'''if "{name}" in protocols:
    new_intents["protocols"]["{name}"] = [{class_name}(**d) for d in protocols["{name}"]]'''


def provision_snippet(name: str, location: str, cardinality: str) -> str:
    source = "intents" if location == "top-level" else 'protocols'
    if cardinality == "single":
        return f'''{name}_intent = {source}.get("{name}")
if {name}_intent:
    self.configure_{name}({name}_intent, payload_format=payload_format)'''
    return f'''for {name}_intent in {source}.get("{name}", []):
    self.configure_{name}({name}_intent, payload_format=payload_format)'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="snake_case feature name, e.g. 'bgp'")
    parser.add_argument("--location", choices=["top-level", "protocols"], required=True)
    parser.add_argument("--cardinality", choices=["single", "list"], required=True)
    parser.add_argument("--vendors", default="ceos,srlinux", help="comma-separated, default: ceos,srlinux")
    args = parser.parse_args()

    check_name(args.name)
    name = args.name
    class_name = to_class_prefix(name) + "Intent"
    vendors = [v.strip() for v in args.vendors.split(",") if v.strip()]

    print(f"Scaffolding '{name}' -- {args.location}, {args.cardinality}-instance, vendors: {', '.join(vendors)}\n")

    # 1. intent dataclass
    write_new_file(FRAMEWORK_DIR / "intent" / f"{name}.py", intent_stub(name, class_name))

    # 2. per-vendor translator + templates
    for vendor in vendors:
        vendor_prefix = to_class_prefix(vendor) if vendor != "srlinux" else "Srlinux"
        if vendor == "ceos":
            vendor_prefix = "Ceos"
        write_new_file(
            FRAMEWORK_DIR / "translation" / vendor / f"{name}.py",
            translator_stub(name, class_name, vendor, vendor_prefix),
        )
        write_new_file(
            FRAMEWORK_DIR / "translation" / "templates" / vendor / f"{name}.xml.j2",
            xml_template_stub(name),
        )
        write_new_file(
            FRAMEWORK_DIR / "translation" / "templates" / vendor / f"{name}.json.j2",
            json_template_stub(name),
        )

    print(
        "\nNew files created above are stubs -- fill in the TODOs (real "
        "fields, real translation logic, real templates)."
    )
    print(
        "\nThe files below already have real content, so nothing was "
        "edited automatically. Paste each snippet into the file named, "
        "near the existing entries it's meant to sit alongside:"
    )

    translator_class_stub = class_name.replace("Intent", "") + "Translator"
    registry_imports = "\n".join(
        f'from translation.{v}.{name} import '
        f'{("Ceos" if v == "ceos" else "Srlinux")}{translator_class_stub}'
        for v in vendors
    )
    registry_entries = "\n".join(
        f'    "{v}": {{\n        ...,\n        "{name}": '
        f'{("Ceos" if v == "ceos" else "Srlinux")}{translator_class_stub}(),\n    }},'
        for v in vendors
    )
    print_snippet(
        "1. registry.py -- add the import near the top, and one entry per "
        "vendor's TRANSLATORS dict",
        "framework/registry.py",
        registry_imports + "\n\n# ...inside TRANSLATORS:\n" + registry_entries,
    )

    print_snippet(
        "2. orchestration/base.py -- add this inside provision(), in "
        + ("the same phase as snmp/network_instances if this doesn't "
           "depend on interfaces, or after interfaces if it does"
           if args.location == "top-level"
           else "Phase 3 (Protocols), alongside ospf/ntp"),
        "framework/orchestration/base.py",
        provision_snippet(name, args.location, args.cardinality),
    )

    for vendor in vendors:
        print_snippet(
            f"3. orchestration/{vendor}.py -- add the import and this method "
            f"(omit entirely for a vendor that can't support {name})",
            f"framework/orchestration/{vendor}.py",
            f'from intent.{name} import {class_name}\n\n'
            f'def configure_{name}(self, intent: {class_name}, payload_format: str = "xml") -> bool:\n'
            f'    payload = self.translators["{name}"].translate(intent, payload_format=payload_format)\n'
            f'    return self.transport.push_config(payload)',
        )

    if args.location == "top-level":
        print_snippet(
            "4. scope.py -- add to TOP_LEVEL_CATEGORIES",
            "framework/scope.py",
            f'TOP_LEVEL_CATEGORIES = {{..., "{name}"}}',
        )
    else:
        print(
            "\n--- 4. scope.py -- no change needed (framework/scope.py) ---"
            f"\n'{name}' is nested under \"protocols\", and filter_intents() "
            "already passes through any key found there."
        )

    print_snippet(
        "5. deploy.py -- add inside hydrate_intents() (import goes near "
        "the other intent imports at the top)",
        "framework/deploy.py",
        f"from intent.{name} import {class_name}\n\n"
        + hydrate_snippet(name, class_name, args.location, args.cardinality),
    )

    example_yaml = (
        f"{name}:\n  enabled: true  # TODO: real fields"
        if args.cardinality == "single"
        else f"{name}:\n  - enabled: true  # TODO: real fields"
    )
    if args.location == "protocols":
        example_yaml = "protocols:\n  " + example_yaml.replace("\n", "\n  ")
    print_snippet(
        "6. devices.yml -- example block for a host that needs this "
        "(add real fields, not the placeholder)",
        "framework/devices.yml",
        example_yaml,
    )

    print(
        "\nThis script only covers framework/. For the GUI (pipeline.py, "
        "schema.py, index.html), follow the same checklist in "
        "docs/framework-developer-guide.md, then run:\n"
        "    python3 gui/backend/check_consistency.py\n"
        "to confirm the GUI agrees with what you just built."
    )


if __name__ == "__main__":
    main()
