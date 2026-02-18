# intent/ntp.py
from dataclasses import dataclass
from typing import List


@dataclass
class NtpIntent:
    """
    Maps to an NTP instance
    """

    network_instance: str  # typically management
    servers: List[str]
    source_address: str
    enabled: bool = True
