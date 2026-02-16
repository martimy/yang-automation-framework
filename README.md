<!--Course Edition 1.0-->
 
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
4.	Apply the three-layer software architecture to write portable automation code
5.	Safely push configuration to devices using candidate datastores and confirmed-commit
6.	Extend a working codebase to cover interfaces, NTP, and SNMP
7.	Test all workflows against virtual devices in Containerlab before touching production
 
# Module 1: The Mental Model — You Are Not Writing Config

The single most important shift in moving to model-driven automation is conceptual. When you type commands into a CLI, you are constructing vendor-specific syntax that the device parses into an internal data structure. Model-driven automation skips the middle step: you write directly to that data structure. The CLI is merely one serialization of that structure. YANG, NETCONF, and gNMI give you direct access to the model itself.

## What is YANG?
YANG (Yet Another Next Generation) is a data modelling language defined in RFC 6020 and revised in RFC 7950. It describes the structure, types, constraints, and relationships of configuration and operational data for network devices. Think of a YANG model the way you would think of a database schema: it defines what data exists, what type each field must be, which fields are mandatory, and how data elements relate to each other.

A YANG model does NOT contain any configuration values. It only describes the shape of the data. The values — your router ID, your OSPF area, your interface IP — are provided separately in an XML or JSON document that conforms to the model.

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
We recommend using Python virtual environment

```bash
sudo apt-get install python3.10-venv
python3 -m venv .ylab
source .ylab/bin/activate
```

```bash
pip install six
pip install netconf-console2
pip install pyang
```

### Defining a Topology

A Containerlab topology is a YAML file. The example below creates a two-node lab with one Nokia SR-Linux router and one Arista cEOS router connected back-to-back. This is your primary lab environment for the entire course:

*topology.yml*

```
name: yang-course

topology:
  nodes:
    srlinux:
      kind: nokia_srlinux
      image: ghcr.io/nokia/srlinux:latest
    ceos:
      kind: arista_ceos
      image: ceos:latest

  links:
    - endpoints: ["srlinux:e1-1", "ceos:eth1"]
```

Start the lab with:

```
sudo containerlab deploy -t topology.yml
```

> Instructor Note
Have students verify NETCONF connectivity immediately after deploying the lab using a simple ncclient get_capabilities() call. This confirms SSH is reachable, credentials are correct, and the device is advertising NETCONF support before any config work begins.

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

> What Both Commands Are Actually Doing
NETCONF is always transported over SSH. Specifically, it uses SSH's subsystem mechanism, named 'netconf'. So both commands above are ultimately opening an SSH connection and requesting the netconf subsystem. The difference is only in who is doing the SSH work.
netconf-console2 is a dedicated NETCONF client. It handles the SSH transport internally, sends a proper NETCONF <hello> message with its own capabilities, waits for the device's <hello> in response, and then presents the result to you cleanly. It understands the NETCONF framing protocol (the ]]>]]> end-of-message marker in NETCONF 1.0, or chunked framing in 1.1).
ssh -s netconf is raw SSH. It opens the subsystem channel but does nothing after that. You are dropped directly into the NETCONF session at the XML layer. The device sends its <hello> message immediately, and then waits for yours. If you just sit there, nothing further happens — you would need to type raw XML to continue. It is useful for confirming the port is open and the device is responding, but it is not a practical way to send operations.



: Lab Environment Summary

Component | Purpose in This Course
---|-----
Containerlab | Orchestrates virtual network nodes as Docker containers
Nokia SR-Linux & Arista cEOS | Configuration targets to demonstrate vendor differences in Translation Layer
netconf-console2 | A dedicated NETCONF client. It handles the SSH transport 
Python 3 + venv | All automation scripts; isolate dependencies per lab
ncclient | Python NETCONF transport library
pyang | 
pygnmi | Python gNMI transport library
libyang2-tools

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

## Technique 4: The Reverse Engineering Discipline
A reliable and fast path to a working payload is to configure the feature manually via CLI first, then use a NETCONF get-config to read back exactly how the device represents that configuration in YANG. This approach is especially valuable when vendor documentation is unclear or when you are working with a native model for the first time:

```python
# Get the full running configuration as YANG/XML
with manager.connect(**conn_params) as m:
    config = m.get_config(source='running')
    print(config.data_xml)
```


Read the output carefully. The namespace declarations, element names, and hierarchy you see in that XML are exactly what your payload must reproduce. Save this output as a reference alongside the `pyang` tree.

### Lab Exercise: Discover the Interface Model

Deploy your Containerlab topology. Configure one interface with an IP address manually using the device CLI. Then perform a `get-config` and locate the interface configuration in the XML output. Cross-reference it with the `pyang` tree for ietf-interfaces and openconfig-if-ip. Document the exact YANG path and namespace you will need to construct a payload for this interface.
 
> Note that SR-Linux requires that your you configure at least one sub-interface and the sub-interface must be associated with a network-instance (i.e. VRF).

```bash
        <interface xmlns="urn:nokia.com:srlinux:chassis:interfaces">
            <name>ethernet-1/1</name>
            <description>To ceos-01</description>
            <admin-state>enable</admin-state>
            <subinterface>
                <index>0</index>
                <ipv4>
                    <address>
                        <ip-prefix>192.168.1.1/24</ip-prefix>
                        <primary/>
                    </address>
                </ipv4>
            </subinterface>
        </interface>
        ...
        <network-instance xmlns="urn:nokia.com:srlinux:net-inst:network-instance">
            <name>vrf1</name>
            <interface>
                <name>ethernet-1/1.0</name>
            </interface>
        </network-instance>
```

```
module: ietf-interfaces
  +--rw interfaces
  |  +--rw interface* [name]
  |     +--rw name                        string
  |     +--rw description?                string
  |     +--rw type                        identityref
  |     +--rw enabled?                    boolean
  |     +--rw link-up-down-trap-enable?   enumeration {if-mib}?
```

For the IP module, you will need to download the dependencies:

```bash
$ git clone https://github.com/openconfig/public openconfig
```


```bash
pyang -f tree openconfig-if-ip.yang -p openconfig
module: openconfig-if-ip

  augment /oc-if:interfaces/oc-if:interface/oc-if:subinterfaces/oc-if:subinterface:
    +--rw ipv4
       +--rw addresses
       |  +--rw address* [ip]
       |     +--rw ip        -> ../config/ip
       |     +--rw config
       |     |  +--rw ip?              oc-inet:ipv4-address
       |     |  +--rw prefix-length?   uint8
       |     |  +--rw type?            ipv4-address-type
```

```
 pyang -f tree -p openconfig  openconfig-if-ip.yang --tree-path addresses --tree-depth 5
```

## Module 4: The Three-Layer Software Architecture

The fundamental design mistake in most network automation codebases is mixing what you want to configure, how it is represented in YANG, and how it is delivered over the wire into a single block of code. This creates brittle, unportable scripts. The three-layer architecture solves this by giving each concern its own isolated layer, so a change in one never requires a change in the others.



: Layer Overview

Layer | Responsibility
---|------
Intent Layer | Expresses what you want in pure business terms. No YANG, no XML, no vendor knowledge. Uses Python dataclasses. Readable by a network engineer who has never heard of NETCONF.
Translation Layer | Maps an Intent object onto a specific YANG model and renders it as an XML or JSON payload. This is where vendor differences are handled. One translator class per feature per vendor.
Transport Layer | Delivers payloads to the device over NETCONF or gNMI. Manages connections, handles datastores, commits, and rollbacks. Has no knowledge of what the payload contains.

**The Intent Layer**

An Intent dataclass describes the desired state of one feature on one device. It uses plain Python types: strings, integers, booleans, and lists. Here is the InterfaceIntent class annotated for clarity:

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class InterfaceIntent:
    name: str              # e.g. 'eth1'
    description: str
    ip_address: str        # e.g. '192.168.1.1'
    prefix_length: int     # e.g. 24
    enabled: bool = True
    mtu: int = 1500
```

The power of this layer is in its readability. A network architect can review this class and instantly understand what parameters drive the deployment, without reading a single line of XML or YANG.

**Adding More Intent Classes**

As your automation grows to cover more features, you add one dataclass per concern. Each one remains small and focused. A device's complete desired state becomes a collection of intent objects that the orchestrator assembles and passes to the appropriate translators:

```python
@dataclass
class OspfIntent:
    process_id: int          # e.g. 1
    area_id: str             # e.g. '0.0.0.0' for the backbone
    router_id: str           # e.g. '10.255.255.1'
    interfaces: List[str]    # e.g. ['eth1', 'eth2']
    passive_interfaces: List[str] = field(default_factory=list)
    redistribute_connected: bool = False

@dataclass
class NtpIntent:
    servers: List[str]     # list of NTP server IPs
    source_interface: str

@dataclass
class SnmpIntent:
    version: str           # 'v2c' or 'v3'
    community: str         # v2c community string
    trap_destinations: List[str]
    location: str
    contact: str
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
          <name>{{ name }}</name>
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

**Avoid CLI Leakage**

Never embed vendor-specific CLI strings inside a Jinja2 template. A string like 'ip address 192.168.1.1 255.255.255.0' inside your XML payload is called CLI leakage. It destroys portability because you are mixing two config paradigms. The payload must contain only element names and values from the YANG model.

**The Transport Layer**

The transport layer is the cleanest of the three. It knows nothing about OSPF, interfaces, or NTP. It only knows about connections, datastores, and NETCONF operations. This separation means you can swap NETCONF for gNMI without touching a single translator:

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
            else:
                m.commit()
            return True
```

**The Impact Matrix**

The real payoff of this architecture becomes clear when you need to make changes. Notice how each type of change is completely contained within one layer:

Change Needed | Intent | Translation | Transport
---|----|---|--
Add a new router vendor | No change | New translator class | No change
Switch NETCONF to gNMI | No change | No change | New transport class
Change OSPF area design | Update dataclass | No change | No change
Upgrade YANG model version | No change | Update template | No change
Add NTP to all devices | New Intent | New translator | No change


### Lab 4: Build Your First Translator

Lab Exercise

Write an InterfaceIntent dataclass and an IetfInterfaceTranslator for your SR-Linux node. Use the YANG path you discovered in Lab 3. Push the configuration using the NetconfTransport class and verify it with a get-config call. Then write a CeosInterfaceTranslator using the native Arista model and push the same intent to the cEOS node. Observe that the intent object is identical; only the translator class changes.
 
# Module 5: Safe Configuration Delivery

Writing the correct payload is only half the problem. Delivering it safely — in a way that is atomic, reversible, and validated before it takes effect — is equally important. NETCONF's datastore model gives you the tools to do this correctly. Using them is not optional in production environments.

The NETCONF Datastore Model
NETCONF distinguishes between three datastores. Understanding when each is used is fundamental:

Datastore | Purpose
running | The active configuration currently in use by the device. Changes here take effect immediately. Direct writes to running should be avoided in production.
candidate | A staging area for changes. You can write, validate, and test here without affecting the live device. The candidate is promoted to running only on explicit commit.
startup | The configuration loaded on boot. Not all devices implement this. Relevant for ensuring changes persist across a reboot.

The Get-Before-Set Pattern
Never push a configuration blindly. Before any edit operation, retrieve the current state of the configuration subtree you are about to modify. This gives you a baseline, confirms the device's current state matches your assumptions, and helps you build a minimal diff rather than a full replacement payload:

```
INTERFACE_FILTER = '''
  <interfaces xmlns='urn:ietf:params:xml:ns:yang:ietf-interfaces'>
    <interface><name>eth1</name></interface>
  </interfaces>
'''
```

current_state = transport.get_config(INTERFACE_FILTER)
# Inspect current_state before building your edit payload

The Candidate, Validate, Commit Sequence
The correct production sequence for pushing configuration is a three-step process. Skipping any step introduces risk:

8.	Edit candidate — write your payload to the candidate datastore. The running config is not touched.
9.	Validate — ask the device to validate the entire candidate datastore against its YANG schemas. If the device rejects the validation, nothing has changed on the running config.
10.	Commit — promote the validated candidate to running. All changes in the candidate take effect atomically; either everything applies or nothing does.

Confirmed-Commit: Your Production Safety Net
The confirmed-commit extension is one of the most important safety mechanisms in NETCONF. When you issue a confirmed commit, the device applies your changes but sets a timer. If you do not send a confirming commit before the timer expires, the device automatically reverts to the previous configuration. This prevents you from accidentally locking yourself out of a device:

# Confirmed commit with 2-minute rollback window
m.commit(confirmed=True, timeout='120')

# ... verify your changes work correctly ...

# Send the confirming commit to make the change permanent
m.commit()

Production Rule
Always use confirmed-commit in production. The two-minute timeout is a seatbelt: the cost of sending one extra commit() call is trivial; the cost of a wrong config locking you out of a core router is not. Build the confirming commit into your verification step so it only fires after your validation checks pass.

Offline Validation with yanglint
Before a payload ever touches a device, you can validate it locally against the YANG schema using yanglint. This catches structural errors, missing mandatory fields, and type mismatches without consuming a device connection:

# Install libyang (provides yanglint)
apt install libyang-tools   # Ubuntu/Debian
brew install libyang        # macOS

# Validate your payload XML against the schema
yanglint ietf-interfaces.yang payload.xml

Lab 5: Safe Delivery Workflow
Lab Exercise
Take the translator you built in Lab 4 and wrap it in the full candidate/validate/confirmed-commit sequence. Deliberately introduce an error into your payload (use an invalid IP address format or omit a mandatory field) and observe how yanglint and the device's validation catch it at different stages. Verify that the running config is unchanged after a failed validation.
 
# Module 6: Extending the Framework to Interfaces, NTP, and SNMP
With the three-layer architecture and the safe delivery workflow established, extending your automation to new features follows a predictable, repeatable pattern. This module walks through the high-level approach for the most common infrastructure features, highlighting the key YANG models and the practical challenges you will encounter for each.

The Extension Pattern
For every new feature, follow the same four steps before writing any code:

11.	Discover — run pyang on the relevant YANG model and read the tree
12.	Reverse-engineer — configure the feature via CLI, then get-config to see its YANG representation
13.	Add an Intent class — write a dataclass that captures the parameters a network engineer would care about
14.	Write translators — one translator class per vendor, per feature, mapping the intent to the correct YANG path

Interface Configuration
Interfaces are the best-supported feature across all vendors from a standards perspective. The ietf-interfaces model (RFC 7223) covers admin state, description, and MTU. IP addressing is handled by ietf-ip (RFC 8344), which augments the interface model. These two modules work together and are widely implemented.

The enabled leaf in ietf-interfaces maps directly to the admin up/down state of an interface. It is a simple boolean, making it one of the easiest fields to automate. Setting it to true is equivalent to no shutdown in IOS or set admin-state enable in SR-Linux.

Key YANG paths to memorise for interfaces:
- /interfaces/interface[name]/enabled — admin state
- /interfaces/interface[name]/description — interface description
- /interfaces/interface[name]/ipv4/address[ip]/prefix-length — IPv4 addressing
- /interfaces/interface[name]/ipv6/address[ip]/prefix-length — IPv6 addressing

Practical Note
When configuring both the interface admin state and its IP address in the same operation, include both the ietf-interfaces and ietf-ip namespaces in the same payload. They can be combined in a single edit-config call, and committing them atomically is cleaner than two separate commits.

NTP Configuration
NTP is the first feature where you will encounter significant divergence between vendors. The IETF NTP model (RFC 9249, ietf-ntp) is relatively new and vendor support varies considerably. Nokia SR-Linux implements a reasonable subset. Cisco IOS-XE and Arista both have more mature native NTP models that expose more knobs.

For your translator registry, the practical approach is to implement an IetfNtpTranslator for vendors that support it and fall back to a native translator for those that do not. Your InterfaceIntent remains identical in both cases; only the translator class changes.

Key parameters to capture in NtpIntent: list of server IPs or hostnames, the source interface for NTP packets, authentication mode and keys if required, and whether to use burst mode. Most production deployments need at least two NTP servers for redundancy.

SNMP Configuration
SNMP is the most vendor-divergent feature you will encounter in this framework. The ietf-snmp model exists but is inconsistently implemented, meaning you will almost always be working with native YANG models. This is expected and acceptable — the three-layer architecture is specifically designed for this situation. Your SnmpIntent class is clean and portable; the complexity is entirely isolated in the translation layer.

For SNMPv2c, the critical parameters are the community string, the list of trap destinations with their community strings, and the system location and contact. For SNMPv3, replace community strings with USM user configurations, authentication protocols (MD5 or SHA), and privacy protocols (DES or AES).

Recommended approach for SNMP in this framework:
- Build native translators for each vendor rather than fighting a poorly-supported IETF model
- Keep the SnmpIntent class version-agnostic by including both v2c and v3 parameters and letting the translator use whichever fields are relevant
- Validate SNMP trap delivery as part of your post-commit verification step

The Translator Registry
As your feature coverage grows, the orchestrator needs a way to select the correct translator for a given vendor and feature combination. A simple nested dictionary serves this purpose well. The outer key is the vendor identifier, the inner key is the feature name, and the value is an instantiated translator object:

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

Lab 6: Full Device Bring-Up
Lab Exercise
Write a complete bring-up script for your SR-Linux node that configures, in order: interfaces with IP addresses, OSPF on those interfaces, an NTP server, and a basic SNMPv2c community. Use the full candidate/validate/confirmed-commit workflow. After the commit, verify each feature using a targeted get-config subtree filter. This is a realistic simulation of a Day 1 provisioning script.
 
# Module 7: Recommended Open-Source Tooling
A reliable model-driven automation workflow depends on a specific set of open-source tools. Each tool in the list below addresses a distinct problem in the workflow. You do not need all of them immediately, but you should know what each one does and when to reach for it.

Network Emulation
Tool	Description
Containerlab	The foundation of your lab environment. Defines network topologies in YAML and runs them as Docker containers. Supports Nokia SR-Linux, Arista cEOS, Cisco XRd, VyOS, and many others. Essential for testing any automation workflow before touching production hardware. containerlab.dev

NETCONF Transport
Tool	Description
ncclient	The standard Python library for NETCONF. Handles SSH transport, capability exchange, all NETCONF RPCs (get, get-config, edit-config, commit, lock, validate), and datastore management. The library most automation code in this course is built on. pip install ncclient
netconf-console	A command-line NETCONF client for quick interactive testing and debugging. Useful for ad-hoc get-schema retrievals and testing filters without writing Python. Available via pip.

gNMI Transport
Tool	Description
pygnmi	A pure-Python gNMI client library. Supports Get, Set, Subscribe, and Capabilities RPCs. Integrates cleanly with the Transport Layer pattern used in this course. pip install pygnmi
gnmic	A feature-rich gNMI command-line client written in Go. Excellent for interactive exploration, subscription testing, and building gNMI-based telemetry pipelines. Available from gnmic.openconfig.net

YANG Model Tools
Tool	Description
pyang	The essential YANG toolkit. Parses YANG modules and renders them in multiple formats including the tree format used throughout this course. Also validates YANG syntax and converts between YANG and YIN. pip install pyang
yanglint	A command-line YANG data validator from the libyang project. Validates XML and JSON payloads against a YANG schema offline, before they touch a device. Included in the libyang package available via apt and brew.
yangson	A Python library for working with YANG-modelled data. Useful for programmatic validation and data manipulation within Python automation scripts. pip install yangson
YANG Catalog	A web-based repository and search engine for IETF, OpenConfig, and vendor YANG models. Use it to find model versions, check vendor support, and browse module dependencies before downloading from a device. yangcatalog.org

Payload Templating and Rendering
Tool	Description
Jinja2	The industry-standard Python templating engine. Used in this course to separate YANG payload structure from variable data. Supports conditionals, loops, and filters, making it ideal for generating complex XML with optional elements. pip install jinja2
xmltodict	Converts between XML strings and Python dictionaries. Essential for parsing get-config responses into data structures your Python code can inspect and compare. pip install xmltodict

Development and Debugging
Tool	Description
ncclient with manager.logger	Enable DEBUG logging in ncclient to see the raw XML sent and received over the wire. Invaluable for debugging payload issues and understanding exactly what the device returns.
VSCode with YANG extension	The YANG language support extension for Visual Studio Code provides syntax highlighting, tree navigation, and basic validation for .yang files. Makes browsing large vendor model repositories much more productive.
git	Version control for your intent dataclasses, translators, and topology files. Every change to your automation codebase should be committed. The diff history is your audit trail for what changed on the network and when.

Higher-Level Frameworks (For Reference)
Tool	Description
Nornir	A pure-Python automation framework with a plugin architecture. Handles inventory management, parallel task execution, and result reporting. The three-layer pattern in this course integrates naturally as Nornir tasks.
Napalm	A vendor-neutral network automation library that abstracts common operations. Useful as a reference for how vendor abstraction is handled at scale, and supports some NETCONF operations natively.
Ansible network modules	Ansible includes NETCONF and gNMI modules. Useful for teams already invested in Ansible, though the YAML-based playbook format makes the three-layer architecture harder to enforce cleanly.
 
# Module 8: Teaching Guide and Course Delivery Notes
This module is addressed directly to the instructor. It contains recommendations for sequencing the lab exercises, common student misconceptions to address early, and suggestions for adapting the course to different audiences.

Before You Teach: Try Everything Yourself
The most important preparation step is to complete every lab exercise on your own workstation before teaching it. The model discovery process, in particular, produces different output on different device software versions, and you need to know what your specific Containerlab images will return. Document the exact pyang tree output for ietf-interfaces and ietf-ospf on your specific SR-Linux version, and use that output as the ground truth in your instruction.

Common issues to discover and resolve before class:
- SR-Linux and cEOS image availability: ensure students can pull both images before the first lab session
- Docker resource limits: each Containerlab node needs approximately 512MB RAM; set expectations for minimum workstation specs
- SSH key handling: ncclient's hostkey_verify=False is acceptable in lab; explain why this setting must never appear in production code

Common Student Misconceptions
"YANG is a configuration language." Correct this early. YANG is a schema language. It describes the shape of data, not the data itself. The analogy to a database schema or JSON Schema is effective.

"I can just use NETCONF to send CLI commands." Some older device implementations allow this via the netconf-config-change or exec-command RPCs. This is not model-driven automation — it is CLI-over-SSH with extra steps. Show students what CLI leakage looks like in a payload and explain why it breaks portability.

"The IETF model is always the right choice." Vendor support for IETF models is uneven. Some features have no IETF model at all. Teaching students to check the device's advertised capabilities and fall back gracefully to native models is more valuable than insisting on standards-only.

Recommended Lab Sequencing
15.	Lab 2: Containerlab deployment and NETCONF connectivity verification
16.	Lab 3: Model discovery — get-schema, pyang tree, reverse-engineer an interface
17.	Lab 4: Build InterfaceIntent, translator, and transport; push to SR-Linux
18.	Lab 4b: Write a second translator for the same intent targeting cEOS
19.	Lab 5: Wrap Lab 4 in the full confirmed-commit safety workflow; test rollback
20.	Lab 6: Full bring-up script covering interface, OSPF, NTP, and SNMP

Adapting for Different Audiences
For network engineers new to Python: spend additional time on the dataclass syntax and the concept of type hints. The Intent layer is the right entry point because it looks like structured data, not code.

For developers new to networking: spend additional time on the datastore model, the difference between candidate and running, and why atomic commits matter. The database transaction analogy maps well to their existing mental models.

For teams evaluating vendor selection: the Blast Radius Matrix in Module 4 is a compelling visual for showing how the three-layer architecture reduces vendor lock-in. Demonstrating the same InterfaceIntent object driving both SR-Linux and cEOS in Lab 4b makes the abstraction concrete.
 
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

---

## Appendix - The Primary References

**OpenConfig YANG Models on GitHub**
`github.com/openconfig/public/tree/master/release/models`
This is the canonical source. For interfaces specifically, look at:
- `interfaces/openconfig-interfaces.yang` — the base model
- `interfaces/openconfig-if-ip.yang` — the IPv4/IPv6 augmentation

Reading the YANG source directly is often the most reliable reference because it shows you the exact container names, list keys, and mandatory fields. The comments in OpenConfig YANG files are also unusually good compared to vendor models.

**OpenConfig Website**
`openconfig.net`
Has working group documentation and model overviews, though it is less detailed than the YANG source itself.

---

## The Most Practical Reference for Payload Structure

**OpenConfig Path and RPC Reference on GitHub**
`github.com/openconfig/gnmi/blob/master/proto/gnmi/gnmi.proto`
More useful for gNMI, but the path conventions carry over to NETCONF payloads.

The single most useful exercise is to use **gnmic** to GET a path interactively and read the JSON response — the JSON structure maps directly to the XML config/state pattern you are learning:

```bash
gnmic -a ceos-01:6030 -u admin -p admin --insecure \
  get --path /interfaces/interface[name=Ethernet1]
```

The JSON response shows you the exact hierarchy including all `config` and `state` wrappers, which you then translate directly into XML for NETCONF.

---

## Vendor-Specific OpenConfig Documentation

This is often more useful than the generic OpenConfig docs because it tells you exactly which parts of the model a specific device actually implements:

**Arista cEOS**
`arista.com/en/support` → EOS Central → search "NETCONF/YANG guide"
Arista also publishes their supported YANG paths in a spreadsheet format per EOS version, which is the fastest way to check if a specific OpenConfig path is implemented.

**Nokia SR-Linux**
`documentation.nokia.com/srlinux`
SR-Linux has excellent YANG documentation including an interactive model browser at `yang.srlinux.dev` where you can browse the full tree in a web UI without needing pyang at all. Highly recommended.

---

## The config/state Pattern Specifically

The OpenConfig config/state convention is formally described in the OpenConfig style guide:
`github.com/openconfig/public/blob/master/doc/openconfig_style_guide.md`

Section 4 covers the config/state pattern in detail. Reading this once will make every OpenConfig payload you write from that point forward much more predictable, because the pattern is applied consistently across every OpenConfig model without exception.

---

## Recommended Order of Consultation

For any new feature you are translating, consult in this order:

| Step | Reference | Why |
|---|---|---|
| 1 | Vendor YANG support matrix | Confirm the path is actually implemented |
| 2 | OpenConfig YANG source on GitHub | Understand the model structure |
| 3 | OpenConfig style guide | Understand config/state conventions |
| 4 | gnmic GET on live device | See the actual data the device returns |
| 5 | pyang tree with OC models | Confirm your path before writing the payload |

The gnmic GET step is the closest equivalent to the NETCONF reverse-engineering discipline you already know — it shows you exactly what the device returns for a given path, which is your ground truth for building the payload.


---

This is the most important architectural question in the entire course, and you have arrived at it through real hands-on experience which is exactly the right way. What you have discovered is the difference between **model portability** and **operational portability**. The YANG model may be the same (OpenConfig ipv4) but the *sequence of operations* and *prerequisite state* required to achieve a working interface differs significantly between vendors.

---

## The Core Problem

Your current three layers handle payload translation well but have no concept of **operation ordering** or **prerequisite dependencies**. A working SR-Linux interface requires three sequential operations that are invisible to the current design:

```
1. Create subinterface (ethernet-1/1.0)
2. Create network-instance (default or custom VRF)
3. Bind subinterface to network-instance
```

While cEOS requires:
```
1. Enable ip routing
2. Push interface + IP (no switchport happens implicitly)
```

Neither of these sequencing requirements belongs in the Intent, Translation, or Transport layer as currently designed. They need a fourth concept.

---

## The Solution: Add a Device Bootstrap and an Orchestration Layer

The full architecture needs two additions:

```
┌─────────────────────────────────────┐
│         INTENT LAYER                │  What you want (unchanged)
├─────────────────────────────────────┤
│       ORCHESTRATION LAYER           │  NEW — sequences operations
│   (vendor-aware workflow engine)    │  per vendor, resolves dependencies
├─────────────────────────────────────┤
│       TRANSLATION LAYER             │  How to express it in YANG
│   (now includes prerequisite        │  (extended with prereq translators)
│    translators per vendor)          │
├─────────────────────────────────────┤
│       TRANSPORT LAYER               │  Wire protocol (unchanged)
└─────────────────────────────────────┘
```

---

## The Orchestration Layer

This is the key new addition. Its job is to know the **recipe** for achieving a working interface on each vendor — the correct sequence of payloads, in the correct order, with the correct dependencies resolved before each step:

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

```python
class CeosOrchestrator(DeviceOrchestrator):
    """
    cEOS recipe:
    1. Enable ip routing (bootstrap, once per device)
    2. Push interface + IP in a single payload
    """
    def bootstrap(self) -> bool:
        # ip routing is a global prerequisite on cEOS
        payload = self.translators['global'].translate_routing(
            GlobalRoutingIntent(enabled=True)
        )
        return self.transport.push_config(payload)

    def configure_interface(self, intent: InterfaceIntent) -> bool:
        # Single payload covers interface + IP + implicit no switchport
        payload = self.translators['interface'].translate(intent)
        return self.transport.push_config(payload)
```

```python
class SrlinuxOrchestrator(DeviceOrchestrator):
    """
    SR-Linux recipe:
    1. Create subinterface on the parent interface
    2. Create or verify network-instance exists
    3. Bind subinterface to network-instance
    All three must succeed in order.
    """
    def bootstrap(self) -> bool:
        # SR-Linux has a default network-instance already
        # but we verify it exists before proceeding
        return True

    def configure_interface(self, intent: InterfaceIntent) -> bool:
        # Step 1: Create the subinterface with IP
        subif_payload = self.translators['subinterface'].translate(intent)
        self.transport.push_config(subif_payload)

        # Step 2: Ensure the network-instance exists
        ni_payload = self.translators['network_instance'].translate(
            NetworkInstanceIntent(
                name=intent.network_instance,
                type='L3'
            )
        )
        self.transport.push_config(ni_payload)

        # Step 3: Bind subinterface to network-instance
        binding_payload = self.translators['ni_interface'].translate(
            NiInterfaceBindingIntent(
                network_instance=intent.network_instance,
                interface=intent.name,
                subinterface=intent.subinterface_index
            )
        )
        return self.transport.push_config(binding_payload)
```

---

## Extended Intent Classes

The InterfaceIntent needs a few new fields to carry SR-Linux concepts that cEOS does not need. The orchestrator decides which fields to use:

```python
@dataclass
class InterfaceIntent:
    name: str                        # 'Ethernet1' or 'ethernet-1/1'
    description: str
    ip_address: str
    prefix_length: int
    enabled: bool = True
    # SR-Linux specific — ignored by cEOS orchestrator
    subinterface_index: int = 0
    network_instance: str = 'default'

@dataclass
class NetworkInstanceIntent:
    name: str                        # 'default', 'MGMT', custom VRF name
    type: str = 'L3'                 # 'L3', 'L2', 'VPWS' etc.
    description: str = ''

@dataclass
class NiInterfaceBindingIntent:
    network_instance: str
    interface: str                   # parent interface name
    subinterface: int = 0            # subinterface index
```

---

## The Translator Registry Gets Vendor Buckets

Each vendor now has its own set of translators, some shared (where OpenConfig is truly common) and some unique:

```python
TRANSLATORS = {
    'ceos': {
        'interface':         OpenConfigInterfaceTranslator(),
        'global':            CeosGlobalRoutingTranslator(),
    },
    'srlinux': {
        'subinterface':      SrlinuxSubinterfaceTranslator(),
        'network_instance':  SrlinuxNetworkInstanceTranslator(),
        'ni_interface':      SrlinuxNiInterfaceBindingTranslator(),
    }
}

ORCHESTRATORS = {
    'ceos':    CeosOrchestrator,
    'srlinux': SrlinuxOrchestrator,
}
```

---

## The Updated Orchestrator Entry Point

The top-level script becomes clean and vendor-agnostic again:

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
            print(f"✓ {device['host']} — {intent.name} configured")

provision_all()
```

---

## How the Blast Radius Matrix Looks Now

| Change needed | Intent | Orchestration | Translation | Transport |
|---|---|---|---|---|
| Add new vendor | Maybe new fields | New orchestrator class | New translators | No change |
| SR-Linux changes NI binding sequence | No change | Update SrlinuxOrchestrator | No change | No change |
| cEOS drops the routing prerequisite | No change | Update CeosOrchestrator | No change | No change |
| Add IPv6 support | Add IPv6 fields | Minor update | New template | No change |
| Switch to gNMI transport | No change | No change | No change | New transport class |

---

## The Key Insight for Your Course

What you discovered through hands-on troubleshooting is the distinction between two types of vendor differences:

**Type 1 — Model differences:** Same feature, different YANG representation. Handled by different translator classes. You already solved this.

**Type 2 — Operational differences:** Same goal, different sequence of prerequisite operations. This is what the Orchestration Layer solves. No amount of payload translation can fix a missing network-instance binding or a disabled routing table — those are sequencing problems, not encoding problems.

The Orchestration Layer is where that operational knowledge lives, isolated from everything else, one class per vendor, easy to read and easy to change.



---

```
yang_course/
│
├── main.py                        # Entry point — runs provision_all()
├── device_registry.py             # List of devices, their vendor, and their intents
│
├── intent/                        # Layer 1 — pure business logic
│   ├── __init__.py
│   ├── interface.py               # InterfaceIntent
│   ├── routing.py                 # GlobalRoutingIntent, OspfIntent
│   ├── network_instance.py        # NetworkInstanceIntent, NiInterfaceBindingIntent
│   ├── ntp.py                     # NtpIntent
│   └── snmp.py                    # SnmpIntent
│
├── translation/                   # Layer 2 — YANG payload generation
│   ├── __init__.py
│   ├── base.py                    # Abstract Translator base class
│   ├── ceos/
│   │   ├── __init__.py
│   │   ├── interface.py           # OpenConfigInterfaceTranslator
│   │   └── routing.py             # CeosGlobalRoutingTranslator
│   ├── srlinux/
│   │   ├── __init__.py
│   │   ├── subinterface.py        # SrlinuxSubinterfaceTranslator
│   │   ├── network_instance.py    # SrlinuxNetworkInstanceTranslator
│   │   └── ni_binding.py          # SrlinuxNiInterfaceBindingTranslator
│   └── templates/                 # Jinja2 XML templates
│       ├── ceos/
│       │   ├── interface.xml.j2
│       │   └── routing.xml.j2
│       └── srlinux/
│           ├── subinterface.xml.j2
│           ├── network_instance.xml.j2
│           └── ni_binding.xml.j2
│
├── orchestration/                 # Layer 3 — operation sequencing
│   ├── __init__.py
│   ├── base.py                    # Abstract DeviceOrchestrator base class
│   ├── ceos.py                    # CeosOrchestrator
│   └── srlinux.py                 # SrlinuxOrchestrator
│
├── transport/                     # Layer 4 — wire protocol
│   ├── __init__.py
│   ├── base.py                    # Abstract Transport base class
│   ├── netconf.py                 # NetconfTransport
│   └── gnmi.py                    # GnmiTransport (when needed)
│
├── registry.py                    # TRANSLATORS and ORCHESTRATORS dicts
│
└── lab/                           # Containerlab and validation assets
    ├── topology.yml
    ├── ceos-startup.cfg
    └── yang/                      # Downloaded YANG models for yanglint
        ├── openconfig/
        └── ietf/
```

## Usefull commands

**Nokia display configuration in XML format**

```
A:admin@srl-01# info network-instance mgmt | as xml
<type xmlns="urn:nokia.com:srlinux:net-inst:network-instance">ip-vrf</type>
<admin-state xmlns="urn:nokia.com:srlinux:net-inst:network-instance">enable</admin-state>
<description xmlns="urn:nokia.com:srlinux:net-inst:network-instance">Management network instance</description>
<interface xmlns="urn:nokia.com:srlinux:net-inst:network-instance">
  <name>mgmt0.0</name>
</interface>
<protocols xmlns="urn:nokia.com:srlinux:net-inst:network-instance">
  <linux xmlns="urn:nokia.com:srlinux:linux:linux">
    <import-routes>true</import-routes>
    <export-routes>true</export-routes>
    <export-neighbors>true</export-neighbors>
  </linux>
</protocols>
```
