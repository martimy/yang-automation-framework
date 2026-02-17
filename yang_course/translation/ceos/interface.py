from pathlib import Path
from typing import Optional

from translation.base import BaseTranslator
from intent.interface import InterfaceIntent


class CeosInterfaceTranslator(BaseTranslator):
    """
    Translator for cEOS interfaces using OpenConfig YANG models.

    This translator converts InterfaceIntent objects into OpenConfig-compliant
    XML payloads for cEOS devices. It uses the interface.xml.j2 Jinja2 template
    to generate the final configuration.
    """

    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()

        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default template path: translation/templates/ceos/
            self.template_dir = Path(__file__).parent.parent / "templates" / "ceos"

        # Load the interface template
        self.template = self._load_template("interface.xml.j2")

    def translate(self, intent: InterfaceIntent, payload_format: str = 'xml') -> str | dict:
        """
        Translates an InterfaceIntent into either XML for NETCONF or a dict for gNMI.
        """
        if payload_format == 'json':
            # Construct the JSON payload for gNMI (OpenConfig model)
            return {
                "openconfig-interfaces:interfaces": {
                    "interface": [
                        {
                            "name": intent.name,
                            "config": {
                                "name": intent.name,
                                "description": intent.description,
                                "enabled": intent.enabled,
                                "mtu": intent.mtu
                            },
                            "subinterfaces": {
                                "subinterface": [
                                    {
                                        "index": 0,
                                        "openconfig-if-ip:ipv4": {
                                            "addresses": {
                                                "address": [
                                                    {
                                                        "ip": intent.ip_address,
                                                        "config": {
                                                            "ip": intent.ip_address,
                                                            "prefix-length": intent.prefix_length
                                                        }
                                                    }
                                                ]
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }

        # Render the XML template for NETCONF
        try:
            xml_payload = self.template.render(**intent.__dict__)
            return xml_payload
        except Exception as e:
            raise RuntimeError(
                f"Failed to render template for interface {intent.name}: {str(e)}"
            )

    def translate_batch(self, intents: list[InterfaceIntent], payload_format: str = 'xml') -> str:
        # Render the template
        try:
            xml_payload = self.template.render(interfaces=intents)
            return xml_payload
        except Exception as e:
            raise RuntimeError(f"Failed to render template for interfaces: {str(e)}")


if __name__ == "__main__":
    # For testing
    paramters = {
        "name": "Ethernet1",
        "description": "A test interface",
        "ip_address": "10.0.0.2",
        "prefix_length": "31",
        "enabled": True,
        "subinterface_index": 0,
        "network_instance": "default",
    }

    intent = InterfaceIntent(**paramters)
    translator = OpenConfigInterfaceTranslator()
    payload = translator.translate(intent)

    print(payload)
