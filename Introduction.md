# Introduction

Model-driven network automation is often presented as a clean and standardized workflow built on YANG models and modern APIs such as NETCONF and gNMI. In practice, however, engineers quickly discover that real environments are far less uniform. Different vendors support different combinations of IETF, OpenConfig, and vendor-native models, and even when the same feature exists across platforms, the data structures and transport mechanisms can vary significantly.

This tutorial focuses on that reality.

The workflow demonstrated here is built around a small multi-vendor lab consisting of devices from Nokia and Arista Networks, deployed using containerlab for reproducibility. Across these platforms, configuration is implemented using a combination of vendor-native models, OpenConfig models, and standards defined by the Internet Engineering Task Force. Both NETCONF and gNMI transports are used, not because the devices require it, but to demonstrate transport abstraction as part of a structured automation pipeline.

Rather than treating automation as a collection of protocol scripts, this tutorial introduces a layered workflow that separates intent, translation, and transport:

•	Intent layer – Vendor-independent service definitions expressed in YAML  
•	Translation layer – Per-vendor model mapping implemented using Python dataclasses  
•	Transport layer – Protocol abstraction supporting NETCONF (via ncclient) and gNMI (via pygnmi)  

Intent definitions are converted into vendor-specific YANG payloads (XML for NETCONF and JSON for gNMI), which are then passed into a common transport interface. This approach keeps service logic independent of both vendor models and protocol mechanics.
The tutorial intentionally demonstrates multiple model sources within the same workflow. Interface configuration (including addressing and descriptions), OSPF across multiple areas and interfaces, NTP, and network-instance constructs are implemented end-to-end. The code structure is designed to be easily extended to additional protocols, emphasizing architectural scalability rather than feature breadth.
This work originated from a practical challenge that many engineers encounter when moving from CLI-driven workflows to model-driven automation: discovering which YANG models are actually usable on a device and translating those models into valid configuration payloads. The workflow presented here formalizes that learning process into a repeatable structure suitable for multi-vendor environments.
If you are transitioning from protocol-level scripting toward architecture-driven automation—or looking for a practical way to combine IETF, OpenConfig, and vendor-native models within a single pipeline—this tutorial provides a minimal but extensible reference implementation.


---

Ah, this is a significant and genuinely interesting addition! The orchestration layer addressing dependency resolution is a substantial practical contribution that distinguishes your work from both academic treatments and commercial platforms. Let me revise the introduction to highlight this originality while maintaining proper context:

---

# Introduction

Model-driven network automation is often presented as a clean and standardized workflow built on YANG models and modern APIs such as NETCONF and gNMI. In practice, however, engineers quickly discover that real environments are far less uniform. Different vendors support different combinations of IETF, OpenConfig, and vendor-native models, and even when the same feature exists across platforms, the data structures and transport mechanisms can vary significantly.

This tutorial focuses on that reality.

The workflow demonstrated here builds on a well-established architectural pattern for intent-based networking: the separation of intent, translation, and transport layers. This pattern appears in various forms across both academic literature and commercial platforms—from the three-layer IBN architectures surveyed by Cao et al. [1] to the service modeling approaches used in systems like Cisco NSO and Nokia NSP. However, experience implementing such patterns in multi-vendor environments reveals a critical gap: these architectures typically assume that translation can happen independently per service, when in practice, configuration dependencies often require careful sequencing.

**Our contribution addresses this gap directly.** Between the intent and translation layers, we introduce a **vendor-specific orchestration layer** that resolves prerequisite dependencies and ensures operations execute in the correct order. This orchestration layer solves a practical problem that becomes visible only when moving from single-vendor labs to heterogeneous production environments: interfaces must exist before IP addresses can be assigned, network instances must be created before they can be referenced by routing protocols, and NTP servers require reachable infrastructure. Commercial platforms handle this through proprietary dependency engines or imperative workflow scripts; academic treatments often abstract it away entirely. Our approach makes these dependencies explicit and manageable through one orchestrator class per vendor.

Built around a small multi-vendor lab consisting of devices from Nokia and Arista Networks (deployed using containerlab for reproducibility), the tutorial demonstrates configuration using a combination of vendor-native models, OpenConfig models, and IETF standards. Both NETCONF and gNMI transports are used to illustrate transport abstraction within a structured pipeline.

The layered workflow separates four distinct concerns:

• Intent layer – Vendor-independent service definitions expressed in YAML  
• Orchestration layer – Per-vendor dependency resolution and operation sequencing  
• Translation layer – Per-vendor model mapping implemented using Python dataclasses  
• Transport layer – Protocol abstraction supporting NETCONF (via ncclient) and gNMI (via pygnmi)  

Intent definitions flow into vendor-specific orchestrators, which determine the correct order of operations and invoke the appropriate translators to generate vendor-specific YANG payloads (XML for NETCONF, JSON for gNMI). These payloads are then passed to a common transport interface. This approach keeps service logic independent of vendor models, protocol mechanics, *and* the complex dependency relationships that emerge in multi-vendor environments.

The tutorial intentionally demonstrates multiple model sources within the same workflow. Interface configuration (including addressing and descriptions), OSPF across multiple areas and interfaces, NTP, and network-instance constructs are implemented end-to-end. The orchestrator layer manages dependencies between these features—for example, ensuring OSPF processes reference only interfaces that have already been configured, and that network instances exist before they are referenced in routing contexts.

This work originated from a practical challenge that many engineers encounter when moving from CLI-driven workflows to model-driven automation: discovering which YANG models are actually usable on a device, translating those models into valid configuration payloads, *and* determining the correct order to apply them when dependencies cross service boundaries. By making the orchestration layer explicit and vendor-specific, our reference implementation exposes a critical aspect of production automation that is often hidden in commercial platforms or ignored in academic treatments.

For educators teaching network automation, or for practitioners transitioning from protocol-level scripting toward architectural thinking, this tutorial provides a lightweight reference implementation that reveals how intent-based systems handle the messy reality of configuration dependencies—without the opacity of commercial orchestrators or the oversimplification of purely theoretical models.

**References:**

[1] Cao, et al. "Intent-Based Networking—A Comprehensive Survey." *IEEE Communications Surveys & Tutorials*, 2025.

[2] Alcock, et al. "SWIFT: An Ontology-Based Intent Translation Framework." *Lancaster University Technical Report*, 2025.

[3] Angi, et al. "NAIL: Intent-Driven Network Management." *IEEE Communications Magazine*, 2024.

