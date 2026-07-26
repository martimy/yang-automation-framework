# YANG Provisioning Tool — Developer Guide

This framework is a modular, model-driven network automation tool designed to manage multi-vendor network devices (Arista cEOS and Nokia SR-Linux) using YANG-based APIs (NETCONF and gNMI). It transitions from "scripted CLI" to structured data management.

## Core Architecture: The Four-Layer Model

The system is built on a four-layer architecture that separates the *intent* (what you want) from the *implementation* (how it's delivered).

1.  **Intent Layer (`intent/`):**
    -   **Responsibility**: Defines the desired state in a vendor-neutral way.
    -   **Implementation**: Python `dataclasses` (e.g., `InterfaceIntent`, `OspfIntent`, `NtpIntent`).
    -   **Benefit**: Human-readable and agnostic of transport or vendor specifics.

2.  **Orchestration Layer (`orchestration/`):**
    -   **Responsibility**: Manages the *recipe* or sequence of operations for each vendor.
    -   **Implementation**: Vendor-specific classes (e.g., `SrlinuxOrchestrator`) that inherit from a `DeviceOrchestrator` base.
    -   **Feature**: Handles "Type 2" differences (dependencies). For example, it ensures SR-Linux subinterfaces are created before being bound to a network-instance.

3.  **Translation Layer (`translation/`):**
    -   **Responsibility**: Maps Intent objects to specific YANG models (OpenConfig, IETF, or Native).
    -   **Implementation**: Classes that use **Jinja2 templates** to render intents into XML or JSON.
    -   **Feature**: Handles "Type 1" differences (same feature, different YANG path).

4.  **Transport Layer (`transport/`):**
    -   **Responsibility**: Manages the "wire" communication.
    -   **Implementation**: `NetconfTransport` (via `ncclient`) and `GnmiTransport` (via `pygnmi`).
    -   **Feature**: Abstracts the protocol, allowing the same intent to be pushed via NETCONF or gNMI.

---

## Directory Structure

```text
framework/
├── deploy.py            # Application entry point; drives the provisioning loop.
├── registry.py          # Glue logic; maps vendors to their specific components.
├── credentials.py        # Resolves each host's username/password from inventory.yml + .env; fails loudly, no hardcoded fallback.
├── scope.py              # filter_intents() -- lets a deploy target only some intent categories (--categories).
├── inventory.yml         # Device inventory: which hosts exist, their vendor, and how to connect (The "Source of Truth" for identity/credentials).
├── devices.yml           # Intent definitions only, keyed by host (The "Source of Truth" for desired configuration).
├── .env.example          # Template for CEOS_PASSWORD / SRL_PASSWORD — copy to .env. inventory.yml says which variable each host uses.
├── intent/              # Vendor-neutral data models for OSPF, NTP, Interfaces, etc.
├── orchestration/       # Vendor-specific workflow logic (Ceos vs. SR-Linux).
├── translation/         # Jinja2-based payload generation logic.
│   ├── ceos/            # Arista-specific translators.
│   ├── srlinux/         # Nokia-specific translators.
│   └── templates/       # The raw XML/JSON Jinja2 templates.
└── transport/           # NETCONF and gNMI protocol implementations.
```

---

## Key Workflow

1.  **Initialization**: `deploy.py` reads `devices.yml` for intents and, for
    each targeted host, resolves credentials via `credentials.py` (vendor
    defaults + host overrides from `inventory.yml`, password from `.env`).
    `--host` and `--categories` (via `scope.py`'s `filter_intents()`)
    optionally narrow this to one device and/or a subset of its intents.
2.  **Registration**: `registry.py` provides the orchestrator and translators required for the specific vendor (e.g., `ceos` or `srlinux`).
3.  **Bootstrap**: The orchestrator performs one-time prerequisites (e.g., enabling `ip routing` on cEOS).
4.  **Sequential Provisioning**:
    -   `deploy.py` passes (optionally filtered) intents to the orchestrator.
    -   The orchestrator uses translators to generate the payload.
    -   The orchestrator pushes the payload via the transport layer.
5.  **Safe Delivery**: `NetconfTransport` uses the **Candidate → Validate →
    Confirmed-Commit** sequence for atomic, safe configuration changes, and
    discards the candidate datastore if any step fails — otherwise a failed
    edit (e.g. a non-existent interface) would silently poison every
    subsequent deploy to that device, NETCONF or not.

---

## Extension Guide

Adding a new feature touches multiple files across every layer, by design
(that's what keeps vendor/transport differences isolated) — but it's easy
to miss a step, or to get an early decision wrong and have the framework
and GUI silently disagree. This is the order SNMP was added in, including
the two decisions that are easy to get wrong on a first pass, and the
consequence of getting them wrong.

### Decide two things before writing any code

1.  **Where does it live in `devices.yml`?**
    -   Under `protocols:` (alongside `ospf`, `ntp`) if it *is* a routing
        protocol.
    -   As a top-level sibling of `protocols:` if it isn't — e.g. `snmp`
        (`ntp` may move here too some day; see the comment in
        `orchestration/base.py`'s `provision()`).
2.  **Single instance per device, or a list?**
    -   `ntp`, `snmp`: one per device — a plain dict/dataclass.
    -   `ospf`: a device can have more than one — a list.

Get either of these wrong and the framework and the GUI can end up
disagreeing about the shape without either side raising an error. That's
exactly what happened the first time SNMP was wired up: the GUI treated it
as a list nested under `protocols`, while `devices.yml`/`deploy.py`/
`scope.py` treated it as a single top-level dict — so a real `deploy.py`
run worked, but deploying the same device from the GUI silently did
nothing (`orchestrator.provision()` never found `intents["snmp"]`), and
the GUI's own preview showed no payload at all.

### Checklist (example: adding `bgp`, top-level and single-instance)

**Framework — required for the CLI to work:**
1.  `intent/bgp.py` — new `BgpIntent` dataclass.
2.  `translation/<vendor>/bgp.py` — one translator class per vendor that
    supports it.
3.  `translation/templates/<vendor>/bgp.xml.j2` + `bgp.json.j2` — payload
    templates.
4.  `registry.py` — register the translator(s) in `TRANSLATORS[vendor]`.
5.  `orchestration/base.py` — add the `configure_bgp()` hook and call it
    from `provision()` in the right phase.
6.  `orchestration/<vendor>.py` — implement `configure_bgp()` for each
    vendor that supports it (omit it entirely for a vendor that can't
    configure this via YANG — see how `orchestration/ceos.py` has no
    `configure_snmp()`).
7.  `scope.py` — add `"bgp"` to `TOP_LEVEL_CATEGORIES` if it's top-level
    (a `protocols`-nested category needs no change here — `filter_intents()`
    already passes through any key under `protocols`).
8.  `deploy.py` — hydrate `bgp` from raw YAML in `hydrate_intents()`.
9.  `devices.yml` — add `bgp:` blocks to the hosts that need it.

**GUI — required so it matches the CLI instead of silently drifting:**
10. `gui/backend/services/pipeline.py` — hydrate/dehydrate `bgp` the same
    way as step 8 (`KNOWN_TOP_LEVEL_INTENT_KEYS` / `KNOWN_PROTOCOL_KEYS`),
    and add it to `preview_translation()`.
11. `gui/backend/services/schema.py` — add `"bgp": BgpIntent` to
    `INTENT_CLASSES`; extend `supported_intent_categories()` if it needs
    vendor filtering beyond what `registry.py` already implies.
12. `gui/frontend/index.html` — if single-instance, add a form block
    mirroring `ntp`'s (or `snmp`'s); if list-shaped, add `"bgp"` to
    `listCategories`.

Steps 10–12 never change how a real deploy behaves — `deploy.py` doesn't
import anything from `gui/` — but skipping them means the GUI's
preview/form/save silently diverges from what the CLI actually does, the
way SNMP's did until it was caught and fixed.

-   **To add a new Transport**:
    1.  Implement a new class in `transport/` (e.g., `RestconfTransport`).
    2.  Update the transport map in `deploy.py`.

---

## GUI

`gui/` is a second consumer of this framework — a local web app, not a
parallel implementation. Its backend (`gui/backend/`) puts `framework/` on
`sys.path` (`gui/backend/framework_bridge.py`) and imports `intent.*`,
`orchestration.*`, `translation.*`, `transport.*`, `registry`, `credentials`,
and `scope` exactly the way `deploy.py` does, so there's one implementation
of what an intent means (and one implementation of credential resolution
and deployment scoping), not two. The GUI's Deploy button resolves
credentials via `credentials.py` and supports the same `--categories`-style
scoping as `deploy.py`, through a checkbox list on the Transport stage.

Two things worth knowing if you're extending the framework and want the GUI
to stay accurate rather than silently stale:

- **The GUI derives everything from `registry.py` and `intent/*.py`, not by
  scanning `framework/` for files.** A new intent dataclass, translator, or
  orchestrator method only appears in the GUI once it's wired into
  `registry.py` (for the Intent form and vendor-support checks) and, for
  the Translation-stage preview specifically, once there's a matching call
  in `gui/backend/services/pipeline.py`'s `preview_translation()` — this
  needs to mirror whatever the vendor's `orchestration/<vendor>.py` does,
  including secondary payloads like SR Linux's `ni_interface` binding
  alongside `subinterface`. Following the "To add a new Feature" steps
  above and registering in `registry.py` is what makes this automatic for
  the Intent form and vendor filtering; the translation preview needs the
  one extra step by hand.
- **Anything not wired into `registry.py` is preserved, not silently
  dropped.** If `devices.yml` has a key the framework has no
  dataclass/translator for, `hydrate_intents()`/`dehydrate_intents()` in
  `gui/backend/services/pipeline.py` round-trip it byte-for-byte and the
  API surfaces it as a warning, rather than the GUI eating it on save.

See [`gui/README.md`](../gui/README.md) for how to run it, what each
pipeline stage shows, and current limitations.

---

## Usage

The tool supports dynamic transport selection via CLI flags:

```bash
# Provision using NETCONF
python3 deploy.py --transport netconf

# Provision using gNMI
python3 deploy.py --transport gnmi
```
