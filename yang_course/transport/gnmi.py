"""
gNMI Transport Layer
"""

from pygnmi.client import gNMIclient


class GnmiTransport:
    def __init__(self, host, username, password, port=57400, **kwargs):
        # gNMI uses a different default port
        # The 'insecure=True' flag is used for lab environments to bypass TLS certificate verification.
        # For production, you should use secure connections with valid certificates.
        self.target = (host, port)
        self.username = username
        self.password = password
        self.client = gNMIclient(
            target=self.target,
            username=self.username,
            password=self.password,
            insecure=True,
        )

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
        update_payload = []
        if "update" in payload:
            for path, val in payload["update"].items():
                update_payload.append((path, val))

        delete_payload = payload.get("delete", [])

        with self.client as client:
            try:
                # gNMI's SET is more direct than NETCONF's candidate/commit workflow.
                # It directly applies changes to the running configuration.
                # Production environments may require more complex validation or pre-check logic.
                client.set(update=update_payload, delete=delete_payload)
                print("Configuration pushed via gNMI.")
                return True
            except Exception as e:
                print(f"✗ gNMI SET failed: {e}")
                return False
