from pathlib import Path
from typing import Optional

from translation.base import BaseTranslator
from intent.interface import InterfaceIntent


class SrlinuxSubinterfaceTranslator(BaseTranslator):
    """
    Translator for SRLinux interfaces using OpenConfig YANG models.

    This translator converts InterfaceIntent objects into OpenConfig-compliant
    XML payloads for SRLinux devices. It uses the subinterface.xml.j2 Jinja2 template
    to generate the final configuration.
    """

    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()

        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default template path: translation/templates/srlinux/
            self.template_dir = Path(__file__).parent.parent / "templates" / "srlinux"

        # Load the interface template
        self.template = self._load_template("subinterface.xml.j2")

    def translate(self, intent: InterfaceIntent) -> str:
        # Render the template
        try:
            xml_payload = self.template.render(**intent.__dict__)
            return xml_payload
        except Exception as e:
            raise RuntimeError(
                f"Failed to render template for interface {intent.name}: {str(e)}"
            )

    def translate_batch(self, intents: list[InterfaceIntent]) -> str:
        # Render the template
        try:
            xml_payload = self.template.render(interfaces=intents)
            return xml_payload
        except Exception as e:
            raise RuntimeError(f"Failed to render template for interfaces: {str(e)}")


if __name__ == "__main__":
    # For testing
    paramters = {
        "name": "ethernet-1/1",
        "description": "A test interface",
        "ip_address": "10.0.0.3",
        "prefix_length": "31",
        "enabled": True,
        "subinterface": 1,
        "network_instance": "default",
    }

    intent = InterfaceIntent(**paramters)
    translator = SrlinuxSubinterfaceTranslator()
    payload = translator.translate(intent)

    print(payload)
