# Lab Exercise 1


```bash
$ python3 get_configuration.py
```

```xml
<?xml version="1.0" encoding="UTF-8"?><data xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
        <interfaces xmlns="http://openconfig.net/yang/interfaces">
            <interface>
                <name>ethernet-1/1</name>
                <config>
                    <name>ethernet-1/1</name>
                    <type xmlns:iana-if-type="urn:ietf:params:xml:ns:yang:iana-if-type">iana-if-type:ethernetCsmacd</type>
                    <enabled>true</enabled>
                </config>
                <subinterfaces>
                <!-- ommited -->
                </subinterfaces>
            </interface>
        </interfaces>
    </data>
```


```bash
$ pyang -f tree -p openconfig ietf-interfaces.yang
```

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

For the IP module, you will need to download the dependencies first:

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


# Code Examples


**Adding More Intent Classes**

As your automation grows to cover more features, you add one dataclass per concern. Each one remains small and focused. Here are additional intent classes that will be used by orchestrators:

```python
@dataclass
class NetworkInstanceIntent:
    name: str                        # 'default', 'MGMT', custom VRF name
    type: str = 'ip_vrf'
    description: str = ''

@dataclass
class NiInterfaceBindingIntent:
    network_instance: str
    interface: str                   # parent interface name
    subinterface: int = 0            # subinterface index

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


**cEOS Orchestrator — Simple Sequence**

Arista cEOS has minimal prerequisites. Once IP routing is enabled globally (a one-time bootstrap step), interfaces can be configured independently:

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

**SR-Linux Orchestrator — Complex Dependencies**

SR-Linux requires three sequential operations. The orchestrator ensures they happen in the correct order:

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


Here are the additional translators needed for SR-Linux orchestration:

```python
class SrlinuxSubinterfaceTranslator:
    TEMPLATE = Template('''
    <config>
      <interface xmlns="urn:nokia.com:srlinux:chassis:interfaces">
        <n>{{ name }}</n>
        <description>{{ description }}</description>
        <admin-state>{{ 'enable' if enabled else 'disable' }}</admin-state>
        <subinterface>
          <index>{{ subinterface_index }}</index>
          <ipv4>
            <address>
              <ip-prefix>{{ ip_address }}/{{ prefix_length }}</ip-prefix>
              <primary/>
            </address>
          </ipv4>
        </subinterface>
      </interface>
    </config>''')

    def translate(self, intent: InterfaceIntent) -> str:
        return self.TEMPLATE.render(**intent.__dict__)


class SrlinuxNetworkInstanceTranslator:
    TEMPLATE = Template('''
    <config>
      <network-instance xmlns="urn:nokia.com:srlinux:net-inst:network-instance">
        <n>{{ name }}</n>
        <type>{{ type }}</type>
        {% if description %}
        <description>{{ description }}</description>
        {% endif %}
      </network-instance>
    </config>''')

    def translate(self, intent: NetworkInstanceIntent) -> str:
        return self.TEMPLATE.render(**intent.__dict__)


class SrlinuxNiInterfaceBindingTranslator:
    TEMPLATE = Template('''
    <config>
      <network-instance xmlns="urn:nokia.com:srlinux:net-inst:network-instance">
        <n>{{ network_instance }}</n>
        <interface>
          <n>{{ interface }}.{{ subinterface }}</n>
        </interface>
      </network-instance>
    </config>''')

    def translate(self, intent: NiInterfaceBindingIntent) -> str:
        return self.TEMPLATE.render(**intent.__dict__)
```


**Interface Configuration**

Interfaces are the best-supported feature across all vendors from a standards perspective. The ietf-interfaces model (RFC 7223) covers admin state, description, and MTU. IP addressing is handled by ietf-ip or openconfig-if-ip. Both models augment the interface model and are widely implemented.

The enabled leaf in ietf-interfaces maps directly to the admin up/down state of an interface. It is a simple boolean, making it one of the easiest fields to automate. Setting it to true is equivalent to no shutdown in IOS or set admin-state enable in SR-Linux.

Key YANG paths to memorize for interfaces:

- /interfaces/interface[name]/enabled — admin state
- /interfaces/interface[name]/description — interface description
- /interfaces/interface[name]/ipv4/address[ip]/prefix-length — IPv4 addressing
- /interfaces/interface[name]/ipv6/address[ip]/prefix-length — IPv6 addressing

>**Practical Note**
When configuring both the interface admin state and its IP address in the same operation, include both the ietf-interfaces and ietf-ip namespaces in the same payload. They can be combined in a single edit-config call, and committing them atomically is cleaner than two separate commits.


**Configuring OSPF**

```bash
$ python3 get_capabilties.py | grep ospf
urn:nokia.com:srlinux:ospf:ospf?module=srl_nokia-ospf&revision=2025-10-31

$ python3 get_schema.py srl srl_nokia-ospf nokia
$ pyang -f tree -p srlinux nokia/srl_nokia-ospf.yang
```

```bash
enter candidate

set / interface system0 subinterface 0 ipv4 admin-state enable
set / interface system0 subinterface 0 ipv4 address 10.0.0.1/32
set / network-instance default interface system0.0
set / network-instance default protocols ospf instance main version ospf-v2
set / network-instance default protocols ospf instance main admin-state enable
set / network-instance default protocols ospf instance main router-id 10.0.0.1
set / network-instance default protocols ospf instance main area 0.0.0.0
set / network-instance default protocols ospf instance main area 0.0.0.0 interface ethernet-1/1.0
set / network-instance default protocols ospf instance main area 0.0.0.0 interface ethernet-1/1.0 admin-state enable
set / network-instance default protocols ospf instance main area 0.0.0.0 interface ethernet-1/2.0
set / network-instance default protocols ospf instance main area 0.0.0.0 interface ethernet-1/2.0 admin-state enable

commit now
```

```
SRL_OSPF = """
<network-instance xmlns="urn:nokia.com:srlinux:net-inst:network-instance">
    <protocols>
        <ospf xmlns="urn:nokia.com:srlinux:ospf:ospf"/>
    </protocols>
</network-instance>
"""
```


**Configuring NTP**

For cEOS

1. Get capabilities 

After some search, I found that NTP is part of openconfig-system model used by cEOS and SRLinux


2. Get schema

```bash
# Get the NTP model from the cEOS device and save it in folder 'arista'
$ python3 get_schema.py ceos openconfig-system arista
```


3. View the NTP subtree from the YANG model

```bash
$ pyang -f tree --tree-path system/ntp --tree-depth 5 -p openconfig arista/openconfig-system.yang 
module: openconfig-system
  +--rw system
     +--rw ntp
        +--rw config
        |  +--rw enabled?           boolean
        |  +--rw enable-ntp-auth?   boolean
        +--ro state
        |  +--ro enabled?           boolean
        |  +--ro enable-ntp-auth?   boolean
        |  +--ro auth-mismatch?     oc-yang:counter64
        +--rw ntp-keys
        |  +--rw ntp-key* [key-id]
        |     +--rw key-id    -> ../config/key-id
        |     +--rw config
        |     |     ...
        |     +--ro state
        |           ...
        +--rw servers
           +--rw server* [address]
              +--rw address    -> ../config/address
              +--rw config
              |     ...
              +--ro state
                    ...
```

4. Generate a skeleton configuration XML file with default values from the YANG model. This generate the XML for the whole model, so you will need to extract only the NTP part

```
$ pyang -f sample-xml-skeleton \
--sample-xml-skeleton-doctype=config --sample-xml-skeleton-defaults \
-p openconfig arista/openconfig-system.yang -o ntp.xml
``` 

*ntp.xml*

```xml
<?xml version='1.0' encoding='UTF-8'?>
<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <system xmlns="http://openconfig.net/yang/system">
    <ntp>
      <config>
        <enabled>false</enabled>
        <enable-ntp-auth>false</enable-ntp-auth>
      </config>
      <ntp-keys>
        <ntp-key>
          <key-id/>
          <config>
            <key-id/>
            <key-type/>
            <key-value/>
          </config>
        </ntp-key>
      </ntp-keys>
      <servers>
        <server>
          <address/>
          <config>
            <address/>
            <port>123</port>
            <version>4</version>
            <association-type>SERVER</association-type>
            <iburst>false</iburst>
            <prefer>false</prefer>
            <network-instance/>
            <source-address/>
            <key-id/>
          </config>
        </server>
      </servers>
    </ntp>
  </system>
</config>
```

The generated file will the basis for the translation template:

 server 0.ca.pool.ntp.org
	   server 1.ca.pool.ntp.org
	   server 2.ca.pool.ntp.org
	   server 3.ca.pool.ntp.org

For testing, I'll edit the file by updating or removing default values then push the configuration to the router.

```xml
<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <system xmlns="http://openconfig.net/yang/system">
    <ntp>
      <config>
        <enabled>true</enabled>
      </config>
      <servers>
        <server>
          <address>192.168.100.1</address>
          <config>
            <address>192.168.100.1</address>
            <network-instance>MGMT</network-instance>
          </config>
        </server>
      </servers>
    </ntp>
  </system>
</config>
```

5. Proceed to

- Update the YAML file *devices.yml*
- Create a NtpIntent
- Create a translator OpenconfigNtpTranslator
- Add the translator to the registry file
- Update the orchestrator
- Add the intent type to the provision code 


For SRLinux

1. Get capabilities

```bash
$ python3 get_capabilties.py srl | grep ntp
urn:nokia.com:srlinux:linux:ntp?module=srl_nokia-ntp&revision=2025-10-31
```


# Best strategy to get gnmic sturcture(?)

use gnmic and the values

```
gnmic -a srl-01 -u admin -p NokiaSrl1! -e json_ietf --skip-verify get --path /network-instance[name=default] -t config
[
  {
    "source": "srl-01",
    "timestamp": 1771631705654269293,
    "time": "2026-02-20T23:55:05.654269293Z",
    "updates": [
      {
        "Path": "srl_nokia-network-instance:network-instance[name=default]",
        "values": {
          "srl_nokia-network-instance:network-instance": {
            "admin-state": "enable",
            "interface": [
              {
                "name": "ethernet-1/1.0"
              },
              {
                "name": "ethernet-1/2.0"
              }
            ],
            "protocols": {
              "srl_nokia-ospf:ospf": {
                "instance": [
                  {
                    "admin-state": "enable",
                    "area": [
                      {
                        "area-id": "0.0.0.0",
                        "interface": [
                          {
                            "admin-state": "enable",
                            "interface-name": "ethernet-1/1.0"
                          },
                          {
                            "admin-state": "enable",
                            "interface-name": "ethernet-1/2.0"
                          }
                        ]
                      }
                    ],
                    "name": "main",
                    "router-id": "10.0.0.2",
                    "version": "srl_nokia-ospf-types:ospf-v2"
                  }
                ]
              }
            }
          }
        }
      }
    ]
  }
]
```


```
gnmic -a ceos-01:6030 -u admin -p admin -e json --insecure get --path /network-instances/network-instance[name=default] -t config
```

```
[
  {
    "source": "ceos-01:6030",
    "timestamp": 1771631817164999398,
    "time": "2026-02-20T23:56:57.164999398Z",
    "updates": [
      {
        "Path": "network-instances/network-instance[name=default]",
        "values": {
          "network-instances/network-instance": {
            "openconfig-network-instance:config": {
              "arista-netinst-augments:ipv4-routing-enabled": false,
              "arista-netinst-augments:ipv6-routing-enabled": false,
              "name": "default",
              "type": "openconfig-network-instance-types:DEFAULT_INSTANCE"
            },
            "openconfig-network-instance:mpls": {
              "global": {
                "reserved-label-blocks": {
                  "reserved-label-block": [
                    {
                      "config": {
                        "local-id": "bgp-sr",
                        "lower-bound": 900000,
                        "upper-bound": 965535
                      },
                      "local-id": "bgp-sr"
                    },
                    {
                      "config": {
                        "local-id": "dynamic",
                        "lower-bound": 100000,
                        "upper-bound": 362143
                      },
                      "local-id": "dynamic"
                    },
                    {
                      "config": {
                        "local-id": "isis-sr",
                        "lower-bound": 900000,
                        "upper-bound": 965535
                      },
                      "local-id": "isis-sr"
                    },
                    {
                      "config": {
                        "local-id": "l2evpn",
                        "lower-bound": 1036288,
                        "upper-bound": 1048575
                      },
                      "local-id": "l2evpn"
                    },
                    {
                      "config": {
                        "local-id": "l2evpnSharedEs",
                        "lower-bound": 1031072,
                        "upper-bound": 1032095
                      },
                      "local-id": "l2evpnSharedEs"
                    },
                    {
                      "config": {
                        "local-id": "ospf-sr",
                        "lower-bound": 900000,
                        "upper-bound": 965535
                      },
                      "local-id": "ospf-sr"
                    },
                    {
                      "config": {
                        "local-id": "srlb",
                        "lower-bound": 965536,
                        "upper-bound": 1031071
                      },
                      "local-id": "srlb"
                    },
                    {
                      "config": {
                        "local-id": "static",
                        "lower-bound": 16,
                        "upper-bound": 99999
                      },
                      "local-id": "static"
                    }
                  ]
                }
              },
              "signaling-protocols": {
                "rsvp-te": {
                  "global": {
                    "hellos": {
                      "config": {
                        "hello-interval": 10000
                      }
                    },
                    "soft-preemption": {
                      "config": {
                        "enable": true
                      }
                    }
                  }
                }
              }
            },
            "openconfig-network-instance:name": "default",
            "openconfig-network-instance:protocols": {
              "protocol": [
                {
                  "config": {
                    "identifier": "openconfig-policy-types:DIRECTLY_CONNECTED",
                    "name": "DIRECTLY_CONNECTED"
                  },
                  "identifier": "openconfig-policy-types:DIRECTLY_CONNECTED",
                  "name": "DIRECTLY_CONNECTED"
                },
                {
                  "config": {
                    "identifier": "openconfig-policy-types:BGP",
                    "name": "BGP"
                  },
                  "identifier": "openconfig-policy-types:BGP",
                  "name": "BGP"
                }
              ]
            },
            "openconfig-network-instance:segment-routing": {
              "srgbs": {
                "srgb": [
                  {
                    "config": {
                      "dataplane-type": "MPLS",
                      "local-id": "isis-sr",
                      "mpls-label-blocks": [
                        "isis-sr"
                      ]
                    },
                    "local-id": "isis-sr"
                  },
                  {
                    "config": {
                      "dataplane-type": "MPLS",
                      "local-id": "ospf-sr",
                      "mpls-label-blocks": [
                        "ospf-sr"
                      ]
                    },
                    "local-id": "ospf-sr"
                  }
                ]
              },
              "srlbs": {
                "srlb": [
                  {
                    "config": {
                      "dataplane-type": "MPLS",
                      "local-id": "srlb",
                      "mpls-label-block": "srlb"
                    },
                    "local-id": "srlb"
                  }
                ]
              }
            },
            "openconfig-network-instance:tables": {
              "table": [
                {
                  "address-family": "openconfig-types:IPV4",
                  "config": {
                    "address-family": "openconfig-types:IPV4",
                    "protocol": "openconfig-policy-types:DIRECTLY_CONNECTED"
                  },
                  "protocol": "openconfig-policy-types:DIRECTLY_CONNECTED"
                },
                {
                  "address-family": "openconfig-types:IPV6",
                  "config": {
                    "address-family": "openconfig-types:IPV6",
                    "protocol": "openconfig-policy-types:DIRECTLY_CONNECTED"
                  },
                  "protocol": "openconfig-policy-types:DIRECTLY_CONNECTED"
                }
              ]
            },
            "openconfig-network-instance:vlans": {
              "vlan": [
                {
                  "config": {
                    "name": "default",
                    "vlan-id": 1
                  },
                  "vlan-id": 1
                }
              ]
            }
          }
        }
      }
    ]
  }
]
```

```
gnmic -a ceos-01:6030 -u admin -p admin -e json --insecure get --path /system/ntp -t config
```


