from pathlib import Path
from typing import Optional

from translation.base import BaseTranslator
from intent.ntp import NtpIntent


class OpenconfigNtpTranslator(BaseTranslator):
    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()

        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default template path: translation/templates/common/
            self.template_dir = Path(__file__).parent.parent / "templates" / "common"

        # Load the interface template
        self.template = self._load_template("ntp.xml.j2")

    def translate(self, intent: NtpIntent, payload_format: str = "xml") -> str | dict:
        """
        Translates an NtpIntent into either XML for NETCONF or a dict for gNMI.
        """
        if payload_format == "json":
            # Construct the JSON payload for gNMI (OpenConfig model)
            servers = []
            for server in intent.servers:
                servers.append(
                    {
                        "address": server["ip_address"],
                        "config": {
                            "address": server["ip_address"],
                        },
                    }
                )

            return {
                "update": {
                    "openconfig-system:system/ntp": {
                        "config": {"enabled": True},
                        "servers": {"server": servers},
                    }
                }
            }

        # Render the XML template for NETCONF
        try:
            xml_payload = self.template.render(**intent.__dict__)
            return xml_payload
        except Exception as e:
            raise RuntimeError(f"Failed to render template for {intent.network_instance}: {str(e)}")
