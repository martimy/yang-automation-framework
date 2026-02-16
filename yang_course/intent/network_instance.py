from dataclasses import dataclass, field
from typing import List


@dataclass
class NetworkInstanceIntent:
    name: str  # 'default', 'MGMT', custom VRF name
    type: str = "ip-vrf"
    description: str = ""
