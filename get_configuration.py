from ncclient import manager

srl_params = {
    "host": "srl-01",
    "port": 830,
    "username": "admin",
    "password": "NokiaSrl1!",
    "hostkey_verify": False,
}

ceos_params = {
    "host": "ceos-01",
    "port": 830,
    "username": "admin",
    "password": "admin",
    "hostkey_verify": False,
}

# Filter: Get one specific interface by name
ONE_SRL_INTERFACE = """
<interfaces xmlns="http://openconfig.net/yang/interfaces">
    <interface>
        <name>ethernet-1/1</name>
    </interface>
</interfaces>
"""

ONE_CEOS_INTERFACE = """
<interfaces>
    <interface>
        <name>Ethernet1</name>
    </interface>
</interfaces>
"""

SRL_OSPF = """
<network-instance xmlns="urn:nokia.com:srlinux:net-inst:network-instance">
    <protocols>
        <ospf xmlns="urn:nokia.com:srlinux:ospf:ospf"/>
    </protocols>
</network-instance>
"""

with manager.connect(**srl_params) as m:
    config = m.get_config(source="running", filter=("subtree", SRL_OSPF))
    print(config.data_xml)
