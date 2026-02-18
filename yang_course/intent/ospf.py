# intent/ospf.py
from dataclasses import dataclass, field
from typing import List

@dataclass
class OspfInterfaceIntent:
    """Single interface enabled for OSPF in an area."""
    name: str                    # e.g. "ethernet-1/1.0" (subinterface)
    enabled: bool = True
    passive: bool = False
    network_type: str = "point_to_point_network"
    # metric: int = None           # optional override
    # priority: int = None         # for DR election

@dataclass
class OspfAreaIntent:
    """Single OSPF area containing multiple interfaces."""
    id: str                      # e.g. "0.0.0.0" for backbone
    interfaces: List[OspfInterfaceIntent] = field(default_factory=list)
    area_type: str = "normal"    # "normal", "stub", "nssa"

@dataclass
class OspfIntent:
    """
    Complete OSPF process configuration.
    Maps to one OSPF instance within a network-instance.
    """
    name: str                    # process name e.g. "main"
    network_instance: str        # which VRF/network-instance
    router_id: str = None        # auto-derived if None
    enabled: bool = True
    areas: List[OspfAreaIntent] = field(default_factory=list)
    # export_policies: List[str] = field(default_factory=list)
    # import_policies: List[str] = field(default_factory=list)