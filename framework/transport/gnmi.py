"""
gNMI Transport Layer
"""

from pygnmi.client import gNMIclient

# gNMI's default port genuinely varies by vendor (unlike NETCONF's, which is
# 830 for both) -- this is a transport-layer detail, not a credentials one,
# so it stays here rather than in inventory.yml. Callers not using one of
# these vendors must pass port explicitly.
DEFAULT_PORTS = {"srlinux": 57400, "ceos": 6030}

# TLS handling also varies by vendor, and the two modes are NOT
# interchangeable: "insecure" connects with no TLS at all (plaintext gRPC),
# while "skip_verify" connects WITH TLS but skips verifying the (self-signed)
# certificate. SR Linux's gNMI server requires TLS -- it needs skip_verify,
# the same way `gnmic ... --skip-verify` does. cEOS accepts a plaintext
# channel. Passing the wrong mode doesn't fail cleanly: the client just hangs
# until grpc's channel-ready timeout fires, which looks like a network
# problem rather than a config mismatch.
DEFAULT_TLS_MODE = {"srlinux": "skip_verify", "ceos": "insecure"}


class GnmiTransport:
    def __init__(self, host, username, password, vendor=None, port=None, tls_mode=None):
        # gNMI uses a different default port per vendor; see DEFAULT_PORTS.
        if port is None:
            if vendor not in DEFAULT_PORTS:
                raise ValueError(
                    f"No default gNMI port known for vendor '{vendor}' -- pass port explicitly."
                )
            port = DEFAULT_PORTS[vendor]

        # And a different default TLS mode; see DEFAULT_TLS_MODE.
        if tls_mode is None:
            if vendor not in DEFAULT_TLS_MODE:
                raise ValueError(
                    f"No default gNMI TLS mode known for vendor '{vendor}' -- "
                    f"pass tls_mode explicitly ('insecure' or 'skip_verify')."
                )
            tls_mode = DEFAULT_TLS_MODE[vendor]

        client_kwargs = {"target": (host, port), "username": username, "password": password}
        if tls_mode == "insecure":
            # No TLS at all -- lab-only; never use against a real network.
            client_kwargs["insecure"] = True
        elif tls_mode == "skip_verify":
            # TLS, but skip certificate verification -- fine for a
            # self-signed lab cert; still not what you'd want in production.
            client_kwargs["skip_verify"] = True
        else:
            raise ValueError(f"Unknown tls_mode '{tls_mode}', expected 'insecure' or 'skip_verify'")

        self.client = gNMIclient(**client_kwargs)

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
                print("Configuration pushed via gNMI.")
                return True
            except Exception as e:
                print(f"✗ gNMI SET failed: {e}")
                return False
