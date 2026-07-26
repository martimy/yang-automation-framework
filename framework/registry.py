from translation.ceos.interface import CeosInterfaceTranslator
from translation.ceos.ospf import CeosOspfTranslator
from translation.ceos.ntp import CeosNtpTranslator

from translation.srlinux.subinterface import SrlinuxSubinterfaceTranslator
from translation.srlinux.network_instance import NetworkInstanceTranslator
from translation.srlinux.ospf import SrlinuxOspfTranslator
from translation.srlinux.ntp import SrlinuxNtpTranslator
from translation.srlinux.snmp import SrlinuxSnmpTranslator
from translation.srlinux.ni_interface import NiInterfaceBindingTranslator

from orchestration.ceos import CeosOrchestrator
from orchestration.srlinux import SrlinuxOrchestrator

TRANSLATORS = {
    "ceos": {
        "interface": CeosInterfaceTranslator(),
        "ospf": CeosOspfTranslator(),
        "ntp": CeosNtpTranslator(),
    },
    "srlinux": {
        "subinterface": SrlinuxSubinterfaceTranslator(),
        "network_instance": NetworkInstanceTranslator(),
        "ni_interface": NiInterfaceBindingTranslator(),
        "ospf": SrlinuxOspfTranslator(),
        "ntp": SrlinuxNtpTranslator(),
        "snmp": SrlinuxSnmpTranslator(),
    },
}

ORCHESTRATORS = {
    "ceos": CeosOrchestrator,
    "srlinux": SrlinuxOrchestrator,
}
