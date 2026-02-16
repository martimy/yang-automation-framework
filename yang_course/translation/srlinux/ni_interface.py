from jinja2 import Template, Environment, FileSystemLoader
from pathlib import Path
from typing import Dict, Any, Optional

from translation.base import BaseTranslator
from intent.ni_interface import NiInterfaceBindingIntent


class NiInterfaceBindingTranslator(BaseTranslator):
    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()

        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default template path: translation/templates/srlinux/
            self.template_dir = Path(__file__).parent.parent / "templates" / "srlinux"

        # Load the interface template
        self.template = self._load_template("ni_interface.xml.j2")

    def translate(self, intent: NiInterfaceBindingIntent) -> str:
        # Render the template
        try:
            xml_payload = self.template.render(**intent.__dict__)
            return xml_payload
        except Exception as e:
            raise RuntimeError(
                f"Failed to render template for network instance interface binding {intent.name}: {str(e)}"
            )

    def translate_batch(self, intents: list[NiInterfaceBindingIntent]) -> str:
        # Render the template
        try:
            xml_payload = self.template.render(interfaces=intents)
            return xml_payload
        except Exception as e:
            raise RuntimeError(
                f"Failed to render template for network instance interface binding: {str(e)}"
            )


if __name__ == "__main__":
    # For testing
    paramters = {
        "network_instance": "default",
        "interface": "ethernegt-1/1",  # parent interface name
        "subinterface": 0,  # subinterface index
    }

    intent = NiInterfaceBindingIntent(**paramters)
    translator = NiInterfaceBindingTranslator()
    payload = translator.translate(intent)

    print(payload)
