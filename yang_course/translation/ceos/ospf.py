from pathlib import Path
from typing import Optional

from translation.base import BaseTranslator
from intent.ospf import OspfIntent, OspfInterfaceIntent, OspfAreaIntent


class CeosOspfTranslator(BaseTranslator):
    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()

        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default template path: translation/templates/ceos/
            self.template_dir = Path(__file__).parent.parent / "templates" / "ceos"

        # Load the interface template
        self.template = self._load_template("ospf.xml.j2")

    def translate(self, intent: OspfIntent) -> str:
        # Render the template
        try:
            xml_payload = self.template.render(**intent.__dict__)
            return xml_payload
        except Exception as e:
            raise RuntimeError(
                f"Failed to render template for network instance {intent.name}: {str(e)}"
            )

if __name__ == "__main__":
    # For testing

    interfaces = [OspfInterfaceIntent(name="eth1"), OspfInterfaceIntent(name="eth2")] 
    areas = [OspfAreaIntent(id="0.0.0.0", interfaces=interfaces)]
    intent = OspfIntent(name="main", network_instance="default", router_id="10.0.0.1", areas=areas)

    translator = OspfTranslator()
    payload = translator.translate(intent)

    print(payload)
