from pygnmi.client import gNMIclient

srl_params = {
    "target": ("srl-01", 57400),
    "username": "admin",
    "password": "NokiaSrl1!",
    "skip_verify": True,
}

ceos_params = {
    "target": ("ceos-01", 6030),
    "username": "admin",
    "password": "admin",
    "insecure": True,
}

xpath = "/interface"

if __name__ == "__main__":
    # Create gNMI client connection
    with gNMIclient(**srl_params) as gc:


        result = gc.get(path=[xpath], datatype="config")
        print(result)
