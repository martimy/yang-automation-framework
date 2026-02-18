# Model-Driven Network Automation with YANG, NETCONF, and gNMI

<!--Course Edition 1.1 - With Orchestration Layer-->
 
# Preface

This course teaches you how to configure network devices using YANG data models as the foundation. Rather than treating network automation as "scripted CLI," you will learn to think in terms of structured data: YANG is the schema, NETCONF and gNMI are the transports, and your Python code is the business logic that bridges human intent to machine-readable payloads.

All labs in this course are built on Containerlab, an open-source network emulation platform that spins up virtual instances of Nokia SR-Linux and Arista cEOS on your laptop. You are encouraged to complete every lab on your own first before teaching it, so that you experience the discovery and debugging process firsthand. That hands-on friction is where the real learning happens.

# How to Use This Course

Each module introduces a concept, explains the theory, and then provides a worked lab exercise using Containerlab. Complete the labs in order — each one builds directly on the previous. Code samples are illustrative; the goal is to understand the pattern, not copy-paste the snippet.

# Prerequisites

- Familiarity with networking fundamentals: IP addressing, routing protocols, VLANs
- Basic Python 3 programming (functions, classes, dictionaries, loops)
- Comfort with the Linux command line and a text editor
- Docker installed on your workstation (required for Containerlab)

# Learning Objectives

By the end of this course, students will be able to:

1.	Explain what YANG is and how it relates to NETCONF and gNMI
2.	Discover and navigate YANG models using pyang and device RPCs
3.	Build XML and JSON payloads that target specific YANG paths
4.	Apply the four-layer software architecture to write portable automation code
5.	Understand and implement orchestration patterns for vendor-specific operational sequences
6.	Safely push configuration to devices using candidate datastores and confirmed-commit
7.	Extend a working codebase to cover interfaces, NTP, and SNMP
8.	Test all workflows against virtual devices in Containerlab before touching production
 
# Module 1: The Mental Model

The single most important shift in moving to model-driven automation is conceptual. When you type commands into a CLI, you are constructing vendor-specific syntax that the device parses into an internal data structure. Model-driven automation skips the middle step: you write directly to that data structure. The CLI is merely one serialization of that structure. YANG, NETCONF, and gNMI give you direct access to the model itself.

## What is YANG?

YANG (Yet Another Next Generation) is a data modelling language defined in RFC 6020 and revised in RFC 7950. It describes the structure, types, constraints, and relationships of configuration and operational data for network devices. Think of a YANG model the way you would think of a database schema: it defines what data exists, what type each field must be, which fields are mandatory, and how data elements relate to each other.

A YANG model does NOT contain any configuration values. It only describes the shape of the data. The values: your router ID, your OSPF area, your interface IP, are provided separately in an XML or JSON document that conforms to the model.

## Key Analogy

YANG is to network configuration what JSON Schema is to a REST API body. It defines what valid data looks like. NETCONF and gNMI are the HTTP equivalents — the transports that carry your data to and from the device.

## The Three Pillars

Pillar | Role
---|------
YANG | The schema. Defines what data the device can hold, and its types and constraints.
NETCONF (RFC 6241) | An XML-based protocol for reading and writing configuration over SSH. Operates on named datastores (running, candidate, startup).
gNMI (gRPC Network Mgmt Interface) | A gRPC-based protocol for streaming telemetry and configuration. Uses JSON or Protobuf payloads. Common in modern cloud-native stacks.

## YANG Model Families

You will encounter three families of YANG models in the wild, and it is critical to understand the difference before you write a single payload:

Family | Defined By | Portability | Example
---|---|---|---
IETF Standard | IETF RFCs | High — works across vendors | ietf-interfaces, ietf-ospf
OpenConfig | OpenConfig consortium | Medium — vendor may augment | openconfig-bgp, openconfig-if-ip
Vendor Native | Individual vendor | None — vendor-locked | Cisco-IOS-XE-ospf, nokia-conf

The practical strategy is to use IETF or OpenConfig models wherever they are well-supported, and fall back to native models only where the standard model lacks coverage. Your Translation Layer (covered in Module 4) is the right place to handle this decision per-feature per-vendor.

Why This Matters for Automation

- A single intent object can drive configuration on Nokia, Arista, and Cisco simultaneously
- Your automation is self-documenting: the YANG tree tells anyone what data the device expects
- Validation can happen offline before the configuration ever touches the network
- The network becomes programmable in the same way a database or REST API is programmable
 
# Module 2: Setting Up Your Lab Environment with Containerlab

Before touching a real device, every workflow in this course must be tested in a virtual lab. Containerlab is an open-source tool that defines network topologies in a simple YAML file and runs them as Docker containers. Nokia SR-Linux and Arista cEOS images are freely available and both have excellent NETCONF and gNMI support, making them ideal targets for this course.

## Installing Containerlab

Containerlab requires Docker and a Linux environment (native Linux or WSL2 on Windows). Install it with the single-line installer from the official documentation:

```bash
# Install Containerlab (visit containerlab.dev for the latest installer)
bash -c "$(curl -sL https://get.containerlab.dev)"
```

## Installing Python Packages

I recommend using Python virtual environment:

```bash
$ sudo apt-get install python3.10-venv
$ python3 -m venv .ylab
$ source .ylab/bin/activate
```

```bash
$ pip install six
$ pip install netconf-console2
$ pip install pyang
...
```

### Defining a Topology

A Containerlab topology is a YAML file. The example below creates a three-node lab with two Nokia SR-Linux router and one Arista cEOS router connected in a ring. This is your primary lab environment for the entire course:


Start the lab with:

```
sudo containerlab deploy [-t yang.clab.yml]
```


### Verifying NETCONF Connectivity

Once the lab is running, verify that NETCONF is reachable on port 830 using netconf-console2:

```bash
netconf-console2 --host=srl-01 --port 830 -u admin -p 'NokiaSrl1!' --hello
netconf-console2 --host=ceos-01 --port 830 -u admin -p 'admin' --hello
```

or use raw ssh connection:

```bash
ssh admin@ceos-01 -p 830 -s netconf
ssh admin@srl-01 -p 830 -s netconf
```

> **What Both Commands Are Actually Doing**  
NETCONF is always transported over SSH. Specifically, it uses SSH's subsystem mechanism, named 'netconf'. So both commands above are ultimately opening an SSH connection and requesting the netconf subsystem. The difference is only in who is doing the SSH work.  
`netconf-console2` is a dedicated NETCONF client. It handles the SSH transport internally, sends a proper NETCONF <hello> message with its own capabilities, waits for the device's <hello> in response, and then presents the result to you cleanly. It understands the NETCONF framing protocol (the ]]>]]> end-of-message marker in NETCONF 1.0, or chunked framing in 1.1).  
`ssh -s netconf` is raw SSH. It opens the subsystem channel but does nothing after that. You are dropped directly into the NETCONF session at the XML layer. The device sends its <hello> message immediately, and then waits for yours. If you just sit there, nothing further happens — you would need to type raw XML to continue. It is useful for confirming the port is open and the device is responding, but it is not a practical way to send operations.



: Lab Environment Summary

Component | Purpose in This Course
---|-----
Containerlab | Orchestrates virtual network nodes as Docker containers
Nokia SR-Linux & Arista cEOS | Configuration targets to demonstrate vendor differences in Translation and Orchestration Layers
netconf-console2 | A dedicated NETCONF client. It handles the SSH transport 
Python 3 + venv | All automation scripts; isolate dependencies per lab
ncclient | Python NETCONF transport library
pyang | YANG visualization and validation tool
pygnmi | Python gNMI transport library
libyang2-tools | Offline YANG data validation

# Module 3: Model Discovery — Know Before You Automate

You cannot automate what you do not understand. Before writing a single payload, you must discover what YANG models the device supports and understand the shape of the data those models describe. This module covers three complementary discovery techniques that together give you a complete map of the device's data model.

## Technique 1: Retrieve Capabilities

Every NETCONF session begins with a capabilities exchange. The device advertises every YANG module it supports, along with the exact revision date. This is your authoritative list of what you can configure:

The following snippet connects and prints the device's advertised YANG capabilities, which is your first model discovery step (edit the file for each router):


*get_capabilties.py*

```python
from ncclient import manager

conn_params = {
    "host": "srl-01",
    "port": 830,
    "username": "admin",
    "password": "NokiaSrl1!",
    "hostkey_verify": False
}

with manager.connect(**conn_params) as m:
    # Filter for YANG model capabilities specifically
    yang_caps = [c for c in m.server_capabilities if 'module=' in c]
    for cap in sorted(yang_caps):
        print(cap)
```

Each capability string contains the module name, namespace, and revision. For example: 

```bash
urn:ietf:params:xml:ns:yang:ietf-interfaces?module=ietf-interfaces&revision=2014-05-08
```

Note the revision date — always use models that match this exact revision when building payloads.


**Using gNMI and gNMic**


```python
from pygnmi.client import gNMIclient

# Create gNMI client connection
with gNMIclient(**ceos_params) as gc:

    # Retrieve capabilities
    capabilities = gc.capabilities()

    caps = [
        f'{c["name"]}, {c["organization"]}, {c["version"]}'
        for c in capabilities["supported_models"]
    ]
    for cap in sorted(caps):
        print(cap)
```

or use gNMIc:

```bash
# Download gNMIc
$ bash -c "$(curl -sL https://get-gnmic.openconfig.net)"

gnmic -a ceos-01:6030 -u admin -p admin --insecure capabilities
gnmic -a srl-01 -u admin -p NokiaSrl1! --skip-verify capabilities
```

> **gNMIc (pronounced gee·en·em·eye·see)**  
is a powerful, open-source command-line client and collector for the gRPC Network Management Interface (gNMI) protocol, originally developed by Nokia and contributed to the OpenConfig project. It serves as a comprehensive tool for interacting with modern network devices, offering full support for all core gNMI RPCs (Capabilities, Get, Set, and Subscribe) to both retrieve and modify configuration and operational state data. Beyond its function as a CLI client, gNMIc can be deployed as a flexible, scalable, and highly available telemetry collector that subscribes to streaming data from network targets and can output to multiple destinations like Kafka, Prometheus, and InfluxDB, often with built-in data transformation capabilities.

## Technique 2: Fetch the Schema

Once you know which modules the device supports, you can pull the actual YANG source files directly from the device using the `get-schema` NETCONF RPC. This guarantees you have the exact model version the device is running, not a version from a public repository that may differ:

*get_schema.py*

```python
with manager.connect(**conn_params) as m:
    schema = m.get_schema('ietf-interfaces')
    with open('ietf-interfaces.yang', 'w') as f:
        f.write(schema.data)
```

Run the script for both devices and save the result in different files.

## Technique 3: Visualize the Tree with pyang

Raw YANG source is verbose and difficult to read. The pyang tool renders any YANG model as a concise indented tree that shows every configuration path, its data type, and whether it is mandatory. This tree is your primary reference when building payloads:

```bash
# Render a tree for ietf-interfaces
pyang -f tree ietf-interfaces.yang
```

A section of the output will look like this, directly mapping to the XML structure you will construct:

```bash
module: ietf-interfaces
  +--rw interfaces
  |  +--rw interface* [name]
  |     +--rw name                        string
  |     +--rw description?                string
  |     +--rw type                        identityref
  |     +--rw enabled?                    boolean
  |     +--rw link-up-down-trap-enable?   enumeration {if-mib}?
```

**Reading the Tree**

The `+--rw` prefix means read-write (configurable). `+--ro` means read-only (operational state). A `*` after the node name means it is a list (multiple entries). A `?` means the field is optional. These symbols tell you exactly what your payload must and can include.

For some modules, you will need to download the dependencies first:

```bash
$ git clone https://github.com/openconfig/public openconfig
$ pyang -f tree -p openconfig arista-intf-augments.yang
```


## Technique 4: The Reverse Engineering Discipline

A reliable and fast path to a working payload is to configure the feature manually via CLI first, then use a NETCONF `get-config` to read back exactly how the device represents that configuration in YANG. This approach is especially valuable when vendor documentation is unclear or when you are working with a native model for the first time:

```python
# Get the full running configuration as YANG/XML
with manager.connect(**conn_params) as m:
    config = m.get_config(source='running')
    print(config.data_xml)
```

Read the output carefully. The namespace declarations, element names, and hierarchy you see in that XML are exactly what your payload must reproduce. Save this output as a reference alongside the `pyang` tree.

### Lab Exercise 1: Discover the Interface Model

Deploy your `Containerlab` topology. Configure one interface with an IP address manually using the device CLI. Then perform a `get-config` and locate the interface configuration in the XML output. Cross-reference it with the `pyang` tree for *ietf-interfaces* and *openconfig-if-ip*. Document the exact YANG path and namespace you will need to construct a payload for this interface.

> Note that SR-Linux requires that you you configure at least one sub-interface and the sub-interface must be associated with a network-instance (i.e. VRF). cEOS creates the subinterface 0 by default. Both follow the convention of OpenConfig YANG models.  

## Module 4: The Four-Layer Software Architecture

The fundamental design mistake in network automation is mixing what you want to configure, how it is represented in YANG, and how it is delivered over the wire into a single block of code. This creates brittle, unportable code. A properly layered architecture solves this by giving each concern its own isolated layer, so a change in one never requires a change in the others.

### Insight: Three Types of Vendor Differences

As you work through Lab Exercise 1, you will encounter a critical insight that shapes the entire architecture. When you manually configure an interface on both SR-Linux and cEOS and then examine the YANG representation, you'll notice something important:

**On Arista cEOS:**
```bash
# Configure an interface
interface Ethernet1
   description To SRL-01
   no switchport
   ip address 192.168.1.2/31
```

**On Nokia SR-Linux:**
```bash
# Configure an interface
set / interface ethernet-1/1 admin-state enable
set / interface ethernet-1/1 subinterface 0 admin-state enable
set / interface ethernet-1/1 subinterface 0 ipv4 admin-state enable
set / interface ethernet-1/1 subinterface 0 ipv4 address 192.168.1.3/31
set / network-instance default interface ethernet-1/1.0
```

A `get-config` for both devices reveals identical structure that includes the interface, its IPv4 address , and its description in the expected locations within the OpenConfig interface model.

However, configuring SRLinux interface via the CLI or using YANG is more complex. The device requires three separate configuration objects: a subinterface, a network-instance, and a binding between them. Moreover, these must be configured in a specific order, subinterface followed by binding before. If you try to bind a subinterface to a network-instance before the subinterface exists, the commit operation fails.

Although Arista cEOS implements the same OpenConfig YANG model, the subinterface creation (index 0) and binding to network instance (default) occurs automatcally. 

This reveals two fundamentally different types of vendor differences:

**Type 1: Model Differences (Translation Problem):**

- Same feature, different YANG representation
- Example: Interface description is a `<description>` leaf in OpenConfig but a `<desc>` leaf in some native models
- Solution: Different translator classes that render the same intent into vendor-specific XML

**Type 2: Operational Differences (Orchestration Problem):**

- Same goal, different sequence of prerequisite operations
- Example: SR-Linux requires binding subinterface to network-instance before; cEOS does not
- Solution: An orchestration layer that knows the correct recipe for each vendor

**Type 3: Support Differences (Support Problem):**

- Feature not exposed in any YANG model
- Example: cEOS interfaces defaults to layer 2 switching mode and IP routing is disabled by default
- Solution: Manual configuration using CLI (`no switchport`)

A four-layer architecture handles Type 1 and Type 2 differences adequately.


### The Four-Layer Architecture

```
+-------------------------------------+
|         INTENT LAYER                |  What you want (vendor-agnostic)
+-------------------------------------+
                ↓
+-------------------------------------+
|     ORCHESTRATION LAYER             |  Sequences operations
|   (vendor-aware workflow engine)    |  per vendor, resolves dependencies
+-------------------------------------+
                ↓
+-------------------------------------+
|       TRANSLATION LAYER             |  How to express it in YANG
|   (includes prerequisite            |  (extended with prereq translators)
|    translators per vendor)          |
+-------------------------------------+
                ↓
+-------------------------------------+
|       TRANSPORT LAYER               |  Wire protocol (unchanged)
+-------------------------------------+
```

: Layer Overview

Layer | Responsibility
---|------
Intent Layer | Expresses what you want in abstract terms, independent of any protocol or vendor details. Can be expressed by Python dataclasses or YAML file and easily readable by a network engineer.
Orchestration Layer | Knows the correct mix of operations for each vendor. Resolves prerequisite dependencies and ensures operations execute in the correct order. One orchestrator class per vendor.
Translation Layer | Maps an Intent object onto a specific YANG model and renders it as an XML or JSON payload. This is where model differences are handled. One translator class per feature per vendor.
Transport Layer | Delivers payloads to the device over NETCONF or gNMI. Manages connections, handles datastores, commits, and rollbacks. Has no knowledge of what the payload contains.

**The Intent Layer**

An Intent dataclass describes the desired state of one feature on one device. It uses plain Python types: strings, integers, booleans, and lists. Here is the InterfaceIntent class annotated for clarity:

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class InterfaceIntent:
    name: str              # e.g. 'Ethernet1' or 'ethernet-1/1'
    description: str
    ip_address: str        # e.g. '192.168.1.1'
    prefix_length: int     # e.g. 24
    enabled: bool = True
    subinterface_index: int = 0
    network_instance: str = 'default'
    ...
    ...
```

The power of this layer is in its readability. A network engineer can review this class and instantly understand what parameters drive the deployment, without reading a single line of XML or YANG.

Note that `subinterface_index` and `network_instance` fields are required by SR-Linux but cEOS doesn't need them. The intent class includes them, but each orchestrator decides which fields to use.

**The Orchestration Layer**

An orchestrator knows the recipe for achieving a working configuration on each vendor: the correct mix of payloads, in the correct order, with the correct dependencies resolved before each step.

Each vendor gets its own orchestrator class:

```python
from abc import ABC, abstractmethod

class DeviceOrchestrator(ABC):
    """
    Abstract base — one concrete subclass per vendor.
    Knows the correct sequence of operations for that vendor.
    """
    def __init__(self, transport, translators):
        self.transport = transport
        self.translators = translators

    @abstractmethod
    def configure_interface(self, intent: InterfaceIntent) -> bool:
        pass

    @abstractmethod
    def bootstrap(self) -> bool:
        """Apply any one-time prerequisites the device needs."""
        pass
```

**The Translation Layer**

A translator is a class with one method per intent type. It takes an intent object and returns a serialized payload string. The key discipline is that the payload structure mirrors the `pyang` tree exactly. Each namespace URI in the XML corresponds to a YANG module, and each element name maps to a node in the tree:

```python
from jinja2 import Template

class IetfInterfaceTranslator:
    TEMPLATE = Template('''
    <config>
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface>
          <n>{{ name }}</n>
          <description>{{ description }}</description>
          <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">
            ianaift:ethernetCsmacd
          </type>
          <enabled>{{ enabled | lower }}</enabled>
          <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
            <address>
              <ip>{{ ip_address }}</ip>
              <prefix-length>{{ prefix_length }}</prefix-length>
            </address>
          </ipv4>
        </interface>
      </interfaces>
    </config>''')

    def translate(self, intent: InterfaceIntent) -> str:
        return self.TEMPLATE.render(**intent.__dict__)
```

> **Avoid CLI Leakage**  
Never embed vendor-specific CLI strings inside a Jinja2 template. A string like 'ip address 192.168.1.1 255.255.255.0' inside your XML payload is called CLI leakage. It destroys portability because you are mixing two config paradigms. The payload must contain only element names and values from the YANG model.

**The Transport Layer**

The transport layer is the cleanest of the four. It knows nothing about OSPF, interfaces, or NTP. It only knows about connections, datastores, and NETCONF operations. This separation means you can swap NETCONF for gNMI without touching a single translator or orchestrator:

```python
from ncclient import manager
import xmltodict

class NetconfTransport:
    def __init__(self, host, username, password, port=830):
        self.params = dict(host=host, port=port,
            username=username, password=password,
            hostkey_verify=False,
            device_params={'name': 'default'})

    def get_config(self, filter_xml: str) -> dict:
        with manager.connect(**self.params) as m:
            result = m.get_config(source='running',
                filter=('subtree', filter_xml))
            return xmltodict.parse(result.data_xml)

    def push_config(self, payload_xml: str,
                   confirmed=True, timeout=120) -> bool:
        with manager.connect(**self.params) as m:
            m.edit_config(target='candidate',
                          config=payload_xml)
            m.validate(source='candidate')
            if confirmed:
                m.commit(confirmed=True,
                         timeout=str(timeout))
                m.commit()
            else:
                m.commit()
            return True
```

**The Translator and Orchestrator Registry**

Each vendor now has its own set of translators and its own orchestrator class:

```python
TRANSLATORS = {
    'ceos': {
        'interface':         CeosInterfaceTranslator(),
    },
    'srlinux': {
        'subinterface':      SrlinuxSubinterfaceTranslator(),
        'ni_interface':      SrlinuxNiInterfaceBindingTranslator(),
    }
}

ORCHESTRATORS = {
    'ceos':    CeosOrchestrator,
    'srlinux': SrlinuxOrchestrator,
}
```

**The Complete Workflow**

The top-level script becomes clean and vendor-agnostic:

```python
DEVICE_REGISTRY = [
    {
        'host':   'ceos-01',
        'vendor': 'ceos',
        'intents': [
            InterfaceIntent(
                name='Ethernet1',
                description='To SRL',
                ip_address='192.168.1.2',
                prefix_length=24,
            )
        ]
    },
    {
        'host':   'srl-01',
        'vendor': 'srlinux',
        'intents': [
            InterfaceIntent(
                name='ethernet-1/1',
                description='To cEOS',
                ip_address='192.168.1.1',
                prefix_length=24,
                subinterface_index=0,
                network_instance='default',
            )
        ]
    },
]

def provision_all():
    for device in DEVICE_REGISTRY:
        transport    = NetconfTransport(device['host'], 'admin', 'secret')
        translators  = TRANSLATORS[device['vendor']]
        OrchestratorClass = ORCHESTRATORS[device['vendor']]
        orchestrator = OrchestratorClass(transport, translators)

        # Run bootstrap once per device
        orchestrator.bootstrap()

        # Apply each intent in order
        for intent in device['intents']:
            orchestrator.configure_interface(intent)
            print(f"{device['host']} — {intent.name} configured")

provision_all()
```

**The Impact Matrix**

The real payoff of this architecture becomes clear when you need to make changes. Notice how each type of change affects each layer below. Often, the changes is completely contained within one layer:

| Change needed | Intent | Orchestration | Translation | Transport |
|---|---|---|---|---|
| Add new vendor | Maybe new fields | New orchestrator class | New translators | No change |
| Add IPv6 support | Add IPv6 fields | Minor update | New template | No change |
| Switch to gNMI transport | No change | No change | No change | New transport class |
| Upgrade YANG model version | No change | No change | Update template | No change |
| Add NTP | New Intent | Add to orchestrator | New translator | No change |


### Lab Exercise 2: Build Your First Translator and Orchestrator

Write an `InterfaceIntent` dataclass and an `SrlinuxSubinterfaceTranslator` for your SR-Linux node. Use the YANG path you discovered in Lab 1. Then write a `SrlinuxOrchestrator` that sequences the three required operations: subinterface creation and network-instance-interface binding.

Push the configuration using the NetconfTransport class and verify it with a `get-config` call. Then write a `CeosOrchestrator` and `CeosInterfaceTranslator` and push the same intent to the cEOS node. Observe that the intent object is identical; only the orchestrator and translator classes change.

 
# Module 5: Safe Configuration Delivery

Writing the correct payload is only half the problem. Delivering it safely, in a way that is atomic, reversible, and validated before it takes effect, is equally important. NETCONF's datastore model gives you the tools to do this correctly. Using them is not optional in production environments.

## The NETCONF Datastore Model

NETCONF distinguishes between three datastores. Understanding when each is used is fundamental:

Datastore | Purpose
---|-------
running | The active configuration currently in use by the device. Changes here take effect immediately. Direct writes to running should be avoided in production.
candidate | A staging area for changes. You can write, validate, and test here without affecting the live device. The candidate is promoted to running only on explicit commit.
startup | The configuration loaded on boot. Relevant for ensuring changes persist across a reboot.

## The Get-Before-Set Pattern

Never push a configuration blindly. Before any edit operation, retrieve the current state of the configuration subtree you are about to modify. This gives you a baseline, confirms the device's current state matches your assumptions, and helps you build a minimal diff rather than a full replacement payload:

Inspect current_state before building your edit payload:

```
INTERFACE_FILTER = '''
  <interfaces xmlns="http://openconfig.net/yang/interfaces">
    <interface>Eternet1</n></interface>
  </interfaces>
'''

current_state = transport.get_config(INTERFACE_FILTER)
```

## The Candidate, Validate, Commit Sequence

The correct production sequence for pushing configuration is a three-step process. Skipping any step introduces risk:

1. Edit candidate: write your payload to the candidate datastore. The running config is not touched.
2. Validate: ask the device to validate the entire candidate datastore against its YANG schemas. If the device rejects the validation, nothing has changed on the running config.
3. Commit: promote the validated candidate to running. All changes in the candidate take effect atomically; either everything applies or nothing does.

**Confirmed-Commit: Your Production Safety Net**

The confirmed-commit extension is one of the most important safety mechanisms in NETCONF. When you issue a confirmed commit, the device applies your changes but sets a timer. If you do not send a confirming commit before the timer expires, the device automatically reverts to the previous configuration. This prevents you from accidentally locking yourself out of a device:

```
# Confirmed commit with 2-minute rollback window
m.commit(confirmed=True, timeout='120')

# ... verify your changes work correctly ...

# Send the confirming commit to make the change permanent
m.commit()
```

> **Production Rule**  
Always use confirmed-commit in production. The two-minute timeout is a seatbelt: the cost of sending one extra commit() call is trivial; the cost of a wrong config locking you out of a core router is not. Build the confirming commit into your verification step so it only fires after your validation checks pass.

**Offline Validation with yanglint**

Before a payload ever touches a device, you can validate it locally against the YANG schema using yanglint. This catches structural errors, missing mandatory fields, and type mismatches without consuming a device connection:

```bash
# Install libyang (provides yanglint)
sudo apt-get install libyang-tools   # Ubuntu/Debian

# Validate your payload XML against the schema
yanglint ietf-interfaces.yang payload.xml
```


### Lab Exercise 3: Safe Delivery Workflow

Take the orchestrator you built in Lab 2 and wrap it in the full candidate/validate/confirmed-commit sequence. Deliberately introduce an error into your payload (use an invalid IP address format or omit a mandatory field) and observe how `yanglint` and the device's validation catch it at different stages. Verify that the running config is unchanged after a failed validation.
 
# Module 6: Extending the Framework to OSPF, NTP, and SNMP

With the four-layer architecture and the safe delivery workflow established, extending your automation to new features follows a predictable, repeatable pattern. This module walks through the high-level approach for the most common infrastructure features, highlighting the key YANG models and the practical challenges you will encounter for each.

**The Extension Pattern**

For every new feature, follow the same steps before writing any code:

1. Discover: find the relevant YANG model, run `pyang` on the relevant YANG model and read the tree
2. Reverse-engineer: configure the feature via CLI, then get-config to see its YANG representation
3. Add an Intent class: write a dataclass that captures the parameters a network engineer would care about
4. Write translators: one translator class per vendor, per feature, mapping the intent to the correct YANG path
5. Update orchestrators: if the feature has vendor-specific sequencing requirements, update the orchestrator's workflow


**OSPF Configuration**

OSPF is the first feature where you will encounter significant divergence between vendors. Artista cEOS implements the OpenConfig model (openconfig-ospf) while Nokia SR-Linux implements a Native model (srl_nokia-ospf).

For your translator registry, you will need to implement a translator for each vendor. Your OspfIntent remains identical in both cases; only the translator class changes.

The main challenge in configuring OSPF is possibility to create multiple OSPF processes; each one could have multiple areas with multiple interfaces in each. Therefore, you can create a hierarchy of intents: one main intent for each OSPF process that include a list of area intents, which in turn includes a list of interface intents. 

**NTP Configuration**

NTP is the first feature where you will encounter significant divergence between vendors. The IETF NTP model (RFC 9249, ietf-ntp) is relatively new and vendor support varies considerably. Nokia SR-Linux implements a reasonable subset. Cisco IOS-XE and Arista both have more mature native NTP models that expose more knobs.

For your translator registry, the practical approach is to implement an IetfNtpTranslator for vendors that support it and fall back to a native translator for those that do not. Your NtpIntent remains identical in both cases; only the translator class changes.

Key parameters to capture in NtpIntent: list of server IPs or hostnames, the source interface for NTP packets, authentication mode and keys if required, and whether to use burst mode. Most production deployments need at least two NTP servers for redundancy.

**SNMP Configuration**

SNMP is the most vendor-divergent feature you will encounter in this framework. The ietf-snmp model exists but is inconsistently implemented, meaning you will almost always be working with native YANG models. This is expected and acceptable — the four-layer architecture is specifically designed for this situation. Your SnmpIntent class is clean and portable; the complexity is entirely isolated in the translation and orchestration layers.

For SNMPv2c, the critical parameters are the community string, the list of trap destinations with their community strings, and the system location and contact. For SNMPv3, replace community strings with USM user configurations, authentication protocols (MD5 or SHA), and privacy protocols (DES or AES).

Recommended approach for SNMP in this framework:

- Build native translators for each vendor rather than fighting a poorly-supported IETF model
- Keep the SnmpIntent class version-agnostic by including both v2c and v3 parameters and letting the translator use whichever fields are relevant
- Validate SNMP trap delivery as part of your post-commit verification step

**The Translator Registry**

As your feature coverage grows, the orchestrator needs a way to select the correct translator for a given vendor and feature combination. A simple nested dictionary serves this purpose well. The outer key is the vendor identifier, the inner key is the feature name, and the value is an instantiated translator object:

```
TRANSLATORS = {
    'nokia': {
        'interface': IetfInterfaceTranslator(),
        'ospf':      IetfOspfTranslator(),
        'ntp':       IetfNtpTranslator(),
        'snmp':      NokiaNativeSnmpTranslator(),
    },
    'arista': {
        'interface': IetfInterfaceTranslator(),
        'ospf':      CeosOspfTranslator(),
        'ntp':       AristaNativeNtpTranslator(),
        'snmp':      AristaNativeSnmpTranslator(),
    },
}
```

### Lab Exercise 4: Full Device Bring-Up

Write a complete bring-up script for your SR-Linux node that configures, in order: interfaces with IP addresses, OSPF on those interfaces, an NTP server, and a basic SNMPv2c community. Extend your `SrlinuxOrchestrator` to handle all these features. Use the full candidate/validate/confirmed-commit workflow. After the commit, verify each feature using a targeted get-config subtree filter. This is a realistic simulation of a Day 1 provisioning script.
 

 
\newpage
 
# References

## IETF RFCs

- RFC 6020 — YANG: A Data Modeling Language for NETCONF (2010). The original YANG specification. foundation.ietf.org
- RFC 7950 — The YANG 1.1 Data Modeling Language (2016). The current YANG version used by all modern implementations.
- RFC 6241 — Network Configuration Protocol (NETCONF) (2011). The core NETCONF protocol specification covering datastores, RPCs, and operations.
- RFC 6242 — Using NETCONF over SSH (2011). Transport layer specification for NETCONF.
- RFC 7223 — A YANG Data Model for Interface Management (2014). Defines ietf-interfaces, the standard model for interface configuration.
- RFC 8344 — A YANG Data Model for IP Management (2018). Defines ietf-ip, the augmentation model for IPv4 and IPv6 addressing on interfaces.
- RFC 9130 — YANG Data Model for the OSPF Protocol (2022). Defines ietf-ospf covering OSPFv2 and OSPFv3.
- RFC 9249 — A YANG Data Model for NTP (2022). Defines ietf-ntp for NTP client and server configuration.
- RFC 8040 — RESTCONF Protocol (2017). The HTTP-based counterpart to NETCONF, using the same YANG models over a REST interface.

## OpenConfig

- OpenConfig Working Group — openconfig.net. Source for all OpenConfig YANG models including openconfig-interfaces, openconfig-bgp, openconfig-network-instance, and many others.
- OpenConfig GitHub Repository — github.com/openconfig/public. The canonical source for OpenConfig YANG models, with vendor implementation notes.

## Tools and Libraries Documentation

- Containerlab Documentation — containerlab.dev/docs. Complete reference for topology YAML syntax, supported node kinds, and image configuration.
- ncclient Documentation — ncclient.readthedocs.io. Python NETCONF client library API reference and usage examples.
- pygnmi Documentation — pypi.org/project/pygnmi. Python gNMI client library documentation.
- pyang Documentation — github.com/mbj4668/pyang. YANG tool usage, output format reference, and plugin development.
- libyang and yanglint — netopeer.liberouter.org/doc/libyang. C library for YANG data manipulation; includes yanglint validator.
- YANG Catalog — yangcatalog.org. Searchable index of IETF, OpenConfig, and vendor YANG models with dependency information.
- gnmic Documentation — gnmic.openconfig.net. gNMI CLI client reference and cookbook.
- Jinja2 Documentation — jinja.palletsprojects.com. Python templating engine reference.

## Vendor YANG Resources

- Nokia SR-Linux YANG Models — github.com/nokia/srlinux-yang-models. Complete model set for SR-Linux, updated per release.
- Arista EOS YANG Models — github.com/aristanetworks/yang. OpenConfig and native EOS models for Arista devices.
- YANG GitHub Repository — github.com/YangModels/yang. Community-maintained repository aggregating IETF standard, OpenConfig, and vendor YANG models.

## Books and Further Reading

- Zheng et al., Network Programmability with YANG (Addison-Wesley, 2019). The most comprehensive book-length treatment of YANG, NETCONF, and RESTCONF.
- Gooley & Stevenson, Network Programmability and Automation (O'Reilly, 2nd ed. 2023). Broader network automation context including YANG-based approaches alongside other methods.
- RFC 8199 — YANG Module Classification (2017). Useful taxonomy for understanding the relationship between IETF, OpenConfig, and vendor YANG models.


Yes, there are several good references, and they complement each other since no single one covers everything you need.


# Appendix A: Open-Source Tools

A reliable model-driven automation workflow depends on a specific set of open-source tools. Each tool in the list below addresses a distinct problem in the workflow. You do not need all of them immediately, but you should know what each one does and when to reach for it.


: Network Emulation

Tool | Description
---|------
Containerlab | The foundation of your lab environment. Defines network topologies in YAML and runs them as Docker containers. Supports Nokia SR-Linux, Arista cEOS, Cisco XRd, VyOS, and many others. Essential for testing any automation workflow before touching production hardware. https://containerlab.dev/


: NETCONF Transport

Tool | Description
---|------
ncclient | The standard Python library for NETCONF. Handles SSH transport, capability exchange, all NETCONF RPCs (get, get-config, edit-config, commit, lock, validate), and datastore management. The library most automation code in this course is built on. Available via pip
netconf-console | A command-line NETCONF client for quick interactive testing and debugging. Useful for ad-hoc get-schema retrievals and testing filters without writing Python. Available via pip.


: gNMI Transport

Tool | Description
---|------
pygnmi | A pure-Python gNMI client library. Supports Get, Set, Subscribe, and Capabilities RPCs. Integrates cleanly with the Transport Layer pattern used in this course. Available via pip
gnmic | A feature-rich gNMI command-line client written in Go. Excellent for interactive exploration, subscription testing, and building gNMI-based telemetry pipelines. Available from gnmic.openconfig.net


: YANG Model Tools

Tool | Description
---|------
pyang | The essential YANG toolkit. Parses YANG modules and renders them in multiple formats including the tree format used throughout this course. Also validates YANG syntax and converts between YANG and YIN. Available via pip.
yanglint | A command-line YANG data validator from the libyang project.Validates XML and JSON payloads against a YANG schema offline, before they touch a device. Included in the libyang package available via apt and brew.
yangson | A Python library for working with YANG-modelled data. Useful for programmatic validation and data manipulation within Python automation scripts. Available via pip.
YANG Catalog | A web-based repository and search engine for IETF, OpenConfig, and vendor YANG models. Use it to find model versions, check vendor support, and browse module dependencies before downloading from a device. https://www.yangcatalog.org/


: Payload Templating and Rendering

Tool | Description
---|------
Jinja2 | The industry-standard Python templating engine. Used in this course to separate YANG payload structure from variable data. Supports conditionals, loops, and filters, making it ideal for generating complex XML with optional elements. Available via pip.
xmltodict | Converts between XML strings and Python dictionaries. Essential for parsing get-config responses into data structures your Python code can inspect and compare. Available via pip.


: Development and Debugging

Tool | Description
---|------
ncclient with manager.logger | Enable DEBUG logging in ncclient to see the raw XML sent and received over the wire. Invaluable for debugging payload issues and understanding exactly what the device returns.
VSCode with YANG extension | The YANG language support extension for Visual Studio Code provides syntax highlighting, tree navigation, and basic validation for .yang files. Makes browsing large vendor model repositories much more productive.
git | Version control for your intent dataclasses, translators, and topology files. Every change to your automation codebase should be committed. The diff history is your audit trail for what changed on the network and when.


: Higher-Level Frameworks (For Reference)

Tool | Description
---|------
Nornir | A pure-Python automation framework with a plugin architecture. Handles inventory management, parallel task execution, and result reporting. The three-layer pattern in this course integrates naturally as Nornir tasks.
Napalm | A vendor-neutral network automation library that abstracts common operations. Useful as a reference for how vendor abstraction is handled at scale, and supports some NETCONF operations natively.
Ansible network modules | Ansible includes NETCONF and gNMI modules. Useful for teams already invested in Ansible, though the YAML-based playbook format makes the three-layer architecture harder to enforce cleanly.

<!--
: Other

```
xmllint --format yourfile.xml
```
-->


# Appendix B: Anatomy of the XML file 

When you retrieve configuration from a device using **NETCONF `<get-config>`**, the reply is an **XML-encoded instance of a YANG data model**.

Below is a structured breakdown of the anatomy of that XML, using examples aligned with:

- Arista cEOS
- Nokia SR Linux

### High-Level NETCONF Envelope

When you send:

```xml
<rpc message-id="101"
     xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <get-config>
    <source>
      <running/>
    </source>
  </get-config>
</rpc>
```

The device replies with:

```xml
<rpc-reply message-id="101"
           xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <data>
      ...
  </data>
</rpc-reply>
```

### Anatomy so far

| Element       | Purpose                                  |
---|---
| `<rpc-reply>` | NETCONF response container               |
| `message-id`  | Correlates request and response          |
| `<data>`      | Contains YANG-modeled configuration data |

Everything inside `<data>` is structured according to YANG.

### YANG → XML Mapping Rules

Understanding the mapping is key:

| YANG Concept | XML Representation        |
---|---
| container    | XML element               |
| list         | Repeated XML elements     |
| list key     | Child element inside list |
| leaf         | XML element with text     |
| leaf-list    | Repeated XML elements     |
| namespace    | `xmlns="..."` attribute   |


### Example 1: Arista cEOS (OpenConfig Interfaces)

cEOS commonly supports **OpenConfig YANG models**.

Example YANG structure (simplified OpenConfig):

```yang
container interfaces {
  list interface {
    key "name";
    leaf name { type string; }
    container config {
      leaf name { type string; }
      leaf description { type string; }
      leaf enabled { type boolean; }
    }
  }
}
```

#### XML returned by `<get-config>`

```xml
<data>
  <interfaces xmlns="http://openconfig.net/yang/interfaces">
    <interface>
      <name>Ethernet1</name>
      <config>
        <name>Ethernet1</name>
        <description>Uplink</description>
        <enabled>true</enabled>
      </config>
    </interface>
  </interfaces>
</data>
```

### Anatomy Breakdown

1. Namespace

    ```xml
    <interfaces xmlns="http://openconfig.net/yang/interfaces">
    ```

    - Tells us which YANG module this data belongs to
    - Prevents name collisions
    - Critical for XML parsing

2. Container

    ```xml
    <interfaces>
    ```

    Maps directly to:

    ```yang
    container interfaces
    ```

3. List

    ```xml
    <interface>
    ```

    Maps to:

    ```yang
    list interface
    ```

    Each `<interface>` is one list entry.



4. List Key

    ```xml
    <name>Ethernet1</name>
    ```

    - This is the **key leaf**
    - Identifies the list instance
    - Required for uniqueness

    Equivalent to:

    ```yang
    key "name";
    ```

5. Nested Container

    ```xml
    <config>
    ```

    Maps to:

    ```yang
    container config
    ```

6. Leaf Nodes

    ```xml
    <description>Uplink</description>
    <enabled>true</enabled>
    ```

    Simple scalar values defined as:

    ```yang
    leaf description { type string; }
    leaf enabled { type boolean; }
    ```


### Example 2: Nokia SR Linux (Native YANG)

Nokia SR Linux uses its own YANG models (e.g., `srl_nokia-interfaces`).

Simplified YANG:

```yang
container interface {
  list ethernet {
    key "name";
    leaf name { type string; }
    leaf admin-state { type enumeration; }
    leaf description { type string; }
  }
}
```

#### XML returned:

```xml
<data>
  <interface xmlns="urn:nokia.com:srlinux:interfaces">
    <ethernet>
      <name>ethernet-1/1</name>
      <admin-state>enable</admin-state>
      <description>Core Link</description>
    </ethernet>
  </interface>
</data>
```

#### Differences You'll Notice

OpenConfig (cEOS) | SR Linux
---|---
Deep config/state split | Often flatter
Uses standard namespace URLs | Uses vendor URNs
More hierarchical | Often more direct

#### Understanding Config vs State

Often you’ll see:

```xml
<interfaces>
  <interface>
    <config>...</config>
    <state>...</state>
  </interface>
</interfaces>
```

**Why?**

OpenConfig separates:

- `config` → intended configuration
- `state` → operational values (read-only)

If you use `<get-config>`, you usually retrieve only `config`.

If you use `<get>`, you retrieve both.


## Namespaces in Detail

You may also see prefixed namespaces:

```xml
<oc-if:interfaces
   xmlns:oc-if="http://openconfig.net/yang/interfaces">
```

This happens when:

- Multiple YANG modules are used in one payload
- The device includes augmentations

Example:

```xml
<interfaces xmlns="http://openconfig.net/yang/interfaces">
  <interface>
    <name>Ethernet1</name>
    <ethernet xmlns="http://openconfig.net/yang/interfaces/ethernet">
      <config>
        <port-speed>SPEED_100GB</port-speed>
      </config>
    </ethernet>
  </interface>
</interfaces>
```

Different namespace → different YANG module.

## How to Read Any `<get-config>` XML

When teaching or analyzing, follow this order:

1. Identify the namespace → which YANG module?
2. Identify top-level container
3. Identify lists and their keys
4. Separate config vs state
5. Map XML elements back to YANG definitions
6. Check for augmentations (extra namespaces)


## Mental Model for Students

Think of it as:

```
NETCONF Envelope
    ↓
<data>
    ↓
YANG root container
    ↓
Hierarchy defined by YANG
    ↓
Leaves = actual configuration values
```

## Key Insight (Very Important)

The XML is NOT arbitrary.

It is:

> A deterministic serialization of the YANG schema tree.

If you know the YANG model, you can predict the XML.
If you see the XML, you can reconstruct the YANG tree.

