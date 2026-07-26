from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Literal

 
"""
SRLinux Security Levels:
  no-auth-no-priv
  auth-no-priv
  auth-priv
"""

"""
SRLinux authentication protocols
  hmac-md5-96
  hmac-sha1-96
  hmac-sha2-224
  hmac-sha2-256
  hmac-sha2-384
  hmac-sha2-512
"""

"""
SRLinux privacy protocols
  cbc-des
  cfb128-aes-128
  cfb128-aes-192
  cfb128-aes-256
"""

@dataclass
class SnmpIntent:
    """
    Configuration parameters for SNMP communication with a network device.
    Supports versions 2c and 3.
    """

    # Common parameters
    network_instance : str = "mgmt"

    # SNMPv2c specific
    # SR Linux supports read-only SNMP community string
    community_ro: Optional[str] = None        # must have value to enable v2c
    community_rw: Optional[str] = None

    # v2c Trap server
    community_trap: Optional[str] = None      # must have value to enable
    trap_server_address: Optional[str] = None

    # SNMPv3 specific
    security_level: Optional[str] = None      # must have value to enable v3
    user_name: Optional[str] = None
    auth_protocol: Optional[str] = None
    auth_password: Optional[str] = None
    priv_protocol: Optional[str] = None
    priv_password: Optional[str] = None

    # v3 Trap server
    # to be completed
