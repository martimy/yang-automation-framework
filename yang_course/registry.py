from translation.ceos.interface import CeosInterfaceTranslator
from translation.ceos.global_routing import CeosGlobalRoutingTranslator
from translation.srlinux.subinterface import SrlinuxInterfaceTranslator
from translation.srlinux.network_instance import NetworkInstanceTranslator

from orchestration.ceos import CeosOrchestrator
from orchestration.srlinux import SrlinuxOrchestrator
from translation.srlinux.ni_interface import NiInterfaceBindingTranslator

TRANSLATORS = {
    "ceos": {
        "interface": CeosInterfaceTranslator(),
        "global": CeosGlobalRoutingTranslator(),
    },
    "srlinux": {
        "subinterface": SrlinuxInterfaceTranslator(),
        "network_instance": NetworkInstanceTranslator(),
        "ni_interface": NiInterfaceBindingTranslator(),
    },
}

ORCHESTRATORS = {
    "ceos": CeosOrchestrator,
    "srlinux": SrlinuxOrchestrator,
}
