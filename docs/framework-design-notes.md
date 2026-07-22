# Framework Design Notes

Notes on the multi-vendor behavior this framework was built to handle, and the
design decisions that follow from it.

## 1. The discovery-first workflow

Automation on an unfamiliar device starts with discovery, not coding:

1. **Retrieve capabilities** — check what models the device supports (e.g. `get_capabilities.py ceos | grep ospf`).
2. **Fetch schema** — download the exact YANG file from the device with `get-schema`.
3. **Visualize** — use `pyang -f tree` to understand the data hierarchy and types.
4. **Reverse-engineer** — configure via CLI, then run `get-config` to see the "truth" of the XML/JSON representation.

`pyang -f sample-xml-skeleton` is also useful for generating an initial XML skeleton for a translator template, which cuts down on manual transcription errors.

## 2. Vendor implementation differences

- **Arista cEOS (simple sequence)** — a single payload can configure an interface, its IP address, and its routing state together. It relies on a one-time "bootstrap" step to enable IP routing globally, and interfaces default to Layer 2 (the orchestrator has to handle the `no switchport` equivalent).
- **Nokia SR Linux (ordered dependencies)** — a more granular, object-oriented model. Every interface needs at least one subinterface, and configuring one end-to-end is a strict three-step sequence:
  1. Create the subinterface.
  2. Create or verify the network-instance.
  3. Bind the subinterface to the network-instance.

  Doing these out of order results in a commit error.

## 3. Model selection strategy

- Prefer standardized models — IETF (`ietf-interfaces`) and OpenConfig (`openconfig-if-ip`) — for common features like interfaces and IP addressing.
- Fall back to vendor-native models (e.g. `srl_nokia-ospf`) where the standard models are unsupported or insufficient for the platform's implementation.
- NTP is one of the few features where both vendors converge on the same model (`openconfig-system`), which makes it the most portable translator in the framework.

## 4. Intent-based design pattern

- Python dataclasses (`InterfaceIntent`, `OspfIntent`, `NetworkInstanceIntent`, etc.) define the desired state independently of any protocol.
- Jinja2 templates separate the structure of each YANG payload from the data that fills it.
- Vendor-specific "recipes" — the ordering logic above — live in orchestrator classes, one per vendor, keeping the main provisioning loop vendor-agnostic.

## 5. Toolchain

- `pyang` — schema visualization.
- `ncclient` — NETCONF transport.
- `pygnmi` / `gnmic` — gNMI transport and telemetry exploration.
- `containerlab` — the sandbox used to test these sequences safely before they reach production.

---

## Framework architecture

The `framework/` directory is a four-layer network automation engine for
managing Arista cEOS and Nokia SR Linux over NETCONF and gNMI.

| Layer | Directory | Responsibility |
|---|---|---|
| Intent | `intent/` | Vendor-neutral dataclasses describing desired state (`InterfaceIntent`, `OspfIntent`, `NtpIntent`, ...). |
| Orchestration | `orchestration/` | Vendor-specific sequencing (`CeosOrchestrator`, `SrlinuxOrchestrator`) — knows the dependency order described above. |
| Translation | `translation/` | Converts intents into vendor-specific payloads using Jinja2 templates (`translation/templates/`) — XML for NETCONF, JSON for gNMI. |
| Transport | `transport/` | Talks to the devices: `netconf.py` (via `ncclient`) and `gnmi.py` (via `pygnmi`). |

Supporting files:

- `deploy.py` — entry point; loads `devices.yml`, builds the intent objects, and drives the provisioning loop.
- `registry.py` — maps a vendor string (`"ceos"`, `"srlinux"`) to its translator and orchestrator classes.
- `devices.yml` — inventory plus the intended configuration (intents) for each device.

### YANG model support by feature

| Feature | Arista cEOS | Nokia SR Linux | Portability |
|---|---|---|---|
| Interfaces | OpenConfig (`openconfig-interfaces`) | Native (`urn:nokia.com:srlinux:chassis:interfaces`) | Low |
| IP addressing | OpenConfig (`openconfig-if-ip`) | Native (`urn:nokia.com:srlinux:chassis:interfaces`) | Low |
| OSPF | OpenConfig (`openconfig-ospf`) | Native (`srl_nokia-ospf`) | Low |
| NTP | OpenConfig (`openconfig-system`) | OpenConfig (`openconfig-system`) | High — shared translator |

### Transport consistency

Both vendors generally support the same YANG models regardless of transport, but the payload format changes: NETCONF carries XML, gNMI carries JSON-IETF (or Python dictionaries in this codebase). Where both vendors share a standard model — NTP via OpenConfig System — `CeosNtpTranslator` and `SrlinuxNtpTranslator` end up nearly identical in logic (they differ only in which template directory they point to), which is the clearest illustration in this codebase of what "portability" actually buys you: less translator logic to write and maintain per vendor, even though each vendor still gets its own translator class.

### Safe delivery

The NETCONF transport uses a **candidate → validate → confirmed-commit** sequence so that changes can be validated before they're committed, and rolled back automatically if a confirming commit never arrives.
