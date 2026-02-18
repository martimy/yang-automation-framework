from dataclasses import dataclass


@dataclass
class InterfaceIntent:
    name: str  # e.g. 'Ethernet1' or 'ethernet-1/1'
    ip_address: str
    prefix_length: int
    enabled: bool = True
    description: str = ""
    # SR-Linux specific — ignored by cEOS orchestrator
    network_instance: str = "default"
    subinterface: int = 0
