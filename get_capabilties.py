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

with manager.connect(**srl_params) as m:
    # Filter for YANG model capabilities specifically
    yang_caps = [c for c in m.server_capabilities if "module=" in c]
    for cap in sorted(yang_caps):
        print(cap)
