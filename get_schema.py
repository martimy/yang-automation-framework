from ncclient import manager

srl_params = {
    "host": "srl-01",
    "port": 830,
    "username": "admin",
    "password": "NokiaSrl1!",
    "hostkey_verify": False,
}

eos_params = {
    "host": "ceos-01",
    "port": 830,
    "username": "admin",
    "password": "admin",
    "hostkey_verify": False,
}

with manager.connect(**eos_params) as m:
    schema = m.get_schema("ietf-interfaces")
    with open("ietf-interfaces.yang", "w") as f:
        f.write(schema.data)
    schema = m.get_schema("openconfig-if-ip")
    with open("openconfig-if-ip.yang", "w") as f:
        f.write(schema.data)
