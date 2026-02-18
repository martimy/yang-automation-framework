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
yang_course/
├── main.py              # Application entry point; drives the provisioning loop.
├── registry.py          # Glue logic; maps vendors to their specific components.
├── devices.yml          # Inventory and intent definitions (The "Source of Truth").
├── intent/              # Vendor-neutral data models for OSPF, NTP, Interfaces, etc.
├── orchestration/       # Vendor-specific workflow logic (Ceos vs. SR-Linux).
├── translation/         # Jinja2-based payload generation logic.
│   ├── ceos/            # Arista-specific translators.
│   ├── srlinux/         # Nokia-specific translators.
│   ├── common/          # Shared translators (e.g., OpenConfig NTP).
│   └── templates/       # The raw XML/JSON Jinja2 templates.
└── transport/           # NETCONF and gNMI protocol implementations.
```

---

## Key Workflow

1.  **Initialization**: `main.py` loads credentials from `.env` and device intents from `devices.yml`.
2.  **Registration**: `registry.py` provides the orchestrator and translators required for the specific vendor (e.g., `ceos` or `srlinux`).
3.  **Bootstrap**: The orchestrator performs one-time prerequisites (e.g., enabling `ip routing` on cEOS).
4.  **Sequential Provisioning**:
    -   `main.py` passes intents to the orchestrator.
    -   The orchestrator uses translators to generate the payload.
    -   The orchestrator pushes the payload via the transport layer.
5.  **Safe Delivery**: The `NetconfTransport` utilizes the **Candidate → Validate → Confirmed-Commit** sequence to ensure atomic and safe configuration changes.

---

## Extension Guide

-   **To add a new Feature (e.g., BGP)**:
    1.  Create `intent/bgp.py`.
    2.  Create translators in `translation/ceos/` and `translation/srlinux/`.
    3.  Register the translators in `registry.py`.
    4.  Update the `DeviceOrchestrator` base class and implementations with `configure_bgp()`.
-   **To add a new Transport**:
    1.  Implement a new class in `transport/` (e.g., `RestconfTransport`).
    2.  Update the transport map in `main.py`.

---

## Usage

The tool supports dynamic transport selection via CLI flags:

```bash
# Provision using NETCONF
python3 main.py --transport netconf

# Provision using gNMI
python3 main.py --transport gnmi
```
