# intent/ntp.py
from dataclasses import dataclass
from typing import List


@dataclass
class NtpServerIntent:
    host: str
    source: str
    network_instance: str  # typically management

@dataclass
class NtpIntent:
    """
    Maps to an NTP instance
    """

    servers: List[NtpServerIntent]
    enabled: bool = True
