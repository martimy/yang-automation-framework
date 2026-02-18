from translation.ceos.interface import CeosInterfaceTranslator
from translation.ceos.global_routing import CeosGlobalRoutingTranslator
from translation.ceos.ospf import CeosOspfTranslator
from translation.srlinux.subinterface import SrlinuxSubinterfaceTranslator
from translation.srlinux.network_instance import NetworkInstanceTranslator
from translation.srlinux.ospf import SrlinuxOspfTranslator

from orchestration.ceos import CeosOrchestrator
from orchestration.srlinux import SrlinuxOrchestrator
from translation.srlinux.ni_interface import NiInterfaceBindingTranslator

TRANSLATORS = {
    "ceos": {
        "interface": CeosInterfaceTranslator(),
        "ospf": CeosOspfTranslator(),
        # "global": CeosGlobalRoutingTranslator(),
    },
    "srlinux": {
        "subinterface": SrlinuxSubinterfaceTranslator(),
        "network_instance": NetworkInstanceTranslator(),
        "ni_interface": NiInterfaceBindingTranslator(),
        "ospf": SrlinuxOspfTranslator(),
    },
}

ORCHESTRATORS = {
    "ceos": CeosOrchestrator,
    "srlinux": SrlinuxOrchestrator,
}
