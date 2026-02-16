from dataclasses import dataclass, field
from typing import List


@dataclass
class NiInterfaceBindingIntent:
    network_instance: str
    interface: str  # parent interface name
    subinterface: int = 0  # subinterface index
