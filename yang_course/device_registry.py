from intent.interface import InterfaceIntent
from intent.network_instance import NetworkInstanceIntent

# DEVICE_REGISTRY = [
#     {
#         "host": "ceos-01",
#         "vendor": "ceos",
#         "admin": "admin",
#         "secret": "admin",
#         "intents": [
#             InterfaceIntent(
#                 name="Ethernet1",
#                 description="To SRL",
#                 ip_address="192.168.1.2",
#                 prefix_length=24,
#             )
#         ],
#     },
#     {
#         "host": "srl-01",
#         "vendor": "srlinux",
#         "admin": "admin",
#         "secret": "NokiaSrl1!",
#         "intents": [
#             InterfaceIntent(
#                 name="ethernet-1/1",
#                 description="To cEOS",
#                 ip_address="192.168.1.1",
#                 prefix_length=24,
#                 subinterface=0,  # change to 0
#                 network_instance="default",
#             ),
#             # NetworkInstanceIntent(
#             #     name="default",
#             #     description="Default VRF",
#             #     type = "ip-vrf"
#             # )
#         ],
#     },
# ]

DEVICE_REGISTRY = [
    {
        "host": "ceos-01",
        "vendor": "ceos",
        "admin": "admin",
        "secret": "admin",
        "intents": {
            "interfaces": [
                InterfaceIntent(
                    name="Ethernet1",
                    description="To SRL-01",
                    ip_address="192.168.1.2",
                    prefix_length=31,
                ),
                InterfaceIntent(
                    name="Ethernet2",
                    description="To SRL-02",
                    ip_address="192.168.1.4",
                    prefix_length=31,
                ),
            ]
        },
    },
    {
        "host": "srl-01",
        "vendor": "srlinux",
        "admin": "admin",
        "secret": "NokiaSrl1!",
        "intents": {
            "interfaces": [
                InterfaceIntent(
                    name="ethernet-1/1",
                    description="To cEOS-01",
                    ip_address="192.168.1.3",
                    prefix_length=31,
                    subinterface=0,
                    network_instance="default",
                ),
                InterfaceIntent(
                    name="ethernet-1/2",
                    description="To SRL-02",
                    ip_address="192.168.1.7",
                    prefix_length=31,
                    subinterface=0,
                    network_instance="default",
                ),
            ]
        },
    },
    {
        "host": "srl-02",
        "vendor": "srlinux",
        "admin": "admin",
        "secret": "NokiaSrl1!",
        "intents": {
            "interfaces": [
                InterfaceIntent(
                    name="ethernet-1/1",
                    description="To cEOS-01",
                    ip_address="192.168.1.5",
                    prefix_length=31,
                    subinterface=0,
                    network_instance="default",
                ),
                InterfaceIntent(
                    name="ethernet-1/2",
                    description="To SRL-01",
                    ip_address="192.168.1.6",
                    prefix_length=31,
                    subinterface=0,
                    network_instance="default",
                ),
            ]
        },
    },
]
