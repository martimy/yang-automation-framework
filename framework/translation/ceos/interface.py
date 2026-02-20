from dataclasses import asdict
from pathlib import Path
from typing import Optional, Union
from translation.base import BaseTranslator
from intent.interface import InterfaceIntent


class CeosInterfaceTranslator(BaseTranslator):

    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            self.template_dir = Path(__file__).parent.parent / "templates" / "ceos"

    def _build_data_structure(self, intent: InterfaceIntent) -> dict:
        return asdict(intent)

    def translate(
        self,
        intent: Union[InterfaceIntent, list[InterfaceIntent]],
        payload_format: str = "xml",
    ) -> str | dict:
        # normalize to always work with a list internally
        intents = intent if isinstance(intent, list) else [intent]
        data_list = [self._build_data_structure(i) for i in intents]

        if payload_format == "xml":
            return self._render_and_validate_xml(data_list, "interface.xml.j2")
        elif payload_format == "json":
            return self._render_and_validate_json(data_list, "interface.json.j2")
        else:
            raise ValueError(f"Unsupported format: {payload_format}")


if __name__ == "__main__":
    # For testing
    paramters = [
        {
            "name": "Ethernet1",
            "ip_address": "10.0.0.2",
            "prefix_length": "31",
            "enabled": True,
            "description": "A test interface",
            "network_instance": "default",
            "subinterface": 0,
        },
        {
            "name": "Ethernet2",
            "ip_address": "10.1.0.2",
            "prefix_length": "31",
            "enabled": True,
            "description": "A 2nd test interface",
            "network_instance": "default",
            "subinterface": 0,
        },
    ]

    intent = [InterfaceIntent(**p) for p in paramters]
    payload = CeosInterfaceTranslator().translate(intent, payload_format="json")

    print(payload)
