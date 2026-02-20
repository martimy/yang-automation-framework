from pathlib import Path
from typing import Optional

from translation.base import BaseTranslator
from intent.network_instance import NetworkInstanceIntent


class NetworkInstanceTranslator(BaseTranslator):
    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()

        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default template path: translation/templates/srlinux/
            self.template_dir = Path(__file__).parent.parent / "templates" / "srlinux"

        # Load the interface template
        self.template = self._load_template("network_instance.xml.j2")

    def translate(
        self, intents: list[NetworkInstanceIntent], payload_format: str = "xml"
    ) -> str | dict:
        # Render the template
        try:
            xml_payload = self.template.render(**intent.__dict__)
            return xml_payload
        except Exception as e:
            raise RuntimeError(
                f"Failed to render template for network instance {intent.name}: {str(e)}"
            )

    def translate_batch(self, intents: list[NetworkInstanceIntent]) -> list[str]:
        return [self.translate(intent) for intent in intents]


if __name__ == "__main__":
    # For testing
    paramters = {
        "name": "default",
        "description": "Default VRF",
    }

    intent = NetworkInstanceIntent(**paramters)
    translator = NetworkInstanceTranslator()
    payload = translator.translate(intent)

    print(payload)
