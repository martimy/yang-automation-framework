from dataclasses import dataclass
from typing import List
from intent.srlinux.interface import InterfaceIntent

@dataclass
class NiInterfaceBindingIntent:
    network_instance: str
    interfaces: list[InterfaceIntent]
    