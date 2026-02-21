from dataclasses import dataclass

@dataclass
class NetworkInstanceIntent:
    name: str  # 'default', 'MGMT', custom VRF name
    type: str = "L3"
    description: str = "Network Instance"
