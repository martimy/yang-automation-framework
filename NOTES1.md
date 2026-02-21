  1. The "Discovery-First" Workflow
  The notes emphasize that automation starts with discovery, not coding. The observed sequence is:
   1. Retrieve Capabilities: Check what models the device supports (e.g., get_capabilties.py | grep ospf).
   2. Fetch Schema: Download the exact YANG file from the device using get-schema.
   3. Visualize: Use pyang -f tree to understand the data hierarchy and types.
   4. Reverse Engineer: Configure via CLI, then run get-config to see the "truth" of the XML/JSON representation.


  2. Vendor Implementation Differences (Type 2 Divergence)
  The notes explicitly contrast the operational complexity between Arista and Nokia:
   * Arista cEOS (Simple Sequence): High-level abstraction where a single payload can handle an interface, its IP, and its routing state. It relies on a "bootstrap"
     step to enable IP routing globally.
   * Nokia SR-Linux (Complex Dependencies): A more granular, object-oriented approach. It requires a strict three-step recipe:
       1. Create the subinterface.
       2. Verify/Create the network-instance.
       3. Bind the subinterface to the network-instance.
      Failure to follow this order results in a commit error.


  3. Pragmatic use of YANG Models
  The notes reveal a strategy for model selection:
   * Standardization: Prefers IETF (ietf-interfaces) and OpenConfig (openconfig-if-ip) for common features like interfaces and IP.
   * Fallback to Native: Uses Nokia Native (srl_nokia-ospf) when the standard models are either unsupported or insufficient for the vendor's specific implementation.
   * Commonality: Identifies that NTP is one of the few features where both vendors use the same model (openconfig-system).


  4. Intent-Based Design Patterns
  The code snippets show a transition from scripts to a Declarative System:
   * Uses Python Dataclasses (e.g., NetworkInstanceIntent, OspfIntent) to define the "Goal" independently of the "Protocol."
   * Uses Jinja2 Templates to separate the structure of the YANG payload from the actual data.
   * Encapsulates vendor-specific "recipes" into Orchestrator classes, keeping the main logic clean.


  5. Technical "Gotchas" and Practical Notes
   * cEOS Defaults: Interfaces default to Layer 2; the orchestrator must handle the no switchport equivalent (Type 3 difference).
   * SR-Linux Structure: Every interface requires at least one sub-interface and must be associated with a network-instance to function.
   * XML Generation: Recommends using pyang -f sample-xml-skeleton to create the initial XML structure for translators, which reduces manual errors when building
     templates.


  6. Role of Tooling
  The file highlights a specific "NetDevOps" toolkit:
   * `pyang`: For schema visualization.
   * `ncclient`: For NETCONF transport.
   * `gnmic`: For gNMI exploration and telemetry.
   * `containerlab`: As the essential sandbox for testing these complex sequences before they reach production.

