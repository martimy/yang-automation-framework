import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Union
from translation.base import BaseTranslator
from intent.ospf import OspfInterfaceIntent, OspfAreaIntent, OspfIntent
import xmltodict


class SrlinuxOspfTranslator(BaseTranslator):

    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            self.template_dir = Path(__file__).parent.parent / "templates" / "srlinux"

    def _build_data_structure(self, intent: OspfIntent) -> dict:
        return asdict(intent)

    def translate(
        self,
        intent: OspfIntent,
        payload_format: str = "xml",
    ) -> str | dict:
        data_list = self._build_data_structure(intent)
        if payload_format == "xml":
            return self._render_and_validate_xml(data_list, "ospf.xml.j2")
        elif payload_format == "json":
            return self._render_and_validate_json(data_list, "ospf.json.j2")
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

    interfaces = [OspfInterfaceIntent(name="eth1"), OspfInterfaceIntent(name="eth2")]
    areas = [OspfAreaIntent(id="0.0.0.0", interfaces=interfaces)]
    intent = OspfIntent(
        name="main", network_instance="default", router_id="10.0.0.1", areas=areas
    )

    translator = SrlinuxOspfTranslator()
    payload = translator.translate(intent, payload_format="json")

    print(payload)
