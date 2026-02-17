from dataclasses import dataclass


@dataclass
class InterfaceIntent:
    name: str  # e.g. 'Ethernet1' or 'ethernet-1/1'
    description: str
    ip_address: str
    prefix_length: int
    enabled: bool = True
    # SR-Linux specific — ignored by cEOS orchestrator
    subinterface: int = 0
    network_instance: str = "default"
