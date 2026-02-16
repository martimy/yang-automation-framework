from dataclasses import dataclass, field
from typing import List


@dataclass
class InterfaceIntent:
    name: str  # e.g. 'eth1'
    description: str
    ip_address: str  # e.g. '192.168.1.1'
    prefix_length: int  # e.g. 24
    enabled: bool = True
    mtu: int = 1500


@dataclass
class OspfIntent:
    process_id: int  # e.g. 1
    area_id: str  # e.g. '0.0.0.0' for the backbone
    router_id: str  # e.g. '10.255.255.1'
    interfaces: List[str]  # e.g. ['eth1', 'eth2']
    passive_interfaces: List[str] = field(default_factory=list)
    redistribute_connected: bool = False


@dataclass
class NtpIntent:
    servers: List[str]  # list of NTP server IPs
    source_interface: str


@dataclass
class SnmpIntent:
    version: str  # 'v2c' or 'v3'
    community: str  # v2c community string
    trap_destinations: List[str]
    location: str
    contact: str
