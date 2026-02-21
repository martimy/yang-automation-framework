from pathlib import Path
from typing import Optional
import xmltodict

from translation.base import BaseTranslator
from intent.network_instance import NetworkInstanceIntent

class NetworkInstanceTranslator(BaseTranslator):
    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            self.template_dir = Path(__file__).parent.parent / "templates" / "srlinux"

    def _build_data_structure(self, intent: NetworkInstanceIntent) -> dict:
        return asdict(intent)

    def translate(
        self,
        intent: NetworkInstanceIntent,
        payload_format: str = "xml",
    ) -> str | dict:
        data_list = self._build_data_structure(intent)
        if payload_format == "xml":
            return self._render_and_validate_xml(data_list, "network_instance.xml.j2")
        elif payload_format == "json":
            return self._render_and_validate_json(data_list, "network_instance.json.j2")
        else:
            raise ValueError(f"Unsupported format: {payload_format}")

    def _render_and_validate_xml(
        self, data_list: list[dict], template_file: str
    ) -> str:
        template = self._load_template(template_file)
        rendered = template.render(data_list)
        xmltodict.parse(rendered)
        return rendered

    def _render_and_validate_json(
        self, data_list: list[dict], template_file: str
    ) -> dict:
        template = self._load_template(template_file)
        rendered = template.render(data_list)
        return json.loads(rendered)


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
