from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Literal


@dataclass
class SnmpIntent:
    """
    Configuration parameters for SNMP communication with a network device.
    Supports versions 2c and 3.
    """

    # Common parameters
    host: str
    version: str

    # SNMPv2c specific
    community_ro: Optional[str] = None
    community_rw: Optional[str] = None

    # SNMPv3 specific
    security_name: Optional[str] = None          # username
    security_level: Optional[str] = None
    auth_protocol: Optional[str] = None
    auth_password: Optional[str] = None
    privacy_protocol: Optional[str] = None
    privacy_password: Optional[str] = None
    context_engine_id: Optional[str] = None
    context_name: Optional[str] = None

    enabled: bool = True
