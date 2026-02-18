from pathlib import Path
from typing import Optional

from translation.base import BaseTranslator
from intent.ntp import NtpIntent


class OpenconfigNtpTranslator(BaseTranslator):
    def __init__(self, template_dir: Optional[str] = None):
        super().__init__()

        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default template path: translation/templates/common/
            self.template_dir = Path(__file__).parent.parent / "templates" / "common"

        # Load the interface template
        self.template = self._load_template("ntp.xml.j2")

    def translate(self, intent: NtpIntent) -> str:
        # Render the template
        try:
            xml_payload = self.template.render(**intent.__dict__)
            return xml_payload
        except Exception as e:
            raise RuntimeError(f"Failed to render template for{intent.name}: {str(e)}")
