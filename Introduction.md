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

