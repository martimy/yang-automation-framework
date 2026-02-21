from pathlib import Path
from typing import Optional

from translation.base import BaseTranslator
from intent.ntp import NtpIntent, NtpServerIntent

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Union
from translation.base import BaseTranslator
import xmltodict


class CeosNtpTranslator(BaseTranslator):

    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            self.template_dir = Path(__file__).parent.parent / "templates" / "ceos"

    def _build_data_structure(self, intent: NtpIntent) -> dict:
        return asdict(intent)

    def translate(
        self,
        intent: NtpIntent,
        payload_format: str = "xml",
    ) -> str | dict:
        data_list = self._build_data_structure(intent)
        if payload_format == "xml":
            return self._render_and_validate_xml(data_list, "ntp.xml.j2")
        elif payload_format == "json":
            return self._render_and_validate_json(data_list, "ntp.json.j2")
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

    servers = [NtpServerIntent(host="192.168.100.1", source="192.168.100.11", network_instance="MGMT"),
               NtpServerIntent(host="pool.ntp.org", source="192.168.100.11", network_instance="MGMT")]
    intent = NtpIntent(servers=servers, enabled=True)

    translator = CeosNtpTranslator()
    payload = translator.translate(intent, payload_format="xml")

    print(payload)