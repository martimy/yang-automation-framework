from dataclasses import dataclass


@dataclass
class NetworkInstanceIntent:
    name: str  # 'default', 'MGMT', custom VRF name
    type: str = "ip-vrf"
    description: str = ""
