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
    config = m.get_config(source="running")
    print(config.data_xml)
