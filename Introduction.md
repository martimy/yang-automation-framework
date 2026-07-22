# Introduction

Model-driven network automation is often presented as a clean and standardized workflow built on YANG models and modern APIs such as NETCONF and gNMI. In practice, however, engineers quickly discover that real environments are far less uniform. Different vendors support different combinations of IETF, OpenConfig, and vendor-native models, and even when the same feature exists across platforms, the data structures and transport mechanisms can vary significantly.

This tutorial focuses on that reality.

The workflow demonstrated here builds on a well-established architectural pattern for intent-based networking: the separation of intent, translation, and transport layers. This pattern appears in various forms across both academic literature and commercial platforms — from the intent-based networking architectures surveyed by Leivadeas and Falkner [1] to the service modeling approaches used in systems like Cisco NSO and Nokia NSP. However, experience implementing such patterns in multi-vendor environments reveals a critical gap: these architectures typically assume that translation can happen independently per service, when in practice, configuration dependencies often require careful sequencing.

**This tutorial addresses that gap directly.** Between the intent and translation layers, it introduces a **vendor-specific orchestration layer** that resolves prerequisite dependencies and ensures operations execute in the correct order. This orchestration layer solves a practical problem that becomes visible only when moving from single-vendor labs to heterogeneous production environments: interfaces must exist before IP addresses can be assigned, network instances must be created before they can be referenced by routing protocols, and NTP servers require reachable infrastructure. Commercial platforms handle this through proprietary dependency engines or imperative workflow scripts; academic treatments often abstract it away entirely. This reference implementation makes these dependencies explicit and manageable through one orchestrator class per vendor.

Built around a small multi-vendor lab consisting of devices from Nokia and Arista Networks (deployed using containerlab for reproducibility), the tutorial demonstrates configuration using a combination of vendor-native models, OpenConfig models, and IETF standards. Both NETCONF and gNMI transports are used to illustrate transport abstraction within a structured pipeline.

The layered workflow separates four distinct concerns:

- **Intent layer** – Vendor-independent service definitions expressed in YAML
- **Orchestration layer** – Per-vendor dependency resolution and operation sequencing
- **Translation layer** – Per-vendor model mapping implemented using Python dataclasses
- **Transport layer** – Protocol abstraction supporting NETCONF (via `ncclient`) and gNMI (via `pygnmi`)

Intent definitions flow into vendor-specific orchestrators, which determine the correct order of operations and invoke the appropriate translators to generate vendor-specific YANG payloads (XML for NETCONF, JSON for gNMI). These payloads are then passed to a common transport interface. This approach keeps service logic independent of vendor models, protocol mechanics, *and* the dependency relationships that emerge in multi-vendor environments.

The tutorial intentionally demonstrates multiple model sources within the same workflow. Interface configuration (including addressing and descriptions), OSPF across multiple areas and interfaces, NTP, and network-instance constructs are implemented end-to-end. The orchestration layer manages dependencies between these features — for example, ensuring OSPF processes reference only interfaces that have already been configured, and that network instances exist before they are referenced in routing contexts.

This work originated from a practical challenge that many engineers encounter when moving from CLI-driven workflows to model-driven automation: discovering which YANG models are actually usable on a device, translating those models into valid configuration payloads, *and* determining the correct order to apply them when dependencies cross service boundaries. By making the orchestration layer explicit and vendor-specific, this reference implementation exposes an aspect of production automation that is often hidden in commercial platforms or simplified away in academic treatments.

For educators teaching network automation, or for practitioners transitioning from protocol-level scripting toward architectural thinking, this tutorial provides a lightweight reference implementation that shows how intent-based systems handle configuration dependencies — without the opacity of commercial orchestrators or the oversimplification of purely theoretical models.

## Reference

[1] A. Leivadeas and M. Falkner, "A Survey on Intent-Based Networking," *IEEE Communications Surveys & Tutorials*, vol. 25, no. 1, pp. 625-655, 2023.
