import sys
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

devices = ["srl", "ceos"]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Expecting: {sys.argv[0]} <device>")
        sys.exit(0)

    device = sys.argv[1]
    if device in devices:
        params = srl_params if device == "srl" else ceos_params

        # Create gNMI client connection
        with gNMIclient(**params) as gc:

            # Retrieve capabilities
            capabilities = gc.capabilities()

            caps = [
                f'{c["name"]}, {c["organization"]}, {c["version"]}'
                for c in capabilities["supported_models"]
            ]
            for cap in sorted(caps):
                print(cap)
    else:
        print(f"Avaliable devices are: {', '.join(devices)}.")
