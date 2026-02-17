from pathlib import Path
from typing import Optional

from translation.base import BaseTranslator
from intent.routing import GlobalRoutingIntent


class CeosGlobalRoutingTranslator(BaseTranslator):
    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()

        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default template path: translation/templates/ceos/
            self.template_dir = Path(__file__).parent.parent / "templates" / "ceos"

        # Load the interface template
        self.template = self._load_template("global_routing.xml.j2")

    def translate(self, intent: GlobalRoutingIntent) -> str:
        # Render the template
        try:
            xml_payload = self.template.render(**intent.__dict__)
            return xml_payload
        except Exception as e:
            raise RuntimeError(
                f"Failed to render template for interface {intent.name}: {str(e)}"
            )

    def translate_batch(self, intents: list[GlobalRoutingIntent]) -> list[str]:
        return [self.translate(intent) for intent in intents]


if __name__ == "__main__":
    # For testing
    paramters = {
        "ipv4_enabled": True,
    }

    intent = GlobalRoutingIntent(**paramters)
    translator = CeosGlobalRoutingTranslator()
    payload = translator.translate(intent)

    print(payload)
