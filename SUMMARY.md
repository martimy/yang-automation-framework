# Code Description

The framework folder contains a modular, four-layer network automation engine designed to manage multi-vendor devices (Arista cEOS and Nokia SR-Linux) using YANG-based APIs.

Here is the breakdown of its components:


1. The Core Layers

  * `intent/`: Contains Python dataclasses (like InterfaceIntent, OspfIntent, NtpIntent). This layer defines what you want to configure in a vendor-neutral way.
  * `orchestration/`: Contains vendor-specific logic (CeosOrchestrator, SrlinuxOrchestrator). This layer knows the sequence and dependencies for each vendor (e.g.,
    SR-Linux requires subinterfaces to be bound to a network-instance).
  * `translation/`: Converts Intents into vendor-specific payloads. It uses Jinja2 templates (in templates/) to generate XML for NETCONF or Python dictionaries for
    gNMI.
  * `transport/`: Handles the communication with the devices. It includes netconf.py (using ncclient) and gnmi.py (using pygnmi).


2. Management & Configuration

  * `deploy.py`: The main entry point script. It reads devices.yml, instantiates the correct transport and orchestrators, and executes the provisioning loop.
  * `registry.py`: The "glue" that maps a vendor string (e.g., "ceos") to its specific orchestrator and translator classes.
  * `devices.yml`: The source of truth containing device hostnames, connection details, and the intended configuration (intents) for each device.


3. Key Features

  * Multi-Protocol: Supports both NETCONF and gNMI for the same intents.
  * Atomic Changes: The NETCONF transport implements a Candidate → Validate → Confirmed-Commit workflow for safety.
  * Vendor Abstraction: You can push the same OSPF or Interface intent to both Arista and Nokia; the framework handles the underlying model differences.

# Code Analysis

Based on the framework/ source code and translation templates, here is a summary of the major differences and similarities between Arista cEOS and Nokia SR-Linux across NETCONF and gNMI.


1. YANG Model Support by Feature



| Feature       | Arista cEOS Model                  | Nokia SR-Linux Model                              | Portability         |
|---|---|---|---
| Interfaces    | OpenConfig (openconfig-interfaces) | Native (urn:nokia.com:srlinux:chassis:interfaces) | Low (Native vs. OC) |
| IP Addressing | OpenConfig (openconfig-if-ip)      | Native (urn:nokia.com:srlinux:chassis:interfaces) | Low (Native vs. OC) |
| OSPF          | OpenConfig (openconfig-ospf)       | Native (urn:nokia.com:srlinux:ospf:ospf)          | Low (Native vs. OC) |
| NTP           | OpenConfig (openconfig-system)     | OpenConfig (openconfig-system)                    | High (Common Model) |



2. Transport Consistency (NETCONF vs. gNMI)

Both vendors generally support the same YANG models regardless of whether you use NETCONF or gNMI, but the payload format changes:

   * NETCONF: Uses XML representations of the models.
   * gNMI: Uses JSON-IETF (or Python dictionaries) representations.
   * Key Similarity: In framework/translation/common/ntp.py, the same OpenconfigNtpTranslator is used for both vendors, demonstrating that when both vendors support the same standard model (OpenConfig System), the automation becomes highly portable.

3. Major Operational Differences (Orchestration)

The most significant difference discovered in the code is Type 2 (Operational) Divergence, handled by the Orchestration layer:


   * Arista cEOS (`CeosOrchestrator`):
       * Simplicity: It can push an interface and its IP address in a single atomic payload.
       * Bootstrap: Requires a one-time "bootstrap" to enable ip routing globally (often via a global translator).
       * Implicit Binding: It automatically binds the interface to the default network instance.

   * Nokia SR-Linux (`SrlinuxOrchestrator`):
       * Complexity (Dependencies): It requires a strict three-step sequence:
           1. Create the Subinterface (Parent interface + Index).
           2. Ensure the Network Instance (VRF) exists.
           3. Bind the subinterface to the network instance.
       * Multi-Object: While cEOS sees an interface as one object, SR-Linux treats the subinterface and its L3 binding as distinct objects that must be coordinated.

4. Summary Table


| Category               | Arista cEOS                          | Nokia SR-Linux                               |
---|---|---
| Primary Model Strategy | OpenConfig-heavy                     | Native-heavy                                 |
| Protocol Support       | NETCONF & gNMI                       | NETCONF & gNMI                               |
| Sequential Dependency  | Low (Single-shot config)             | High (Requires ordered binding)              |
| Safe Delivery          | Candidate / Validate / Commit        | Candidate / Validate / Commit                |
| gNMI Pathing           | openconfig-interfaces:interfaces/... | urn:nokia.com:srlinux:chassis:interfaces/... |



Conclusion: While both vendors support modern YANG-based management, Arista cEOS leans towards OpenConfig standardization, making it easier to share translators with
other vendors. Nokia SR-Linux uses a more powerful but complex native model that requires a specialized orchestrator to handle the strict order of operations for
interface and VRF bindings.
