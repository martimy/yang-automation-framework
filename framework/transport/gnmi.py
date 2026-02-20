"""
gNMI Transport Layer
"""

from pygnmi.client import gNMIclient

devices = {
    "srl-01": {
        "target": ("srl-01", 57400),
        "username": "admin",
        "password": "NokiaSrl1!",
        "skip_verify": True,
    },
    "srl-02": {
        "target": ("srl-01", 57400),
        "username": "admin",
        "password": "NokiaSrl1!",
        "skip_verify": True,
    },
    "ceos-01": {
        "target": ("ceos-01", 6030),
        "username": "admin",
        "password": "admin",
        "insecure": True,
    },
}


class GnmiTransport:
    def __init__(self, host):
        # gNMI uses a different default port
        # The 'insecure=True' flag is used for lab environments to bypass TLS certificate verification.
        # For production, you should use secure connections with valid certificates.

        self.client = gNMIclient(**devices[host])

    def get_config(self, path: list) -> dict:
        """
        Retrieves configuration from the device using gNMI GET.
        A path must be specified.
        """
        with self.client as client:
            result = client.get(path=path, encoding="json_ietf")
            return result

    def push_config(self, payload: dict) -> bool:
        """
        Pushes configuration to the device using gNMI SET.
        The payload should be a dictionary representing the JSON to be sent.
        """

        if isinstance(payload, dict):
            payload = [payload]

        update_payload = [(item["path"], item["value"]) for item in payload]

        with self.client as client:
            try:
                # gNMI's SET is more direct than NETCONF's candidate/commit workflow.
                # It directly applies changes to the running configuration.
                # Production environments may require more complex validation or pre-check logic.
                result = client.set(update=update_payload)
                print(result)
                print("Configuration pushed via gNMI.")
                return True
            except Exception as e:
                print(f"✗ gNMI SET failed: {e}")
                return False
